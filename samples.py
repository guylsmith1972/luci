example_json = '''
{
    "functionName": "update_docstring",
    "summary": "Updates the docstring of a specified function within a Python file.",
    "description": "This function reads a Python file, modifies the docstring of a specified function using the abstract syntax tree (AST), and writes the modified code back to the file. It ensures that the new docstring is correctly inserted at the beginning of the function definition.",
    "parameters": [
        {
            "name": "filename",
            "type": "string",
            "description": "The path to the Python file containing the function whose docstring needs updating.",
            "required": true,
            "defaultValue": null
        },
        {
            "name": "function_name",
            "type": "string",
            "description": "The name of the function whose docstring is to be updated.",
            "required": true,
            "defaultValue": null
        },
        {
            "name": "new_docstring",
            "type": "string",
            "description": "The new docstring text that will replace the existing docstring of the function.",
            "required": true,
            "defaultValue": null
        }
    ],
    "returns": [
        {
            "type": "void",
            "description": "Does not return any value. The function's primary effect is the modification of the source code file."
        }
    ],
    "errors": [
        {
            "name": "FileNotFoundError",
            "description": "Thrown if the specified file cannot be found at the given path."
        },
        {
            "name": "SyntaxError",
            "description": "Thrown if the source code file contains syntax errors that prevent AST parsing."
        }
    ],
    "examples": [
        {
            "description": "Updates the docstring of the function 'my_function' in 'example.py' to 'This is a new docstring.'",
            "code": "update_docstring('example.py', 'my_function', 'This is a new docstring.')"
        }
    ],
    "notes": [
        "This function relies on the 'ast' and 'astor' libraries to parse and generate Python source code, respectively. Ensure these libraries are installed and the source file is syntactically correct for proper operation."
    ]
}
'''

example_function = '''
def update_docstring(filename, function_name, new_docstring):
    """ Hello, world! """
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
'''
