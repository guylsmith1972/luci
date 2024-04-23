import ollama
import parse
import sys
generate_docstring_template = """def update_docstring(filename, function_name, new_docstring):
    ""\" Hello, world! ""\"
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

Please write a detailed doc string for the above python function named update_docstring.
If there is already a docstring, make any necessary corrections to the string.
Respond with only the text of the docstring.

    ""\"
    Updates the docstring of a specified function within a Python source file.

    This function reads a Python file, parses its source code to find the
    function with the given name, and then replaces its existing docstring
    with the provided new docstring. The updated source code is then written
    back to the same file, effectively updating the file in-place.

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
    >>> update_docstring("example.py", "my_function", "This is the new docstring.")
    # This will update the docstring of `my_function` in `example.py` file.

    Note:
    This function does not handle functions defined within classes or other
    scopes; only top-level functions are supported.
    ""\"

"""
check_docstring_template = """def simple_validate(docstring):
    if docstring.startswith('""\"') and docstring.endswith('""\"'):
        return '""\"' not in docstring[3:-3]
    return False

Please check if the docstring that follows correctly describes the above Python function.
If the docstring is correct, respond with only the word "correct".
If the docstring is incorrect, response with only the word "incorrect" followed by a colon and explanation.

docstring: ""\"Check if the docstring starts and ends with triple quotes.""\"

incorrect: The string is missing sections describing the parameters and return values.


"""


def get_docstring(function_key, function_body):
    """
Generates a docstring for a given Python function by querying a language model.

This function takes the name and body of a Python function as input, uses them to generate a prompt for a language model, and then asks the model to provide a detailed docstring for the function. The generated docstring is validated against the original function body, and if it meets certain criteria, it is returned. If not, the function tries again up to five times.

Parameters:
function_key (str): A string representing the key of the Python function, used to extract its name.
function_body (str): The source code of the Python function, without its docstring.

Returns:
str: The generated and validated docstring for the given Python function. If no valid docstring is found after five attempts, the function returns None.

Example:
>>> get_docstring("my_function", "This is the function body.")
# This will generate a docstring for `my_function` based on its source code.
"""
    function_name = function_key.split('|')[1].split('.')[-1]
    query = generate_docstring_template + f"""

{function_body}

Please write a detailed doc string for the above python function named {function_name}. Respond with only the text of the docstring; do not explain your work or include the source code.

"""
    for i in range(5):
        result = ollama.query_llm(query)
        if validate_docstring(function_body, result):
            return result
    return None


def validate_docstring(function_body, docstring):
    """Prints hello world to console."""
    if docstring.startswith('"""') and docstring.endswith('"""'):
        if '"""' not in docstring[3:-3]:
            query = check_docstring_template + f"""

{function_body}

Please check if the docstring that follows correctly describes the above Python function.
If the docstring is correct, respond with only the word "correct".
If the docstring is incorrect, response with only the word "incorrect" followed by a colon and explanation.

docstring: {docstring}

"""
            for i in range(5):
                result = ollama.query_llm(query)
                if result.strip().lower().startswith('correct'):
                    return True
                else:
                    pass
    return False


def main():
    """
Main entry point for the program.

This function is the central hub that orchestrates the updating of docstrings in Python files.
It takes command-line arguments to specify the directory containing the files to be processed, 
and iterates over each file, extracting functions and their corresponding docstrings. 
For each function, it checks if a docstring exists and updates it using the `update_docstring` function.

Parameters:
directory (str): The directory path where Python source files are located.
                If not provided, defaults to the current working directory.

Raises:
None: This function does not raise any specific exceptions. However, 
      any exceptions raised by its internal functions will be propagated.

Returns:
None: The function does not return any value; it modifies the files directly.
"""
    directory = sys.argv[1] if len(sys.argv) > 1 else '.'
    functions = parse.extract_functions(directory)
    for function_key in functions:
        docstring = get_docstring(function_key, functions[function_key])
        if docstring is not None:
            parts = function_key.split('.')
            parse.update_docstring(function_key, docstring)


if __name__ == '__main__':
    main()
