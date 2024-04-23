import libcst
import os


class FunctionCollector(libcst.CSTVisitor):

    def __init__(self, module, current_file):
        self.functions = {}
        self.current_class = None
        self.module = module
        self.current_file = current_file

    def visit_ClassDef(self, node):
        self.current_class = node.name.value

    def leave_ClassDef(self, node):
        self.current_class = None

    def visit_FunctionDef(self, node):
        function_name = node.name.value
        args = node.params
        arg_list = ','.join([param.name.value for param in args.params])
        key = f'{self.current_file}|'
        if self.current_class:
            key += f'{self.current_class}:'
        key += f'{function_name}|{arg_list}'
        self.functions[key] = libcst.Module([]).code_for_node(node)


def extract_functions(directory):
    """
Extracts and organizes functions from Python source files within a given directory.

This function walks through the specified directory and its subdirectories, parsing each Python file (.py) found. It then collects and organizes the functions defined in these files into a dictionary, where each key represents a unique function name and its corresponding value is the path to the file containing that function.

Parameters:
directory (str): The root directory whose contents are to be searched for Python source files.

Returns:
function_dict (dict): A dictionary mapping each function name to its respective source file path. This allows for easy access and manipulation of functions by their names.

Example:
>>> extract_functions("/path/to/directory")
# Returns a dictionary containing all the functions found in the specified directory.
"""
    function_dict = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r') as source_file:
                    source_code = source_file.read()
                    module = libcst.parse_module(source_code)
                    collector = FunctionCollector(module, path)
                    module.visit(collector)
                    function_dict.update(collector.functions)
    return function_dict


class DocstringUpdater(libcst.CSTTransformer):

    def __init__(self, function_name, class_name, new_docstring):
        self.function_name = function_name
        self.class_name = class_name
        self.new_docstring = libcst.SimpleString(f'"""{new_docstring}"""')
        self.in_target_class = False

    def visit_ClassDef(self, node):
        if node.name.value == self.class_name:
            print(f'Entering class {self.class_name}')
            self.in_target_class = True

    def leave_ClassDef(self, node, updated_node):
        if self.in_target_class:
            print(f'Leaving class {self.class_name}')
        self.in_target_class = False
        return updated_node

    def visit_FunctionDef(self, node):
        print(f'Visiting function {node.name.value}')
        if node.name.value == self.function_name and (self.class_name is
            None or self.in_target_class):
            print(
                f"Updating function {self.function_name} in class {self.class_name if self.class_name else 'N/A'}"
                )
            return self.update_function(node)
        return node

    def update_function(self, node):
        new_docstring_node = libcst.Expr(value=self.new_docstring)
        body_list = list(node.body.body)
        if body_list and isinstance(body_list[0], libcst.Expr) and isinstance(
            body_list[0].value, libcst.SimpleString):
            print('replacing docstring')
            body_list[0] = new_docstring_node
        else:
            print('creating docstring')
            body_list.insert(0, new_docstring_node)
        return node.with_changes(body=node.body.with_changes(body=body_list))


def update_docstring(key, new_docstring):
    """
Updates the docstring of a specified function within a Python module.

This function reads the source code of a Python module, parses its Abstract Syntax Tree (AST) to find the function with the given name and class (if applicable), and then updates its docstring with the provided new docstring. The updated source code is then written back to the same file, effectively updating the file in-place.

Parameters:
key (str): A string in the format "file_path|function_signature", where "file_path" is the path to the Python module and "function_signature" is the name of the function whose docstring needs updating. For functions within classes, use the class name followed by a colon.
new_docstring (str): The new docstring content that will replace the existing docstring of the specified function.

Raises:
FileNotFoundError: If the file specified by `key` does not exist.
SyntaxError: If the source code in `key` is not valid Python code.
ValueError: If no function with the name `function_name` exists in the file, or if the file contains no functions at all.

Returns:
None: The function does not return any value. It modifies the file directly.

Example:
>>> update_docstring("example.py|my_function", "This is the new docstring.")
# This will update the docstring of `my_function` in `example.py` file.
"""
    print(f'Adding "{new_docstring}" to {key}')
    parts = key.split('|')
    file_path, function_signature = parts[0], parts[1]
    class_name = None
    if ':' in function_signature:
        class_name, function_name = function_signature.split(':')
    else:
        function_name = function_signature
    print(f'Path: {file_path}, Class: {class_name}, Function: {function_name}')
    with open(file_path, 'r') as source_file:
        source_code = source_file.read()
    tree = libcst.parse_module(source_code)
    transformer = DocstringUpdater(function_name, class_name, new_docstring)
    new_tree = tree.visit(transformer)
    new_source = new_tree.code
    with open(file_path, 'w') as source_file:
        source_file.write(new_source)
