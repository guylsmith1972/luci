from tree_sitter_languages import get_language, get_parser
import languages


def transform(source_code, language, transformer):
    """
    Transforms a source code file according to a given language and transformer.

    This function parses the source code, applies transformation actions based on
    the specified language and transformer, and recursively traverses the abstract
    syntax tree (AST) to apply these actions. It ensures that the transformer is
    properly called before and after entering each node in the AST, as well as after
    leaving it.

    Parameters:
    source_code (string): The source code text to be transformed.
    language (string): The language of the source code, used to determine
                transformation actions.
    transformer (object): An object that defines transformation actions for the
                given language. It should have methods named 'enter_class',
                'leave_class', 'enter_function', 'leave_function', and
                'enter_other'/'leave_other'.

    Returns:
    void: Does not return any value. The function's primary effect is the
          transformation of the source code.

    Errors:
    SyntaxError: Thrown if the source code contains syntax errors that prevent
                parsing.

    Examples:
    Translates a Python file using a given transformer.
     transform(source_code='example.py', language='python', transformer=transformer)
    """
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
            "code_body": code_body,
            "name": name,
            "node": node
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
