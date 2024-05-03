import argparse
import samples
import logging
from docstrings import DocstringService
from ollama import OllamaService


def get_arguments():
    """
    Parse command line arguments.

    This function parses the command line arguments provided to the script.
    It uses the argparse library to define a set of command-line options,
    and then parses those options from the command line.

    Parameters:
      None: This function does not take any parameters. It only returns the parsed
            arguments.

    Returns:
      args (argparse.Namespace): The parsed command line arguments, which can be
            accessed as attributes on the returned object.
    """
    # Initialize the parser
    parser = argparse.ArgumentParser(description="Create, update, or validate docstrings in Python files.")

    parser.add_argument('-a', '--attempts', type=int, default=5, metavar='[1-100]',
                        help='Set the number of attempts for processing. Must be an integer in the range [1-100].')
    parser.add_argument('-c', '--create', action='store_true',
                        help='Create new docstrings for functions that do not currently have one.')
    parser.add_argument('-d', '--depth', type=int, default=1, metavar='[1-100]',
                        help='Set the depth for processing. Must be an integer in the range [1-100].')
    parser.add_argument('-l', '--log-level', type=int, default=1, choices=range(0, 3),
                        help='Set the log level. 0 = no logs, 1 = brief logs, 2 = verbose logs.')
    parser.add_argument('-m', '--modify', action='store_true',
                        help='Modify the original files with new changes. If -p or -r is also specified, the file will prompt the user before modifying.')
    parser.add_argument('-p', '--preview', action='store_true',
                        help='Preview the content of the files without making changes unless -m is also specified, in which case, it will prompt the user before modifying.')
    parser.add_argument('-r', '--report', action='store_true',
                        help='Show a report after each file is processed. If the -m flag is present, this flag will cause the user to be prompted before the modification occurs.')
    parser.add_argument('-s', '--strip', action='store_true',
                        help='Strip existing docstrings. When used in conjunction with -v, it will only strip docstrings that fail validation. Incompatible with -u and -c.')
    parser.add_argument('-u', '--update', action='store_true',
                        help='Update existing docstrings. If -v is specified, it will only update if the current docstring failed validation. Incompatible with -s.')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validate that the docstrings in the file correctly describe the source code. If -u is specified, an update will only occur if validation fails. If -s is specified, the docstring will be deleted if validation fails.')

    # Arguments for listing, installing, and choosing models
    parser.add_argument('--install-model', type=str, metavar='MODEL_NAME',
                        help='Install a model by name onto the Ollama server.')
    parser.add_argument('--list', action='store_true',
                        help='List all installed models available on the Ollama server.')
    parser.add_argument('--model', type=str, default='llama3',
                    help='Specify the model to operate on. Defaults to llama3.')

    
    # Arguments for specifying host and port
    parser.add_argument('--host', type=str, default='localhost',
                        help='Specify the host of the Ollama server. Defaults to localhost.')
    parser.add_argument('--port', type=int, default=11434,
                        help='Specify the port of the Ollama server. Defaults to 11434.')


    # Adding positional argument for filenames
    parser.add_argument('filenames', nargs='*',
                        help='List of filenames to process. If an undecorated filename is provided, all functions in the file will be examined. To limit the scope of operations, filenames can be decorated by adding a colon-separated list of fully-qualified function names of the form foo.bar.zoo, where foo, bar, and zoo can be the names of functions or classes. Nesting of functions and classes is allowed. If a path is longer than the --depth field, a warning is reported, and the function is not processed.')

    # Parse the arguments
    args = parser.parse_args()
    
    args.example_docstring = samples.example_docstring
    args.example_function = samples.example_function

    return args


def get_logger(args):
    """
    Creates a new logger with the specified log level. The log level is determined
    by the `log_level` argument.

    This function creates a new logger and sets its log level based on the provided
    `log_level`. It then adds a console handler to the logger, which allows logs to
    be printed to the console.

    The log level can be one of three levels: 0 (CRITICAL), 1 (INFO), or 2 (DEBUG).
    If `log_level` is not specified or is invalid, the default log level will be
    used.

    Parameters:
        args (obj): The arguments object containing the log level to use for the
    logger.

    Returns:
        logger (logging.Logger): The new logger with the specified log level.

    Example:
    > get_logger({'log_level': 1}) # This will create a logger with an INFO log
    level
    """
    logger = logging.getLogger(__name__)
    if args.log_level == 0:
        logger.setLevel(logging.CRITICAL)  # No logs shown
    elif args.log_level == 1:
        logger.setLevel(logging.INFO)  # Brief logs
    elif args.log_level == 2:
        logger.setLevel(logging.DEBUG)  # Verbose logs

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def main():
    """
    This is the main entry point of the application. It handles command-line
    arguments and orchestrates the execution of various functions to update
    docstrings in Python files.

    The function accepts a set of options, including file names, logging levels, and
    actions to perform on the files. The main logic involves:

    - Processing each file with the document_file function
    - Printing reports if requested
    - Asking for user confirmation before saving changes (if preview or report
    option is enabled)
    - Saving the modified file (if confirmed) or reporting that no changes were made

    This function does not handle errors and exceptions, relying on other functions
    to do so. It should be called with valid command-line arguments.

    Parameters:
      None: This function does not take any explicit parameters.
      Returns:
      None: The function does not return any value.
    """
    args = get_arguments()
    logger = get_logger(args)
    
    if args.strip and (args.create or args.update):
        logger.critical(f'Critical error: cannot use -s with -c or -u')    
        exit(1)
        
    if args.list:
        models = OllamaService.get_models(args, logger)
        print('-' * 79)
        for model in models:
            print(f"{model['name']}")
        
    if args.install_model:
        OllamaService.install_model(args, logger)
        
    # Create the docstring service
    docstring_service = DocstringService(args, logger)

    # Process each file with the document_file function
    for decorated_filename in args.filenames:
        parts = decorated_filename.split(':')
        filename = parts[0]
        function_paths = None if len(parts) <= 1 else parts[1:]
        # Call the document_file function with the filename and list of options
        modified_file, reports, modified = docstring_service.document_file(filename, function_paths)

        if args.report and reports is not None and len(reports) > 0:
            print('-' * 79)
            for report in reports:
                print(report)

        if not modified:
            logger.info(f'The file {filename} was not modified')
        else:
            if args.preview:
                print(modified_file)

            if args.modify:
                save_file = not args.preview
    
                # Only ask for user confirmation if 'preview' or 'report' option is enabled
                if args.preview or args.report:
                    user_response = input(f'\nDo you want to save these modifications to {filename}? (y/N) ').strip().lower()
                    # Set the save_file flag based on user input
                    save_file = (user_response == 'y')

                # Check the save_file flag to decide whether to save the file
                if save_file:
                    with open(filename, 'w') as outfile:
                        outfile.write(modified_file)
                    print(f'Updated {filename}')
                else:
                    print(f'{filename} was NOT updated.')
        

if __name__ == '__main__':
    main()
