from tree_sitter_languages import get_language, get_parser
import languages


def transform(source_code, language, transformer):
    specification = languages.language_specifications[language]
    
    actions = {
        "class": (lambda args: transformer.enter_class(args), lambda args: transformer.leave_class(args)),
        "function": (lambda args: transformer.enter_function(args), lambda args: transformer.leave_function(args)),
        "other": (lambda args: transformer.enter_other(args), lambda args: transformer.leave_other(args))
    }
    
    def find_node_by_sequence(node, sequence):
        comparator = sequence[0] if callable(sequence[0]) else lambda nt: nt == sequence[0]
        next_node = next((child for child in node.children if comparator(child.type)), None)
        return next_node if len(sequence) == 1 else find_node_by_sequence(next_node, sequence[1:]) if next_node else None

    def traverse(node):
        node_type = specification.get(node.type)
        enter_action, leave_action = actions[node_type[0]] if (node_type and node_type[0] in actions) else actions['other']        
        code_body = node.text.decode("utf-8")
        name = None
            
        if node_type:
            subtype = node_type[1]
            name_node = find_node_by_sequence(node, subtype)
            if name_node:
                name = name_node.text.decode("utf-8") if isinstance(name_node.text, bytes) else name_node.text
                
        arguments = {
            "name": name,
            "node": node,
            "code_body": code_body
            }
                
        transformer.before_enter(arguments)
        enter_action(arguments)                
        transformer.after_enter(arguments)
        for child in node.children:
            traverse(child)
        transformer.before_leave(arguments)
        leave_action(arguments)
        transformer.after_leave(arguments)

    parser = get_parser(language)
    parser.set_language(get_language(language))
    tree = parser.parse(bytes(source_code, "utf8"))
    traverse(tree.root_node) 
