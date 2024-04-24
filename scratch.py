import libcst

class DocstringUpdater(libcst.CSTTransformer):
    def __init__(self):
        self.function_level = 0
        self.class_level = 0

    def visit_ClassDef(self, node: libcst.ClassDef) -> None:
        self.class_level += 1

    def leave_ClassDef(self, original_node: libcst.ClassDef, updated_node: libcst.ClassDef) -> libcst.ClassDef:
        self.class_level -= 1
        return updated_node

    def visit_FunctionDef(self, node: libcst.FunctionDef) -> None:
        self.function_level += 1
        
    def convert_functiondef_to_string(function_def: libcst.FunctionDef) -> str:
      code = libcst.Module()
      code.body.append(function_def)
      return code.code

    def leave_FunctionDef(self, original_node: libcst.FunctionDef, updated_node: libcst.FunctionDef) -> libcst.BaseStatement:
        self.function_level -= 1
        
        print(f'class_level: {self.class_level}')
        print(f'function_level: {self.function_level}')        
        
        if self.function_level > 0 or self.class_level > 1:
            return updated_node

        current_docstring = updated_node.get_docstring()
        new_docstring = generate_docstring(updated_node.body, current_docstring)

        if current_docstring is not None:
            # Replace existing docstring
            body_statements = list(updated_node.body.body)
            if isinstance(body_statements[0], libcst.SimpleStatementLine) and isinstance(body_statements[0].body[0], libcst.Expr):
                if isinstance(body_statements[0].body[0].value, libcst.SimpleString):
                    body_statements[0] = libcst.SimpleStatementLine([libcst.Expr(libcst.SimpleString(f'"""{new_docstring}"""'))])
            updated_body = libcst.IndentedBlock(body=body_statements)
        else:
            # Append new docstring
            updated_body = libcst.IndentedBlock(
                body=[libcst.SimpleStatementLine([libcst.Expr(libcst.SimpleString(f'"""{new_docstring}"""'))])] + list(updated_node.body.body)
            )
        return updated_node.with_changes(body=updated_body)

def generate_docstring(body, current_docstring):
    # Placeholder for external function
    return 'Hello, world!'

def process_file(file_path):
    with open(file_path, "r") as source_file:
        source_code = source_file.read()

    tree = libcst.parse_module(source_code)
    transformer = DocstringUpdater()
    modified_tree = tree.visit(transformer)
    print(modified_tree.code)

# Example usage
process_file("testing/example.py")
