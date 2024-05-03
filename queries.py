import formatting
import re


def generate_docstring_query(code, example_function, example_json):
    """
    Generates a JSON description of another function's documentation, including
    parameters, returns, errors, and examples.

    This function takes in a code snippet, an example function, and its
    corresponding JSON template. It then constructs a query string that can be used
    to generate the documentation for the example function.

    Parameters:
    code (string): The code snippet that defines the function whose documentation is
                being generated.
    example_function (string): The name of the example function whose documentation
                is being generated.
    example_json (string): The JSON template that defines the format of the
                generated documentation.

    Returns:
    string: A query string that can be used to generate the documentation for the
            example function.

    Errors:
    ValueError: Thrown if the code snippet is invalid or cannot be parsed into a
                JSON template.

    Examples:
    Generates a JSON description of the 'update_docstring' function.
     generate_docstring_query('example code', 'update_docstring', '...')'

    Notes:
    This function relies on the formatting and JSON template parsing to construct
     the query string. Ensure that the input code snippet is correct and the JSON
     template is well-formed for proper operation.
    """
    query = 'Refer to this JSON template for the following tasks:\n\n'    
    query += formatting.json_template
    query += '\n'
    
    instructions = 'Generate a JSON description of the following function:\n\n'
    query += instructions
    query += example_function
    query += '\n\n'
    query += example_json
    query += '\n\n'
    query += instructions
    query += code
    return query


def generate_validation_query(code, example_json):
    """
    Creates a validation query to ensure that the docstring in a given code snippet
    accurately reflects its content and adheres to specific guidelines.

    This function generates a query that checks if the docstring in a piece of code
    is accurate, consistent with comments, and only discusses visible functionality.
    It also provides an example code snippet that does not adhere to these
    guidelines, making it an 'incorrect' answer.

    Parameters:
    code (string): The code snippet whose docstring is being validated.
    example_json (string): JSON data containing an example of incorrect validation
                (i.e., a function that does not list files in a directory).

    Returns:
    string: The generated validation query, which includes instructions and the
            example code snippet.

    Errors:
    None: No specific errors are documented for this function.

    Examples:
    Generates a validation query for the given code snippet.
     generate_validation_query('example_code', 'incorrect_example')

    Notes:
    This function is designed to provide a framework for validating docstrings in
     Python code. It may not cover all possible edge cases or error scenarios.
    """
    instructions = f'Examine the following code and check that it conforms with these instructions:\n'
    instructions += f'1. The docstring in the function must accurately reflect the code in the function.\n'
    instructions += f'2. The docstring is consistent with any comments in the code.\n'
    instructions += f'3. The docstring only discusses what is actually visible in the code. It should not make claims about functionality that is not visible in the code."\n'
    instructions += f'\nIf all points are met, reply with "ANSWER: correct"\n'
    instructions += f'If any point fails, respond with "ANSWER: incorrect: " followed by an explanation.\n\n'

    query = instructions
    query += f'def load_file(filename):\n'
    query += f'    """ List all files in a directory """\n'
    query += f'    with open(filename, "r") as infile:\n'
    query += f'        file_content = infile.read()\n'
    query += f'    return file_content\n\n'
    query += f'ANSWER: incorrect: The function does not list files in a directory. It loads a file and returns the contents. It also does not adhere to the style conventions for docstrings.\n\n'
    query += instructions
    query += f'{code}\n\n'

    return query


def generate_docstring(ollama, function_path, function_name, function_body, current_docstring, options, logger, special_instructions=None):
    """
    Generates a docstring for a given function using OLLAMA and formatting.

    This function takes in various parameters to generate a docstring. It queries
    OLLAMA, formats the result, validates it, and returns the final docstring. If
    any exceptions occur during the process, they are logged but not propagated.

    Parameters:
    ollama (object): The OLLAMA object used to query for the docstring.
    function_path (string): The path to the function whose docstring is being
                generated.
    function_name (string): The name of the function for which the docstring is
                being generated.
    function_body (string): The body of the function whose docstring is being
                generated.
    current_docstring (string): The current docstring for the function, which may be
                updated.
    options (object): Options used to customize the generation process.
    logger (object): A logger object for logging debug messages.
    special_instructions (string): Optional special instructions to be included in
                the generated docstring.

    Returns:
    string: The generated docstring for the function.

    Errors:
    Exception: Thrown if an exception occurs during the generation process, which is
               logged but not propagated.

    Examples:
    Generates a docstring for a function named 'my_function' in a file at
     'path/to/file.py'.   generate_docstring(ollama, 'path/to/file.py',
     'my_function', function_body, current_docstring, options, logger)

    Notes:
    This function uses OLLAMA and formatting libraries to generate the docstring.
     Ensure these libraries are installed for proper operation.
    """
    query = generate_docstring_query(function_body, options.example_function, options.example_json)
    if special_instructions is not None:
        query += '\n\nSpecial Instructions:\n'
        query += special_instructions
     
    for i in range(options.attempts):
        try:
            docstring = ollama.query(query, options, logger)
            formatted = formatting.generate_documentation(formatting.extract_json(docstring), formatting.format_spec_python)
            if validate_docstring(ollama, function_name, function_body, formatted, options, logger):
                return formatted.strip('"').strip("'")
        except Exception as e:
            # We don't care about exceptions here, since we already just try again when we get bad results. Let's just log it for debug mode.
            logger.debug(f'Exception: {str(e)}')
    return None


def validate_docstring(ollama, function_name, function_body, docstring, options, logger):
    """
    Validates whether a given docstring is syntactically correct and matches certain
    criteria.

    This function takes in various parameters such as dummy code, options, and
    logger. It attempts to parse the dummy code to check if the docstring is
    syntactically valid. If it's not, it returns False along with an error message.
    Then, it checks if the docstring meets certain criteria by querying Ollama (a
    search engine) for answers. If the query results in a valid answer, it returns
    True along with the result. Otherwise, it reports the failure and returns False.

    Parameters:
    ollama (object): The Ollama search engine instance used for validation queries.
    function_name (string): The name of the function whose docstring is being
                validated.
    function_body (string): The code body of the function being validated.
    docstring (string): The docstring to be validated.
    options (object): The options used for the validation process, including
                attempts and example JSON data.
    logger (object): The logger instance used to log messages during the validation
                process.

    Returns:
    boolean: A boolean indicating whether the docstring is valid or not.
    string: An error message or report if the validation fails.

    Errors:
    SyntaxError: Thrown if the dummy code contains syntax errors during parsing.

    Examples:
    Validates the docstring of a function with the name 'my_function' against
     certain criteria.   validate_docstring(ollama, 'my_function', function_body,
     docstring, options, logger)

    Notes:
    This function relies on the Ollama search engine for validation queries. Ensure
     that it is properly configured and functioning correctly.
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
        query = generate_validation_query(function_body, options.example_json)
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
