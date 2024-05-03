from tree_sitter_languages import get_language, get_parser

python_code = """
class MyClass:
    def my_method(self, value):
        return value == 42

def foo():
    pass
"""

c_code = """
class Foo {
public:
    void bar();
}

int main(int argc, char**argv) {
    return 0
}
"""


python_specification = {
    "class_definition": ["class", "identifier"],
    "function_definition": ["function", "identifier"]
}

cpp_specification = {
    "class_specifier": ["class", "identifier"],
    "function_declarator": ["function", "identifier"]
}

languages = {
    "c": cpp_specification,
    "cpp": cpp_specification,
    "python": python_specification
}

def parse(code, language):
    parser = get_parser(language)
    parser.set_language(get_language(language))

    tree = parser.parse(bytes(code, "utf8"))
    return tree.root_node

# Function to recursively print only class and function names
def print_tree(node, language, level=0, source_code=None):
    specification = languages[language]
    node_type = specification[node.type] if node.type in specification else None
    if node_type is not None and (node_type[0] == 'class' or node_type[0] == 'function'):
        subtype = node_type[1]
        name_node = next((child for child in node.children if child.type == subtype), None)
        if name_node:
            name = name_node.text
            prefix = '  ' * level  # Add indentation based on the tree level
            print(f"{prefix}Name: {name}")

    # Recursively process children
    for child in node.children:
        print_tree(child, language, level+1, source_code)

print('-' * 79)
root_node = parse(python_code, 'python')
print_tree(root_node, 'python', source_code=python_code)

print('-' * 79)
root_node = parse(c_code, 'cpp')
print_tree(root_node, 'cpp', source_code=c_code)
