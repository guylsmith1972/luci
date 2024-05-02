example_docstring = '''
"""
Updates the docstring of a specified function within a Python source file.

This function reads a Python file, parses its source code to find the function
with the given name, and then replaces its existing docstring with the
provided new docstring. The updated source code is then written back to the
same file, effectively updating the file in-place.

Parameters:
  filename (str): The path to the Python source file where the function
                  whose docstring is to be updated is located.
  function_name (str): The name of the function whose docstring needs
                       updating. The function should be defined at the
                       top level of the module (not nested inside other
                       classes or functions).
  new_docstring (str): The new docstring content that will replace the
                       existing docstring of the specified function.

Raises:
  FileNotFoundError: If the file specified by `filename` does not exist.
  SyntaxError: If the source code in `filename` is not valid Python code.
  ValueError: If no function with the name `function_name` exists in the
              file, or if the file contains no functions at all.

Returns:
  None: The function does not return any value. It modifies the file directly.

Example:
> update_docstring("example.py", "my_function", "This is the new docstring.")
# This will update the docstring of `my_function` in `example.py` file.

Note:
  This function does not handle functions defined within classes or other
  scopes; only top-level functions are supported.
"""
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