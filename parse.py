import os
import ast
import astor


def get_function_code(node, source_code):
    """
Retrieves the source code of a given AST node representing a Python function.

This function takes an Abstract Syntax Tree (AST) node and the original source code, then
extracts the source code corresponding to that node. The returned string represents the
actual function definition, including its body, but not any potential docstring or type
hints.

Parameters:
node (ast.FunctionDef): The AST node representing the Python function.
source_code (str): The original source code of the Python file where the function is defined.

Returns:
str: The source code of the given function node.
"""
    return ast.get_source_segment(source_code, node)


def get_function_parameters(function_node):
    """
Extracts and formats the parameters of a given Python function node into a readable string.

This function takes a parsed AST (Abstract Syntax Tree) node representing a function
definition as input, and returns a comma-separated string containing the function's
parameter names and their annotations, if any. The returned string is suitable for
displaying or logging information about the function's parameters.

Parameters:
function_node (ast.FunctionDef): The parsed Python function definition node.

Returns:
str: A comma-separated string representing the function's parameters and their
      annotations.
"""
    return ','.join(f'{arg.arg}={ast.unparse(arg.annotation)}' if arg.
        annotation else arg.arg for arg in function_node.args.args)


def extract_functions(base_directory):
    """
Extracts all Python functions from a directory and its subdirectories, and creates a map of these functions along with their corresponding source code.

This function traverses the directory tree, reads each Python file, parses its source code, and extracts information about the defined functions. It also extracts the directory path of each file to uniquely identify the functions within the same file but different directories.

The returned map is a dictionary where keys are composite identifiers (directory path | function name | parameters) and values are the actual function code.

This function is useful for creating a comprehensive mapping of all Python functions across multiple files and directories, which can be used for various purposes such as code analysis, documentation generation, or automatic testing.

Parameters:
base_directory (str): The root directory to start searching for Python files.

Returns:
functions_map (dict): A dictionary where keys are composite identifiers representing the functions, and values are the actual function code.
"""
    functions_map = {}
    for root, dirs, files in os.walk(base_directory):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                with open(file_path, 'r') as file:
                    source_code = file.read()
                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    for child in ast.iter_child_nodes(node):
                        child.parent = node
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        parent = getattr(node, 'parent', None)
                        if isinstance(parent, ast.ClassDef):
                            function_name = f'{parent.name}:{node.name}'
                        else:
                            function_name = node.name
                        parameters = get_function_parameters(node)
                        function_code = get_function_code(node, source_code)
                        key = f'{file_path}|{function_name}|{parameters}'
                        functions_map[key] = function_code
    return functions_map


def update_docstring(function_key, new_docstring):
    """
Updates the docstring of a specified function within a Python source file.

This function takes in a function key (filepath|function_id|parameters) and a new docstring, parses the source code to find the corresponding function, updates its existing docstring with the provided new docstring, and then writes back the modified code to the same file. The function supports functions within classes and raises specific exceptions if the file does not exist or the specified function is not found.

Parameters:
function_key (str): A string representing the filepath|function_id|parameters of the function whose docstring needs updating.
new_docstring (str): The new docstring content that will replace the existing docstring of the specified function.

Raises:
FileNotFoundError: If the file specified by `filename` does not exist.
ValueError: If no function with the name matching the provided key exists in the file, or if the file contains no functions at all.

Returns:
None: The function does not return any value. It modifies the file directly.

Example:
>>> update_docstring("example.py|my_function|", "This is the new docstring.")
# This will update the docstring of `my_function` in `example.py` file.
"""
    print(f'updating {function_key}')
    parts = function_key.split('|')
    if len(parts) < 3:
        raise ValueError(
            'Invalid function key format. Expected pattern filepath|function_id|parameters'
            )
    path = parts[0]
    function_parts = parts[1].split(':')
    function_name = function_parts[-1]
    class_name = None if len(function_parts) == 1 else function_parts[0]
    try:
        with open(path, 'r') as file:
            source_code = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f'No such file or directory: {path}')
    tree = ast.parse(source_code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            if class_name:
                parent = getattr(node, 'parent', None)
                if not (isinstance(parent, ast.ClassDef) and parent.name ==
                    class_name):
                    continue
            found = True
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                node.body[0].value, ast.Str):
                node.body.pop(0)
            new_doc_expr = ast.Expr(value=ast.Str(s=new_docstring.strip('"'
                ).strip("'")))
            node.body.insert(0, new_doc_expr)
            break
    if not found:
        raise ValueError(
            f'Function or method not found with the provided key {class_name}:{function_name}.'
            )
    with open(path, 'w') as file:
        file.write(astor.to_source(tree))
