from tree_sitter_languages import get_language, get_parser
import languages


def transform(source_code, language, transformer):
    specification = languages.language_specifications[language]
    
    actions = {
        "class": (lambda n, c, b: transformer.enter_class(n, c, b), lambda n, c, b: transformer.leave_class(n, c, b)),
        "function": (lambda n, c, b: transformer.enter_function(n, c, b), lambda n, c, b: transformer.leave_function(n, c, b)),
        "other": (lambda n, c, b: transformer.enter_other(n, c, b), lambda n, c, b: transformer.leave_other(n, c, b))
    }
    
    context = []
    
    def find_node_by_sequence(node, sequence):
        comparator = sequence[0] if callable(sequence[0]) else lambda nt: nt == sequence[0]
        next_node = next((child for child in node.children if comparator(child.type)), None)
        return next_node if len(sequence) == 1 else find_node_by_sequence(next_node, sequence[1:]) if next_node else None

    def traverse(node):
        node_type = specification.get(node.type)
        extended_context = False
        enter_action, leave_action = actions[node_type[0]] if (node_type and node_type[0] in actions) else actions['other']        
        code_body = node.text.decode("utf-8")
            
        if node_type:
            subtype = node_type[1]
            name_node = find_node_by_sequence(node, subtype)
            if name_node:
                name = name_node.text.decode("utf-8") if isinstance(name_node.text, bytes) else name_node.text
                context.append(name)
                extended_context = True
                
        enter_action(node, context, code_body)                
        for child in node.children:
            traverse(child)
        leave_action(node, context, code_body)

        if extended_context:
            context.pop()

    parser = get_parser(language)
    parser.set_language(get_language(language))
    tree = parser.parse(bytes(source_code, "utf8"))
    traverse(tree.root_node) 
