from tokenize import Special


def generate_docstring_query(code, example_function, example_docstring):
    """
    This function generates a docstring for another function. It takes in some code, an example function name, and an example docstring as parameters.
    Parameters:
    code (str): The source code of the original function that needs to be documented.
    example_function (str): The name of the example function whose docstring is provided.
    example_docstring (str): The content of the example docstring that should be used as a template.
    
    Returns:
    query (str): The generated query string with the instructions and the provided code, function name, and docstring."""
    instructions = 'Write a docstring for the following function. Do not explain your work. Use """ as the docstring delimter. Respond with only the text of the docstring.\n\n'
    query = instructions
    query += example_function
    query += '\n\n"""'
    query += example_docstring
    query += '"""\n\n'
    query += instructions
    query += code
    return query


def generate_validation_query(code, current_docstring, example_docstring):
    """
    Generate a validation query based on a given function's code and two sample docstrings. This query helps to determine if the actual function's docstring meets certain criteria.
    The query presents an example of well-written docstring, the target function's code, and then asks the user to check whether the actual function's docstring accurately reflects its code and follows the same pattern as the example.
    
    Parameters:
    code (str): The source code of the target function.
    current_docstring (str): The actual docstring of the target function.
    example_docstring (str): A sample well-written docstring for a Python function.
    
    Returns:
    query (str): A text-based query that can be used to validate whether the actual function's docstring meets certain criteria."""
    instructions = f'Check whether the docstring in the following function meets the following critera:\n\n'
    instructions += f'1. The docstring in the function must accurately reflect the code in the function.\n'
    instructions += f'2. The docstring in the function should follow the pattern shown in the example docstring.\n'
    instructions += f'\nIf both point 1 and point 2 are met, reply with "ANSWER: correct"\n'
    instructions += f'If either point fails, respond with "ANSWER: incorrect: " followed by an explanation.\n\n'

    query = f'Here is an example of a well-written docstring for a Python function:\n\n"""{example_docstring}\n"""\n\n'
    query += f'Examine the following code:\n'
    query += f'def load_file(filename):\n'
    query += f'    """ List all files in a directory """\n'
    query += f'    with open(filename, "r") as infile:\n'
    query += f'        file_content = infile.read()\n'
    query += f'    return file_content\n\n'
    query += instructions
    query += f'ANSWER: incorrect: The function does not list files in a directory, it loads a file and returns the contents. It also does not adhere to the style conventions for docstrings.\n\n'
    query += f'Examine the following code:\n'
    query += f'{code}\n\n'
    query += instructions

    return query


def generate_docstring(ollama, function_path, function_name, function_body, current_docstring, options, special_instructions=None):
    """
    Generates a docstring for a given Python function based on an AI model's query response.
    
    This function uses the provided OLLAMA API client to query its natural language processing capabilities and generates a docstring based on the input parameters. The generated docstring is then validated against the original function's body and options. If the validation passes, the function returns the generated docstring; otherwise, it attempts to generate a new one up to the specified number of times before returning None.
    
    Parameters:
    ollama (OLLAMA API client): The OLLAMA API client instance used for querying.
    function_name (str): The name of the function for which the docstring is being generated.
    function_body (str): The source code body of the function, excluding its header and docstring.
    options (dict): A dictionary containing options for generating the docstring, such as example_function and example_docstring.
    
    Returns:
    str: The generated docstring if it passes validation; otherwise, None.
    Raises:
    None
    Note:
    This function is highly dependent on the OLLAMA API's capabilities and may not work well with all types of functions or inputs. It's recommended to test this function thoroughly before using it in production code."""
    query = generate_docstring_query(function_body, options.example_function, options.example_docstring)
    if special_instructions is not None:
        query += '\n\nSpecial Instructions:\n'
        query += special_instructions
        
    for i in range(options.attempts):
        docstring = ollama.query(query)
        if validate_docstring(ollama, function_name, function_body, docstring, options):
            return docstring.strip('"').strip("'")
    return None


def validate_docstring(ollama, function_name, function_body, docstring, options):
    """Validates the correctness of a given docstring against an AI-based language model.
    This function takes in a docstring and compares it to the expected output from an AI-based
    language model. If the docstring is correct, returns True along with any additional result;
    otherwise, returns False along with the error report.
    
    Parameters:
    ollama (Object): The AI-based language model used for validation.
    function_name (str): The name of the function whose docstring is being validated.
    function_body (str): The source code of the function itself.
    docstring (str): The actual docstring to be validated.
    options (Object): A dictionary containing various options, including example_docstring and attempts.
    
    Returns:
    Tuple[bool, str]: Returns True if the docstring is correct, False otherwise along with an error report."""
    report = None
    if not docstring.startswith('"""') or not docstring.endswith('"""') or '"""' in docstring[3:-3]:
        report = f'Failed simple string test (incorrect quoting): {docstring}'
    else:
        query = generate_validation_query(function_body, docstring, options.example_docstring)
        for i in range(options.attempts):
            result = ollama.query(query)
            parts = result.lower().split('answer:')
            if len(parts) != 2:
                return False, result
            parts = parts[1].split(' \t\r\n')
            answer = parts[0].strip()
            print(f'first thing after answer: {answer}')
            if answer == 'correct':
                return True, result
            report = result

    return False, report
