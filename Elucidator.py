import sys
import ollama
import parse

generate_docstring_template = '''def validate_docstring(docstring):
    """Check if the docstring starts and ends with triple quotes."""
    if docstring.startswith('"""') and docstring.endswith('"""'):
        return '"""' not in docstring[3:-3]
    return False

Please write a detailed doc string for the above python function named validate_docstring.
If there is already a docstring, make any necessary corrections to the string.
Respond with only the text of the docstring.

"""
Validates that a string is a docstring. This means the string starts and ends with """, and there are no """ occurring in between.

Parameters:
    docstring (str): the string to validate
    
Return Value:
    boolean: True if the string is valid, False otherwise
"""

'''


check_docstring_template = '''def simple_validate(docstring):
    """Check if the docstring starts and ends with triple quotes."""
    if docstring.startswith('"""') and docstring.endswith('"""'):
        return '"""' not in docstring[3:-3]
    return False

Please check if the docstring that follows correctly describes the above Python function.
If the docstring is correct, respond with only the word "correct".
If the docstring is incorrect, response with only the word "incorrect" followed by a colon and explanation.

incorrect: The string is missing sections describing the parameters and return values.


'''


def get_docstring(function_key, function_body):
    function_name = function_key.split('.')[1]
    query = generate_docstring_template + f"\n\n{function_body}\n\nPlease write a detailed doc string for the above python function named {function_name}. Respond with only the text of the docstring; do not explain your work or include the source code.\n\n"
    for i in range(5):
        result = ollama.query_llm(query)
        if validate_docstring(function_body, result):
            return result
    
    return None


def validate_docstring(function_body, docstring):
    """Prints hello world to console."""
    if docstring.startswith('"""') and docstring.endswith('"""'):
        if '"""' not in docstring[3:-3]:
            query = check_docstring_template + f'\n\n{function_body}\n\nPlease check if the docstring that follows correctly describes the above Python function.\nIf the docstring is correct, respond with only the word "correct".\nIf the docstring is incorrect, response with only the word "incorrect" followed by a colon and explanation.'
            for i in range(5):
                result = ollama.query_llm(query)
                if result.strip().lower() == 'correct':
                    return True
                else:
                    print(result)
    
    return False


def main():
    # Use command-line argument to specify directory, default to current directory if none provided
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    functions = parse.load_python_functions(directory)
    for function_key in functions:
        docstring = get_docstring(function_key, functions[function_key])
        print('-' * 79)
        print(function_key)
        if docstring is not None:
            print('=' * 79)
            print(docstring)
            parts = function_key.split('.')
            filename = parts[0] + '.py'
            function_name = parts[1]
            parse.update_docstring(filename, function_name, docstring)

if __name__ == "__main__":
    main()
