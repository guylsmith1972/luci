import argparse
import logging
from docstrings import DocstringService


def get_arguments():
    """
    Create, update, or validate docstrings in Python files.

    This function parses the command line arguments for various options related to
    processing and validating docstrings. The user can specify the number of
    attempts for processing, whether to create new docstrings, modify original
    files, preview changes, show reports, strip existing docstrings, update existing
    docstrings, or validate that docstrings correctly describe source code.

    Parameters:
    filenames (list[str]): A list of filenames to process.
    attempts (int): The number of attempts for processing. Default is 5.
    create (bool): Whether to create new docstrings for functions without one.
    Default is False.
    depth (int): The depth for processing. Default is 1.
    log_level (int): The log level. Options are 0 (no logs), 1 (brief logs), or 2
    (verbose logs). Default is 0.
    modify (bool): Whether to modify original files with new changes. If True, will
    prompt user before modifying the file. Default is False.
    preview (bool): Whether to preview the content of the files without making
    changes. If True and -m is also specified, will prompt user before modifying the
    file. Default is False.
    report (bool): Whether to show report after each file is processed. If True and
    -m is also specified, will cause the user to be prompted before the modification
    occurs. Default is False.
    strip (bool): Whether to strip existing docstrings. When used in conjunction
    with -v, will only strip docstrings that fail validation. Incompatible with -u
    and -c. Default is False.
    update (bool): Whether to update existing docstrings. If True and -v is
    specified, will only update if current docstring failed validation. Incompatible
    with -s. Default is False.
    validate (bool): Whether to validate that the docstrings in the file correctly
    describe the source code. If True and -u is specified, will update only if
    validation fails. If -s is specified, docstring will be deleted if validation
    fails. Default is False.

    Example:
        >>> get_arguments()
            # This will return the parsed command line arguments.
    """
    # Initialize the parser
    parser = argparse.ArgumentParser(description="Create, update, or validate docstrings in Python files.")

    parser.add_argument('-a', '--attempts', type=int, default=5, metavar='[1-100]',
                        help='Set the number of attempts for processing. Must be an integer in the range [1..100].')
    parser.add_argument('-c', '--create', action='store_true',
                        help='Create new docstrings for functions that do not currently have one.')
    parser.add_argument('-d', '--depth', type=int, default=1, metavar='[1-100]',
                        help='Set the depth for processing. Must be an integer in the range [1..100].')
    parser.add_argument('-l', '--log-level', type=int, default=0, choices=range(0, 3),
                        help='Set the log level. 0 = no logs, 1 = brief logs, 2 = verbose logs')
    parser.add_argument('-m', '--modify', action='store_true',
                        help='Modify the original files with new changes. If -p or -r is also specified, will prompt user before modifying the file.')
    parser.add_argument('-p', '--preview', action='store_true',
                        help='Preview the content of the files without making changes unless -m is also specified, in which case it will prompt user before modifying the file.')
    parser.add_argument('-r', '--report', action='store_true',
                        help='Show report after each file is processed. If the -m flag is present, this flag will cause the user to be prompted before the modification occurs.')
    parser.add_argument('-s', '--strip', action='store_true',
                        help='Strip existing docstrings. When used in conjunction with -v, will only strip docstrings that fail validation. Incompatible with -u and -c.')
    parser.add_argument('-u', '--update', action='store_true',
                        help='Update existing docstrings. If -v is specified, will only update if current docstring failed validation. Incompatible with -s.')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validate that the docstrings in the file correctly describe the source code. If -u is specified, update will only occur if validation fails. If -s is specified, docstring will be deleted if validation fails.')
    
    # Adding positional argument for filenames
    parser.add_argument('filenames', nargs='*',
                        help='List of filenames to process. If an undecorated filename is provided, all functions in the file will be examined. The limit the scope of operations, filenames can be decorated by add a colon-separated list of fully-qualified function names of the form foo.bar.zoo, where foo, bar, and zoo can be the names of functions or classes. Nesting of functions and classes is allowed. If a path is longer than the --depth field,a warning is reported and the function is not processed.')

    # Parse the arguments
    args = parser.parse_args()
    
    with open('samples/example_docstring.txt', 'r') as infile:
        args.example_docstring = infile.read()
    with open('samples/example_function.txt', 'r') as infile:
        args.example_function = infile.read()

    return args


def get_logger(args):
    """
    Returns a configured logger instance based on the provided command-line
    arguments.
    The logger's log level is set according to the specified `log_level` argument:
      * 0: No logs are shown (CRITICAL level).
      * 1: Brief logs are displayed (INFO level).
      * 2: Verbose logs are shown (DEBUG level).

    Parameters:
    args (dict): Dictionary containing command-line arguments.
    log_level (int): Level of logging, where 0 is the most restrictive and 2 is the
    least.

    Returns:
    logger (logging.Logger): Configured logger instance with the specified log
    level.
    Raises:
    None: No exceptions are raised. The function simply returns a configured logger
    instance.
    Example:
    >>> get_logger({'log_level': 1})
    # This will return a logger instance set to INFO logging level.
    Note:
    This function is designed to be used in command-line applications or scripts
    where logging configuration needs to be dynamic and controlled by user-provided
    arguments.
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
    The main entry point for processing Python files and updating their docstrings.
    This function orchestrates the steps to parse command-line arguments, create a
    logger,
    handle file operations, and report on any modifications made.

    Parameters: None. This function does not accept any parameters from outside.

    Raises:
        CriticalError: If the -s option is used with either -c or -u options.

    Returns: None. The function prints messages to the console as it runs.
    """
    args = get_arguments()
    logger = get_logger(args)
    
    if args.strip and (args.create or args.update):
        logger.critical(f'Critical error: cannot use -s with -c or -u')    
        exit(1)
        
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
