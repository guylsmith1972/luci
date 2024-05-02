import argparse
import logging
from docstrings import DocstringService
from ollama import OllamaService


def get_arguments():
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
                        help='List of filenames to process. If an undecorated filename is provided, all functions in the file will be examined. The limit the scope of operations, filenames can be decorated by add a colon-separated list of fully-qualified function names of the form foo.bar.zoo, where foo, bar, and zoo can be the names of functions or classes. Nesting of functions and classes is allowed. If a path is longer than the --depth field,a warning is reported and the function is not processed.')

    # Parse the arguments
    args = parser.parse_args()
    
    with open('samples/example_docstring.txt', 'r') as infile:
        args.example_docstring = infile.read()
    with open('samples/example_function.txt', 'r') as infile:
        args.example_function = infile.read()

    return args


def get_logger(args):
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


def list_models(args, logger):
    models = OllamaService.get_models(args)
    for model in models:
        print(f"{model['name']}")
    

def install_model(args, logger):
    print(f'Install model is {args.install_model}')
    OllamaService.install_model(args, logger)


def main():
    args = get_arguments()
    logger = get_logger(args)
    
    if args.strip and (args.create or args.update):
        logger.critical(f'Critical error: cannot use -s with -c or -u')    
        exit(1)
        
    if args.list:
        list_models(args, logger)
        
    if args.install_model:
        install_model(args, logger)
        
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
