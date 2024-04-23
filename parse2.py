import libcst
import os


class FunctionCollector(libcst.CSTVisitor):
    def __init__(self, module, current_file):
        self.functions = {}
        self.current_class = None
        self.module = module  # This is the libcst.Module for the current file
        self.current_file = current_file  # Store the current file path

    def visit_ClassDef(self, node):
        self.current_class = node.name.value

    def leave_ClassDef(self, node):
        self.current_class = None

    def visit_FunctionDef(self, node):
        function_name = node.name.value
        args = node.params
        arg_list = ','.join([param.name.value for param in args.params])
        key = f"{self.current_file}|"
        if self.current_class:
            key += f"{self.current_class}:"
        key += f"{function_name}|{arg_list}"
        self.functions[key] = libcst.Module([]).code_for_node(node)
        

def extract_functions(directory):
    function_dict = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as source_file:
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
        if node.name.value == self.function_name and (self.class_name is None or self.in_target_class):
            print(f'Updating function {self.function_name} in class {self.class_name if self.class_name else "N/A"}')
            return self.update_function(node)
        return node

    def update_function(self, node):
        new_docstring_node = libcst.Expr(value=self.new_docstring)

        # Checking and managing existing docstring
        body_list = list(node.body.body)
        if body_list and isinstance(body_list[0], libcst.Expr) and isinstance(body_list[0].value, libcst.SimpleString):
            print('replacing docstring')
            body_list[0] = new_docstring_node  # Replace existing docstring
        else:
            print('creating docstring')
            body_list.insert(0, new_docstring_node)  # Insert new docstring

        return node.with_changes(
            body=node.body.with_changes(body=body_list)
        )


def update_docstring(key, new_docstring):
    print(f'Adding "{new_docstring}" to {key}')
    parts = key.split('|')
    file_path, function_signature = parts[0], parts[1]
    class_name = None
    if ':' in function_signature:
        class_name, function_name = function_signature.split(':')
    else:
        function_name = function_signature

    print(f'Path: {file_path}, Class: {class_name}, Function: {function_name}')

    with open(file_path, "r") as source_file:
        source_code = source_file.read()

    tree = libcst.parse_module(source_code)
    transformer = DocstringUpdater(function_name, class_name, new_docstring)
    new_tree = tree.visit(transformer)

    new_source = new_tree.code

    with open(file_path, "w") as source_file:
        source_file.write(new_source)

