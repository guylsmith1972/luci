import libcst

class SimpleVisitor(libcst.CSTTransformer):
    def visit_ClassDef(self, node: libcst.ClassDef) -> None:
        print(f"Entering class: {node.name.value}")
        return None

    def leave_ClassDef(self, node: libcst.ClassDef) -> None:
        print(f"Leaving class: {node.name.value}")
        return None

source_code = """
class Test:
    def example(self):
        pass
"""

tree = libcst.parse_module(source_code)
tree.visit(SimpleVisitor())
