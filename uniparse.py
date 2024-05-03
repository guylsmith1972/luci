from tree_sitter_languages import get_language, get_parser


python_specification = {
    "class_definition": ["class", ["identifier"]],
    "function_definition": ["function", ["identifier"]]
}

cpp_specification = {
    "class_specifier": ["class", ["type_identifier"]],
    "function_definition": ["function", [lambda nt: nt=="function_declarator" or nt=="parenthesized_declarator", lambda nt: nt == "field_identifier" or nt == "identifier"]]
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


def print_tree(node, language, context, level=0, source_code=None):

    print(f'node.type: {"  " * level}{node.type} -- {node.text}')

    # Recursively process children
    for child in node.children:
        print_tree(child, language, context, level+1, source_code)


def print_functions(node, language, context, source_code=None):
    def get_element(node, sequence):
        comparator = sequence[0] if callable(sequence[0]) else lambda nt: nt == sequence[0]
        next_node = next((child for child in node.children if comparator(child.type)), None)
        return next_node if len(sequence) == 1 else get_element(next_node, sequence[1:]) if next_node else None


    specification = languages[language]
    node_type = specification[node.type] if node.type in specification else None
    
    extended_context = False
    
    if node_type is not None and (node_type[0] == 'class' or node_type[0] == 'function'):
        subtype = node_type[1]
        name_node = get_element(node, subtype)
        if name_node:
            name = name_node.text.decode("utf-8")
            context.append(name)
            extended_context = True
            print(f"Name: {'.'.join(context)}")
            if node_type[0] == 'function':
               code_body = node.text.decode("utf-8")
               print(code_body)

    # Recursively process children
    for child in node.children:
        print_functions(child, language, context, source_code)

    if extended_context:
        context.pop()

def main():
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
        void (do_nothing) {}
    };
    
    int main(int argc, char**argv) {
        return 0
    }
    """


    print('=' * 79)
    root_node = parse(python_code, 'python')
    print_tree(root_node, 'python', [], source_code=python_code)

    print('-' * 79)
    root_node = parse(python_code, 'python')
    print_functions(root_node, 'python', [], source_code=python_code)

    print('=' * 79)
    root_node = parse(c_code, 'cpp')
    print_tree(root_node, 'cpp', [], source_code=c_code)

    print('-' * 79)
    root_node = parse(c_code, 'cpp')
    print_functions(root_node, 'cpp', [], source_code=c_code)

if __name__ == '__main__':
    main()
    