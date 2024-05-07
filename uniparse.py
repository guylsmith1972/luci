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


class PrintTransformer:
    def __init__(self):
        self.level = 0
        
    def enter_class(self, node, context):
        print(f'{"   " * self.level}Entering class {context[-1]}: {".".join(context)}')
        self.level += 1
    
    def leave_class(self, node, context):
        self.level -= 1
        print(f'{"   " * self.level}Leaving class {context[-1]}: {".".join(context)}')
        
    def enter_function(self, node, context):
        print(f'{"   " * self.level}Entering function {context[-1]}: {".".join(context)}')
        code_body = node.text.decode("utf-8")
        print(code_body)
        self.level += 1

    def leave_function(self, node, context):
        self.level -= 1
        print(f'{"   " * self.level}Leaving function {context[-1]}: {".".join(context)}')
        
    def enter_other(self, node, context):
        print(f'{"   " * self.level}{node.type} -- {node.text}')
        self.level += 1

    def leave_other(self, node, context):
        self.level -= 1


def transform(source_code, language, transformer):
    specification = languages[language]
    
    actions = {
        "class": (lambda n, c: transformer.enter_class(n, c), lambda n, c: transformer.leave_class(n, c)),
        "function": (lambda n, c: transformer.enter_function(n, c), lambda n, c: transformer.leave_function(n, c)),
        "other": (lambda n, c: transformer.enter_other(n, c), lambda n, c: transformer.leave_other(n, c))
    }
    
    context = []
    
    def parse(code, language):
        parser = get_parser(language)
        parser.set_language(get_language(language))

        tree = parser.parse(bytes(code, "utf8"))
        return tree.root_node

    def get_element(node, sequence):
        comparator = sequence[0] if callable(sequence[0]) else lambda nt: nt == sequence[0]
        next_node = next((child for child in node.children if comparator(child.type)), None)
        return next_node if len(sequence) == 1 else get_element(next_node, sequence[1:]) if next_node else None

    def traverse(node):
        node_type = specification.get(node.type)
        extended_context = False
        enter_action, leave_action = (None, None)

        if node_type and node_type[0] in actions:
            enter_action, leave_action = actions[node_type[0]]
        else:
            enter_action, leave_action = actions['other']
            
        if enter_action:
            if node_type:
                subtype = node_type[1]
                name_node = get_element(node, subtype)
                if name_node:
                    name = name_node.text.decode("utf-8") if isinstance(name_node.text, bytes) else name_node.text
                    context.append(name)
                    extended_context = True
            enter_action(node, context)                

        for child in node.children:
            traverse(child)
        
        if leave_action:
            leave_action(node, context)

        if extended_context:
            context.pop()

    root_node = parse(source_code, language)
    traverse(root_node) 
    

def print_functions(source_code, language):
    print('=' * 79)
    transform(source_code, language, PrintTransformer())
        

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

    print_functions(python_code, 'python')
    print_functions(c_code, 'cpp')


if __name__ == '__main__':
    main()
    