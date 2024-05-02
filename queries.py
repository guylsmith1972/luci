import re


def generate_docstring_query(code, example_function, example_docstring):
    """
    This function generates a docstring query for the given code, example function
    and example docstring.

    Parameters:
      code (str): The source code of the Python file where the function's docstring
    needs to be updated.
      example_function (str): The name of the function whose docstring needs
    updating.
      example_docstring (str): The new docstring content that will replace the
    existing docstring of the specified function.

    Returns:
      str: The generated docstring query.
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
    This function generates a validation query for checking whether the docstring of
    a given Python function meets certain criteria.
    The function takes three parameters: the code of the function, its current
    docstring, and an example of a well-written docstring.
    It returns a query that contains the function's code, instructions for
    evaluation, and an example of a correct docstring.

    Parameters:
      code (str): The source code of the Python function whose docstring needs to be
    validated.
      current_docstring (str): The existing docstring of the function being
    evaluated.
      example_docstring (str): A well-written docstring that serves as an example
    for comparison.

    Returns:
      query (str): A string containing the validation query.
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


def generate_docstring(ollama, function_path, function_name, function_body, current_docstring, options, logger, special_instructions=None):
    """
    Generates a docstring for a given function using Ollama and
    updates it accordingly.

    This function takes in several parameters: the Ollama instance, the path to the
    function, the name of the function, the body of the function, the current
    docstring, options for the query, and special instructions. It uses these inputs
    to generate a query that is then passed to Ollama to generate a new docstring.

    The generated docstring is validated against certain criteria before it is
    returned. If the generated docstring does not meet the validation criteria after
    a specified number of attempts, None is returned.

    This function can be used to automatically generate high-quality docstrings for
    Python functions using Ollama.

    Parameters:
      ollama (Ollama instance): The Ollama instance used to generate the
    docstring.
      function_path (str): The path to the function in the source code.
      function_name (str): The name of the function for which the docstring is being
    generated.
      function_body (str): The body of the function, excluding any docstrings or
    comments.
      current_docstring (str): The current docstring of the function, if any.
      options (dict): A dictionary containing options for the query, such as example
    functions and docstrings.
      special_instructions (str): Special instructions that should be included in
    the generated docstring.

    Returns:
      str: The generated docstring for the given function. If no valid docstring
    could be generated after a specified number of attempts, None is returned.
    """
    query = generate_docstring_query(function_body, options.example_function, options.example_docstring)
    if special_instructions is not None:
        query += '\n\nSpecial Instructions:\n'
        query += special_instructions
        
    for i in range(options.attempts):
        docstring = ollama.query(query, options, logger)
        if validate_docstring(ollama, function_name, function_body, docstring, options, logger):
            return docstring.strip('"').strip("'")
    return None


def validate_docstring(ollama, function_name, function_body, docstring, options, logger):
    """
    Validates the provided docstring for a given function.
    Checks if the docstring is syntactically correct by attempting to execute it,
    and then performs a series of checks on its contents. The validation process
    can be customized with options.

    Parameters:
      ollama (object): An OLLAMA instance used for querying.
      function_name (str): The name of the function whose docstring is being
    validated.
      function_body (str): The source code of the function.
      docstring (str): The docstring content to be validated.
      options (dict): A dictionary containing customization options.

    Returns:
      tuple: A tuple containing a boolean indicating whether the docstring is valid
             and a report message detailing the validation result.
    """
    report = None

    try:
        # Attempt to parse the dummy function code to see if the docstring is syntactically correct
        dummy_code = f'def dummy_function():\n    {docstring}\n    pass\n\ndummy_function()\n'
        exec(dummy_code, {})
    except SyntaxError:
        return False, 'Docstring syntax not valid'

    if not docstring.startswith('"""') or not docstring.endswith('"""') or '"""' in docstring[3:-3]:
        report = f'Failed simple string test (incorrect quoting): {docstring}'
    else:
        query = generate_validation_query(function_body, docstring, options.example_docstring)
        for i in range(options.attempts):
            result = ollama.query(query, options, logger)
            # Pattern to find 'ANSWER:' followed by any amount of whitespace and then a word
            pattern = r'ANSWER:\s*(\w+)'
            # Use re.findall to extract all matching words
            answers = re.findall(pattern, result)
            valid = len(answers) > 0
            for answer in answers:
                if answer.lower() != 'correct':
                    valid = False
                    break
            if valid:
                return True, result
            report = result

    return False, report
