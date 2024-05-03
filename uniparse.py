from tree_sitter_languages import get_language, get_parser


parser = get_parser('python')
parser.set_language(get_language('python'))

code = """
class MyClass:
    def my_method(self):
        pass
"""

tree = parser.parse(bytes(code, "utf8"))
root_node = tree.root_node

# Function to recursively print the tree
def print_tree(node, level=0):
    print('  ' * level + node.type, node.start_point, node.end_point)
    for child in node.children:
        print_tree(child, level+1)

print_tree(root_node)