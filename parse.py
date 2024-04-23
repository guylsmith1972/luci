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

def load_python_functions(directory):
    """Load all Python files and create a map of all functions."""
    functions_map = {}
    for filename in os.listdir(directory):
        if filename.endswith(".py"):
            file_path = os.path.join(directory, filename)
            with open(file_path, "r") as file:
                source_code = file.read()

            # Parse the Python file and manually track parent nodes
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child.parent = node  # Manually assign parent

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not isinstance(getattr(node, 'parent', None), ast.FunctionDef):
                        function_name = node.name
                        parameters = get_function_parameters(node)
                        function_code = get_function_code(node, source_code)
                        # Create the map key
                        key = f"{filename[:-3]}.{function_name}.{parameters}"
                        functions_map[key] = function_code
    return functions_map


def update_docstring(filename, function_name, new_docstring):
    with open(filename, "r") as file:
        source_code = file.read()

    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            # Create a new docstring node
            node.body.insert(0, ast.Expr(value=ast.Str(s=new_docstring)))
            break
    
    # Write back the modified code
    with open(filename, "w") as file:
        file.write(astor.to_source(tree))

# Example usage:
update_docstring('example.py', 'my_function', 'This is the new docstring.')
