from ollama import OllamaService
import libcst as cst
import queries
import re
import textwrap


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, qualified_function_names):
            self.class_level = 0
            self.function_level = 0
            # Store the current FQFN as a stack of class and function names
            self.fully_qualified_function_name = []
            self.docstring_service = docstring_service
            # options contains the parsed command-line arguments
            self.options = docstring_service.options
            self.reports = []
            # qualified_function_names is a list of mostly-qualified function names. These are dot-separated
            # identifiers that indicate the complete nesting of the function excluding the module name,
            # eg class_name.method_name.nested_function_name.
            self.qualified_function_names = qualified_function_names
            self.logger = docstring_service.logger
            self.leading_whitespace = []
            self.modified = False

        def convert_functiondef_to_string(self, function_def, remove_docstring=False):
            if remove_docstring:
                # Traverse the FunctionDef body to find and remove the docstring
                body = function_def.body
                if body and isinstance(body[0], cst.SimpleStatementLine):
                    # Check if the first statement is an Expr with a string (docstring)
                    first_statement = body[0]
                    if isinstance(first_statement.body[0], cst.Expr) and isinstance(first_statement.body[0].value, cst.SimpleString):
                        # Remove the docstring statement
                        new_body = body.with_changes(body=body[1:])
                        function_def = function_def.with_changes(body=new_body)

            # Convert the possibly modified FunctionDef to code
            code = cst.Module(body=[function_def])
            return code.code

        def add_leading_whitespace(self, node):
            # This is outrageously ineffient, but I haven't found a better way (yet)
            code = cst.Module([])
            code.body.append(node.body)
            match = re.match(r'\s*', code.code)
            lws = match.group(0) if match else ''
            lws = lws.split('\n')[-1]
            self.leading_whitespace.append(lws)

        def get_leading_whitespace(self):
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            # Pop the last-added whitespace fragment from the stack.
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            # NOTE: This does not include the module name in the result.
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            leading_whitespace = self.get_leading_whitespace()
            # Calculate the total width for wrapping
            total_width = len(leading_whitespace) + 80
            lines = docstring.strip().split('\n')
            formatted_lines = []
            for line in lines:
                wrapper = textwrap.TextWrapper(width=total_width, initial_indent=leading_whitespace, subsequent_indent=leading_whitespace)
                wrapped_lines = wrapper.wrap(line) 
                formatted_lines.append('\n'.join(wrapped_lines))
            return '"""\n' + '\n'.join(formatted_lines) + '\n' + leading_whitespace + '"""'
    
        def update_docstring(self, fully_qualified_function_name, function_name, current_docstring, updated_node, action_taken):
            function_code = self.convert_functiondef_to_string(updated_node)
            do_update = self.options.update
            strip_docstring = self.options.strip
            if self.options.validate:
                self.logger.debug('Validating existing docstring')
                validated, assessment = queries.validate_docstring(self.docstring_service.ollama, function_name, function_code, f'"""{current_docstring}"""', self.options, self.logger)
                if validated:
                    do_update = False
                    strip_docstring = False
                report = '-' * 70 + f'\nValidation report for {fully_qualified_function_name}: {"PASS" if validated else "FAILED"}\n{assessment}'
                self.reports.append(report)

            body_statements = list(updated_node.body.body)
            if body_statements and isinstance(body_statements[0], cst.SimpleStatementLine) and isinstance(body_statements[0].body[0], cst.Expr):
                if isinstance(body_statements[0].body[0].value, cst.SimpleString):
                    if strip_docstring:
                        self.logger.debug('Stripping existing docstring')
                        body_statements.pop(0)  # Remove the first statement assuming it's the docstring
                        action_taken = "stripped existing docstring"
                        self.modified = True
                    elif do_update:
                        self.logger.debug('Replacing existing docstring')
                        new_docstring = queries.generate_docstring(self.docstring_service.ollama, fully_qualified_function_name, function_name, function_code, current_docstring, self.options, self.logger)
                        new_docstring = self.format_docstring(new_docstring)
                        body_statements[0] = cst.SimpleStatementLine([cst.Expr(cst.SimpleString(new_docstring))])
                        action_taken = "updated existing docstring"
                        self.modified = True

            updated_body = cst.IndentedBlock(body=body_statements)
            updated_node = updated_node.with_changes(body=updated_body)
            return updated_node, action_taken
        
        def create_docstring(self, fully_qualified_function_name, function_name, current_docstring, updated_node, action_taken):
            if self.options.create:
                # Append new docstring
                self.logger.debug('Creating a new docstring')
                function_code = self.convert_functiondef_to_string(updated_node)
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, fully_qualified_function_name, function_name, function_code, current_docstring, self.options, self.logger)
                if new_docstring is not None:
                    new_docstring = self.format_docstring(new_docstring)
                    body_statements = [cst.SimpleStatementLine([cst.Expr(cst.SimpleString(new_docstring))])] + list(updated_node.body.body)
                    updated_body = cst.IndentedBlock(body=body_statements)
                    updated_node = updated_node.with_changes(body=updated_body)
                    action_taken = "created a new docstring"
                    self.modified = True
                else:
                    action_taken = "failed to create new docstring, leaving as-is" 
            return updated_node, action_taken
        
        def leave_FunctionDef(self, original_node, updated_node):
            # Note that the qualified function names include class and function nesting but do not include the module name
            action_taken = "did nothing"
            function_name = updated_node.name.value
            fully_qualified_function_name = self.get_fully_qualified_function_name()

            if self.function_level > self.options.depth or self.class_level > self.options.depth:
                action_taken = f'skipped due to high nesting level -- function_level: {self.function_level}, class_level: {self.class_level}'
                if self.qualified_function_names is not None and fully_qualified_function_name in self.qualified_function_names:
                    action_taken = f'ignored: you specified {fully_qualified_function_name} to be processed, but the depth setting is too low ({self.options.depth}). Increase the depth with the "--depth {max(self.function_level, self.class_level)}" option.'
                    self.logging.warning(action_taken)
            else:
                do_process = True
                if self.qualified_function_names is not None:
                    do_process = fully_qualified_function_name in self.qualified_function_names 
                    if not do_process:
                        action_taken = f'Skipped because it is not in the decorated filename list of functions to document.'
                if do_process:
                    current_docstring = updated_node.get_docstring()
                    if current_docstring is None:
                        updated_node, action_taken = self.create_docstring(fully_qualified_function_name, function_name, current_docstring, updated_node, action_taken)
                    else:
                        updated_node, action_taken = self.update_docstring(fully_qualified_function_name, function_name, current_docstring, updated_node, action_taken)
            self.remove_leading_whitespace()


            self.function_level -= 1
            report = f"{fully_qualified_function_name}: {action_taken}"
            self.logger.info(report)
            self.reports.append(report)
            self.fully_qualified_function_name.pop()
            return updated_node

    def __init__(self, options, logger):
        """
        Initializes an instance of the class with given options and logger.

        This special method is called when a new instance of the class is created. It
        sets up the logger and Ollama service for use within the class.

        Parameters:
        self (object): The current instance of the class.
        options (object): A dictionary of options to configure the class.
        logger (object): An instance of a logger that will be used for logging purposes
                    within the class.

        Returns:
        void: Does not return any value. The primary effect is to initialize the class
              instance.

        Examples:
        Initializes an instance of the class with given options and logger.
                    __init__(self, {'key': 'value'}, logger)
        """
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, qualified_function_names):
        """
        Updates the docstrings of specified functions within a Python file.

        This function reads a Python file, parses its abstract syntax tree (AST), and
        updates the docstrings of the specified functions using a custom transformer.
        The transformed AST is then returned along with any reports or modified code.

        Parameters:
        file_path (string): The path to the Python file containing the functions whose
                    docstrings need updating.
        qualified_function_names (list of strings): A list of function names including
                    class and function nesting, but not including the module name. These
                    are the functions whose docstrings will be updated.

        Returns:
        tuple: A tuple containing the modified source code, a list of reports, and a
               boolean indicating whether any modifications were made.

        Errors:
        FileNotFoundError: Thrown if the specified file cannot be found at the given
                    path.
        SyntaxError: Thrown if the source code file contains syntax errors that prevent
                    parsing.

        Examples:
        Updates the docstrings of functions 'MyClass.my_function' and
         'AnotherClass.another_function' in 'example.py'.   document_file('example.py',
         ['MyClass.my_function', 'AnotherClass.another_function'])

        Notes:
        This function relies on the 'cst' library to parse Python source code and
         'DocstringService' for updating docstrings. Ensure these libraries are
         installed and the source file is syntactically correct for proper operation.
        """
        # Note that the qualified function names include class and function nesting but do not include the module name
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, qualified_function_names)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
