from tokenize import Special


def generate_docstring_query(code, example_function, example_docstring):
    """
    This function generates a docstring query for the given code, example function,
    and example docstring.
    The generated query is designed to test the update_docstring function by
    providing a code snippet that requires updating its own docstring.

    Parameters:
    code (str): The Python code that will be updated with the new docstring.
    example_function (str): The name of the function whose existing docstring should
    be replaced with the provided example docstring.
    example_docstring (str): The new docstring content that will replace the
    existing docstring of the specified function.

    Returns:
    query (str): A string representing the generated docstring query.
    """
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
    Checks whether a given function's docstring meets certain criteria.
    This function generates a validation query based on the provided code, current
    docstring, and example docstring.
    The query is designed to test if the docstring accurately reflects the code in
    the function and follows a specific pattern.

    Parameters:
    code (str): The Python code that the docstring should be validated against.
    current_docstring (str): The existing docstring of the function being validated.
    example_docstring (str): A well-written example docstring that the current
    docstring should match.

    Returns:
    query (str): The validation query to be executed. This query is designed to test
    if the docstring meets the specified criteria.
    """
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
    Generates a docstring for a Python function.

    Parameters:
    ollama (object): An object that generates the initial query.
    function_path (str): The path of the function.
    function_name (str): The name of the function.
    function_body (str): The body of the function.
    current_docstring (str): The current docstring for the function.
    options (dict): A dictionary containing options such as example_function and
    example_docstring.
    special_instructions (str): Special instructions to be included in the query.

    Returns:
    str: The generated docstring. If no suitable docstring is found, returns None.

    Raises:
    None: This function does not raise any exceptions.
    """
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
    """
    Validates the given docstring against a specified ollama query and options.

    Parameters:
    ollama (obj): The OLLAMA object used for querying.
    function_name (str): The name of the function whose docstring is being
    validated.
    function_body (str): The source code of the function, not including its
    docstring.
    docstring (str): The docstring to be validated.
    options (dict): A dictionary containing options for validation.

    Returns:
    tuple: A tuple containing a boolean indicating whether the validation was
    successful,
           and a report string describing the result of the validation process.
           If the validation failed, the report will contain information about what
    went wrong.
    """
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
            if answer == 'correct':
                return True, result
            report = result

    return False, report
