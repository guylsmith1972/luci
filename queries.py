


def generate_docstring_query(code, example_function, example_docstring):
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
    instructions = f'Check whether the docstring in the following function meets the following critera:\n\n'
    instructions += f'1. The docstring in the function must accurately reflect the code in the function.\n'
    instructions += f'2. The docstring in the function should follow the pattern shown in the example docstring.\n'
    instructions += f'\nIf both point 1 and point 2 are met, reply with just the single word "correct"\n'
    instructions += f'If either point fails, respond with "incorrect: " followed by an explanation.\n\n'

    query = f'Here is an example of a well-written docstring for a Python function:\n\n"""{example_docstring}\n"""\n\n'
    query += f'Examine the following code:\n'
    query += f'def load_file(filename):\n'
    query += f'    """ List all files in a directory """\n'
    query += f'    with open(filename, "r") as infile:\n'
    query += f'        file_content = infile.read()\n'
    query += f'    return file_content\n\n'
    query += instructions
    query += f'incorrect: The function does not list files in a directory, it loads a file and returns the contents. It also does not adhere to the style conventions for docstrings.\n\n'
    query += f'Examine the following code:\n'
    query += f'{code}\n\n'
    query += instructions

    return query
