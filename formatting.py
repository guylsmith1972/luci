import json
import re
import textwrap

json_template = '''
{
  "functionName": "exampleFunction",
  "summary": "Provides a quick overview of the function's purpose and main actions.",
  "description": "Detailed description of what the function does, its purpose within the program, and any specific behaviors it exhibits.",
  "parameters": [
    {
      "name": "param1",
      "type": "integer",
      "description": "Description of what this parameter represents and how it affects the function's operation.",
      "required": true,
      "defaultValue": null
    },
    {
      "name": "param2",
      "type": "string",
      "description": "Description of what this parameter represents and how it affects the function's operation.",
      "required": false,
      "defaultValue": "defaultString"
    }
  ],
  "returns": [
    {
        "type": "boolean",
        "description": "Description of the value returned by the function, including possible values and their meanings."
    },
    {
        "type": "float",
        "description": "Description of another value returned by the function, including possible values and their meanings."
    },
  ],
  "errors": [
    {
      "name": "ErrorType",
      "description": "Description of when and why this error might be thrown by the function."
    }
  ],
  "examples": [
    {
      "description": "A brief description of what this example demonstrates.",
      "code": "exampleFunction(42, 'example')"
    }
  ],
  "notes": [
    "Any additional notes or caveats about using the function, including performance considerations, side effects, or common pitfalls."
  ]
}
'''

format_spec_python = {
    "start_same_line": False,
    "start": "\"\"\"",
    "end": "\"\"\"",
    "line_prefix": "",
    "forbidden": ['"""', "'''"]
}

format_spec_c_multiline = {
    "start_same_line": True,
    "start": "/* ",
    "end": " */",
    "line_prefix": " * ",
    "forbidden": ["*/"]
}

format_spec_c_slashes = {
    "start_same_line": True,
    "start": "// ",
    "end": "",
    "line_prefix": "// ",
    "forbidden": []
}

format_spec_c = format_spec_c_multiline


def extract_json(text):
    """
    Extracts a JSON object from a given string, assuming it starts with '{' and ends
    with '}'.

    This function finds the first occurrence of '{' in the input text, then searches
    for the last occurrence of '}' to determine the bounds of the potential JSON
    object. It checks if the indices are valid and that the start index comes before
    the end index. If the JSON is valid, it returns the parsed JSON object;
    otherwise, it returns None.

    Parameters:
    text (string): The input string containing the potential JSON object to extract.

    Returns:
    object: The extracted JSON object, or None if the input text does not contain a
            valid JSON object.

    Examples:
    Extracts the JSON object from a string containing it.   extract_json('{'key':
                'value'}')
    """
    start = text.find('{')  # Find the first occurrence of '{'
    end = text.rfind('}')  # Find the last occurrence of '}'
    
    if start == -1 or end == -1 or start > end:
        return None  # Ensure valid indices and that start comes before end

    return json.loads(text[start:end+1])


def generate_documentation(func_data, format_spec, max_width=80, max_indent=12):
    """
    Generates documentation for a given function based on its metadata and
    formatting specifications.

    This function uses the provided formatting specifications to generate
    documentation for a given function. It takes into account the function's
    summary, description, parameters, returns, errors, examples, and notes, as well
    as any forbidden substrings that should not appear in the generated
    documentation.

    Parameters:
    func_data (object): The metadata of the function to be documented, including its
                summary, description, parameters, returns, errors, examples, and
                notes.
    format_spec (object): The formatting specifications for generating the
                documentation. This includes options such as line prefix, start
                marker, end marker, and forbidden substrings.

    Returns:
    string: The generated documentation for the given function.

    Examples:
    Formats the text 'This is a long line that needs to be wrapped.' into multiple
     lines.   'This is a long line that needs to be wrapped.', 20

    Notes:
    """
    line_prefix = format_spec.get('line_prefix', '')
    start_marker = format_spec.get('start', '')
    end_marker = format_spec.get('end', '')

    def format_text(text, width, prefix='', subsequent_indent='  '):
        """
        Formats text into multiple lines with adjustable width, prefix, and indentation.

        This function uses the `textwrap` module to wrap a given text into multiple
        lines. The wrapping occurs at a specified maximum width, with optional prefix
        and subsequent indentation settings. It returns a list of formatted lines.

        Parameters:
        text (string): The original text that needs to be wrapped.
        width (integer): The maximum width at which the text should be wrapped.
        prefix (string): Optional prefix to add to each line. Defaults to an empty
                    string.
        subsequent_indent (string): Optional indentation for subsequent lines. Defaults
                    to a single space character.

        Returns:
        list of strings: A list of formatted text lines.

        Examples:
        Formats the text 'This is a long line that needs to be wrapped.' into multiple
         lines.   format_text('This is a long line that needs to be wrapped.', 20)

        Notes:
        The `textwrap` module must be installed and imported for this function to work
         correctly.
        """
        # Handles text wrapping and adds the line prefix to all lines
        wrapper = textwrap.TextWrapper(width=width,
                                       initial_indent=prefix,
                                       subsequent_indent=subsequent_indent,
                                       replace_whitespace=True)
        wrapped_lines = wrapper.wrap(text)
        return wrapped_lines

    doc_string = []

    if func_data.get('summary'):
        doc_string.extend(format_text(func_data['summary'], max_width, subsequent_indent=''))
        doc_string.append('')

    if func_data.get('description'):
        doc_string.extend(format_text(func_data['description'], max_width, subsequent_indent=''))

    sections = {
        'Parameters': lambda item: f"{item['name']} ({item['type']}): {item['description']}",
        'Returns': lambda item: f"{item['type']}: {item['description']}",
        'Errors': lambda item: f"{item['name']}: {item['description']}",
        'Examples': lambda item: f"{item['description']}\n  {item['code']}",
        'Notes': lambda item: item
    }

    for section_title, formatter in sections.items():
        section_data = func_data.get(section_title.lower())
        if section_data:
            doc_string.append('')
            doc_string.append(section_title + ':')
            if isinstance(section_data, list):
                for item in section_data:
                    item_desc = formatter(item)
                    colon_pos = item_desc.find(':') + 2
                    subsequent_indent = ' ' * (min(max_indent, colon_pos))
                    formatted_text = format_text(item_desc, max_width, subsequent_indent=subsequent_indent)
                    doc_string.extend(formatted_text)
            elif isinstance(section_data, dict):  # For single-item sections like 'returns'
                item_desc = formatter(section_data)
                colon_pos = item_desc.find(':') + 2
                subsequent_indent = ' ' * (min(max_indent, colon_pos))
                formatted_text = format_text(item_desc, max_width, subsequent_indent=subsequent_indent)
                doc_string.extend(formatted_text)
                
    # check for forbidden substrings
    for forbidden in format_spec.get('forbidden', []):
        for line in doc_string:
            if forbidden in line:
                return None
                
    if format_spec.get('start_same_line', False):
        body = '\n'.join([line_prefix + line for line in doc_string[1:]])
        return start_marker + doc_string[0] + '\n' + body + '\n' + end_marker
    else:
        body = '\n'.join([line_prefix + line for line in doc_string])
        return start_marker + '\n' + body + '\n' + end_marker
