import os
import ast
import astor


def get_function_code(node, source_code):
    """Extract function code from the AST node."""
    return ast.get_source_segment(source_code, node)


def get_function_parameters(function_node):
    """Extract function parameters into a readable format."""
    return ','.join(
        f"{arg.arg}={ast.unparse(arg.annotation)}" if arg.annotation else arg.arg
        for arg in function_node.args.args
    )

def extract_functions(base_directory):
    """Load all Python files and create a map of all functions, including directory paths."""
    functions_map = {}
    for root, dirs, files in os.walk(base_directory):
        for filename in files:
            if filename.endswith(".py"):
                file_path = os.path.join(root, filename)
                with open(file_path, "r") as file:
                    source_code = file.read()

                tree = ast.parse(source_code)
                for node in ast.walk(tree):
                    for child in ast.iter_child_nodes(node):
                        child.parent = node  # Manually assign parent

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check if the function is inside a class
                        parent = getattr(node, 'parent', None)
                        if isinstance(parent, ast.ClassDef):
                            # It's a method, prepend class name
                            function_name = f"{parent.name}:{node.name}"
                        else:
                            function_name = node.name

                        parameters = get_function_parameters(node)
                        function_code = get_function_code(node, source_code)
                        key = f"{file_path}|{function_name}|{parameters}"
                        functions_map[key] = function_code
    return functions_map


def update_docstring(function_key, new_docstring):
    print(f'updating {function_key}')

    # Attempt to parse the function key to extract directory path, class name (if any), and function name
    parts = function_key.split('|')
    if len(parts) < 3:
        raise ValueError("Invalid function key format. Expected pattern filepath|function_id|parameters")

    # Combine all parts except the last two (which are function name and parameters)
    path = parts[0]
    function_parts = parts[1].split(':')  # Function name is second to last
    function_name = function_parts[-1]
    class_name = None if len(function_parts) == 1 else function_parts[0]

    try:
        with open(path, "r") as file:
            source_code = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"No such file or directory: {path}")

    # Parse the source code into an AST
    tree = ast.parse(source_code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            # Check if the function is in the correct class if class_name is not None
            if class_name:
                parent = getattr(node, 'parent', None)
                if not (isinstance(parent, ast.ClassDef) and parent.name == class_name):
                    continue  # Skip, not the right method

            found = True
            # Check if the first element in the function body is a docstring
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                # Remove existing docstring
                node.body.pop(0)
            # Insert new docstring
            new_doc_expr = ast.Expr(value=ast.Str(s=new_docstring.strip('"').strip("'")))
            node.body.insert(0, new_doc_expr)
            break

    if not found:
        raise ValueError(f"Function or method not found with the provided key {class_name}:{function_name}.")

    # Write the modified code back to the file
    with open(path, "w") as file:
        file.write(astor.to_source(tree))
        