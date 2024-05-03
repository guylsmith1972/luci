from ollama import OllamaService
import libcst as cst
import queries
import re
import textwrap


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, functions_of_interest):
            """
            Initializes the object with various settings and services.

            This constructor sets up the object's attributes, including docstring service,
            default indent, functions of interest, reports, logger, leading whitespace, and
            a modified flag. It also initializes the class level, function level, and fully
            qualified function name arrays.

            Parameters:
            self (object): The object being initialized.
            docstring_service (object): A docstring service object that provides various
                        functionality for processing and generating documentation.
            functions_of_interest (list of strings): A list of fully-qualified function
                        names that indicate the functions to be processed and documented.

            Returns:
            void: Does not return any value. The constructor sets up the object's
                  attributes.

            Examples:
            Initializes an object with a docstring service, default indent, and functions of
             interest.   __init__(docstring_service, 4, ['class.method.nested_function'])

            Notes:
            This constructor relies on the `docstring_service` to provide various
             functionality for processing and generating documentation.
            """
            self.class_level = 0
            self.function_level = 0
            # Store the FQFN as a list of class and function names
            self.fully_qualified_function_name = []
            self.docstring_service = docstring_service
            # options contains the parsed command-line arguments
            self.options = docstring_service.options
            self.reports = []
            # functions_of_interest is a list of fully-qualified function names. These are dot-separated
            # identifiers that indicate the complete nesting of the function excluding the module name,
            # eg class_name.method_name.nested_function_name.
            self.functions_of_interest = functions_of_interest
            self.logger = docstring_service.logger
            self.leading_whitespace = []
            self.modified = False

        def convert_functiondef_to_string(self, function_def, remove_docstring=False):
            """
            Converts a function definition (FunctionDef) to a string representation,
            optionally removing the docstring.

            This function takes a FunctionDef object and converts it into a code string. If
            the `remove_docstring` parameter is set to True, the function will remove any
            existing docstring from the function definition before converting it.

            Parameters:
            self (object): The object instance that this method belongs to (not used in this
                        implementation).
            function_def (cst.FunctionDef): The function definition to be converted to a
                        string.
            remove_docstring (boolean): Whether to remove the docstring from the function
                        definition before conversion. Default is False.

            Returns:
            string: The string representation of the function definition.

            Errors:
            SyntaxError: Thrown if the FunctionDef contains invalid syntax that prevents
                        conversion to code.

            Examples:
            Converts a function definition without removing the docstring.
             convert_functiondef_to_string(function_def, False)
            Converts a function definition and removes its docstring.
             convert_functiondef_to_string(function_def, True)

            Notes:
            This function relies on the 'cst' library to parse and manipulate Python source
             code. Ensure this library is installed for proper operation.
            """
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
            """
            Adds the leading whitespace from a given node to a list for further processing.

            This function takes a CST (Concrete Syntax Tree) node as input and extracts the
            leading whitespace from it. It then appends this whitespace to a list for future
            use. This function is not efficient, but it serves its purpose.

            Parameters:
            self (object): The object instance that this method belongs to.
            node (cst.Module): The CST node from which the leading whitespace is extracted.

            Returns:
            void: This function does not return any value.

            Errors:
            None: No specific errors are mentioned for this function.

            Examples:
            Example usage of the method.   self.add_leading_whitespace(node)

            Notes:
            This function may not be efficient but serves its purpose. There might be a
             better way to achieve this functionality.
            """
            # This is outrageously ineffient, but I haven't found a better way (yet)
            code = cst.Module([])
            code.body.append(node.body)
            match = re.match(r'\s*', code.code)
            lws = match.group(0) if match else ''
            lws = lws.split('\n')[-1]
            self.leading_whitespace.append(lws)

        def get_leading_whitespace(self):
            """
            Returns the leading whitespace characters as a string.

            This method returns the leading whitespace characters stored in the instance's
            `leading_whitespace` attribute.

            Parameters:
            self (object): The instance of the class containing this method.

            Returns:
            string: The leading whitespace characters as a string.

            Examples:
            Gets the leading whitespace from an instance `obj`.   result =
             obj.get_leading_whitespace()
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """
            Removes the last added whitespace fragment from a stack.

            This function removes the top element (the most recently added) from a stack,
            effectively removing the leading whitespace. It is intended for use in an
            object-oriented context where the leading whitespace is being tracked and
            managed.

            Parameters:
            self (object): The instance of the class that this function belongs to.

            Returns:
            void: Does not return any value.

            Examples:
            Removes the last added whitespace fragment from a stack.
             self.leading_whitespace.pop()
            """
            # Pop the last-added whitespace fragment from the stack.
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            """
            Returns the fully qualified name of a function, excluding the module name.

            This method joins the components of a function's name to form its fully
            qualified name. Note that it does not include the module name in the result.

            Parameters:
            self (object): The instance of the class containing this method.

            Returns:
            string: The fully qualified name of the function, excluding the module name.

            Examples:
            Returns the fully qualified name of a function without including the module
             name.   get_fully_qualified_function_name(self)
            """
            # NOTE: This does not include the module name in the result.
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            """
            Visits a ClassDef node in the abstract syntax tree (AST) and updates relevant
            variables.

            This method increments a class level counter, appends the class name to a list
            of fully qualified function names, adds leading whitespace as necessary, and
            logs information about the examined class.

            Parameters:
            self (object): The current object instance.
            node (object): The ClassDef node being visited in the AST.

            Returns:
            void: Does not return any value. The function's primary effect is updating
                  object state.

            Examples:
            Examines a ClassDef node and updates the class level, fully qualified function
             name, and leading whitespace.   visit_ClassDef(self, node)

            Notes:
            This method is likely part of a larger AST traversal or code analysis process.
            """
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Handles the leaving of a ClassDef node in an Abstract Syntax Tree (AST)
            representation of Python source code.

            This method reduces the class level by 1, removes the fully qualified function
            name from a stack, and removes any leading whitespace. It returns the updated
            node.

            Parameters:
            self (object): The object instance that contains relevant information about the
                        current parsing context.
            original_node (node): The original node being left, which is typically a
                        ClassDef node in an AST representation of Python source code.
            updated_node (node): The updated node that results from leaving the original
                        node.

            Returns:
            node: The updated node that results from leaving the original node.

            Examples:
            Leaves a ClassDef node and updates the relevant information.
             leave_ClassDef(self, original_node, updated_node)
            """
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """
            Visits a FunctionDef node in an Abstract Syntax Tree (AST) and increments the
            function level, appends the fully qualified function name, adds leading
            whitespace, and logs information about the examined function.

            This function is part of a visitor pattern that traverses the AST. It handles
            FunctionDef nodes by incrementing the function level, appending the fully
            qualified function name to a list, adding leading whitespace for indented
            output, and logging information about the examined function.

            Parameters:
            self (object): The object instance that this method is called on. It contains
                        references to other methods and attributes necessary for the
                        visitor's operation.
            node (object): The FunctionDef node in the AST being visited. This method
                        examines this node and performs the described actions.

            Returns:
            void: Does not return any value.

            Examples:
            Visits a FunctionDef node and performs the described actions.
             visit_FunctionDef(self, node)

            Notes:
            This method is part of a larger visitor pattern that traverses an AST. Ensure
             the `self` object and the `node` parameter are correctly instantiated and
             passed to this function for proper operation.
            """
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            """
            Formats a docstring by wrapping its lines to fit within a specified width.

            This function takes a docstring as input, calculates the total width for
            wrapping based on the leading whitespace and a default value of 80 characters,
            and then uses the `textwrap` library to wrap each line of the docstring. The
            formatted lines are then joined together with newline characters to form the
            final output.

            Parameters:
            self (object): The object instance that this function is part of, likely a
                        class.
            docstring (string): The docstring to be formatted.

            Returns:
            string: The formatted docstring as a string, with lines wrapped within the
                    specified width.

            Examples:
            Formats the docstring of the function `example_function` to fit within a width
             of 80 characters.   format_docstring(self, 'This is an example docstring.').
            """
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
            """
            Updates the docstring of a specified function within an object's context.

            This function updates the docstring of a function with given parameters and
            returns the updated node along with an action taken. It first validates the
            existing docstring if validation is enabled, then strips or replaces the
            docstring based on configuration options.

            Parameters:
            self (object): The object instance that contains the function to be updated.
            fully_qualified_function_name (string): The fully qualified name of the function
                        whose docstring is to be updated.
            function_name (string): The name of the function whose docstring is to be
                        updated.
            current_docstring (string): The current docstring of the function that needs
                        updating.
            updated_node (object): The updated node representing the function with its new
                        docstring.
            action_taken (string): A string indicating the action taken by the function
                        (e.g., 'stripped existing docstring' or 'updated existing
                        docstring').

            Returns:
            object: The updated node representing the function with its new docstring, along
                    with an action taken.

            Errors:
            ValidationFailedError: Thrown if validation of the existing docstring fails.

            Examples:
            Updates the docstring of a function within an object's context.
             update_docstring(self, 'my_function', 'my_function_name', 'current_docstring',
             updated_node, action_taken)

            Notes:
            This function relies on various configuration options and validation mechanisms
             to ensure correct updating of the docstring.
            """
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
            """
            Creates or updates a docstring for a given function within a Python file.

            This function creates or updates the docstring of a specified function based on
            the provided current docstring, updated node, and action taken. It formats the
            new docstring according to certain rules and modifies the original code
            accordingly.

            Parameters:
            self (object): The object instance of the class that contains this function.
            fully_qualified_function_name (string): The fully qualified name of the function
                        whose docstring is to be updated.
            function_name (string): The name of the function whose docstring is to be
                        updated.
            current_docstring (string): The current docstring of the function being
                        modified.
            updated_node (object): The updated node representing the modified code.
            action_taken (string): The action taken by the function, such as 'created a new
                        docstring' or 'failed to create new docstring'.

            Returns:
            tuple: Returns a tuple containing the updated node and the action taken.

            Errors:
            None: Thrown if the function fails to create or update the docstring due to an
                  error.

            Examples:
            Creates a new docstring for the 'my_function' in 'example.py'.
             create_docstring(self, 'example.my_function', 'my_function', 'This is the
             current docstring.', updated_node, 'created a new docstring')

            Notes:
            This function relies on the object instance and its attributes to operate
             correctly. Ensure that the necessary objects are properly initialized before
             calling this function.
            """
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
            """
            Handles a FunctionDef node in the abstract syntax tree (AST) and determines
            whether to process it or skip it based on the current nesting level and the list
            of functions to document.

            This function is part of a larger processing pipeline for Python code. It takes
            two AST nodes as input: the original node and the updated node. Based on the
            current nesting level and the list of functions to document, it decides whether
            to process the function or skip it. If processed, it updates the docstring if
            necessary and removes leading whitespace.

            Parameters:
            self (object): The object instance that contains various attributes and methods
                        used by this function.
            original_node (ast node): The original FunctionDef node in the AST.
            updated_node (ast node): The updated FunctionDef node in the AST.

            Returns:
            ast node: The processed and possibly updated FunctionDef node.

            Errors:
            ValueError: Thrown if an unexpected error occurs during processing, such as an
                        invalid function name or incorrect nesting level.

            Examples:
            Skips a function with a high nesting level due to the specified depth limit.
             leave_FunctionDef(self, original_node, updated_node)

            Notes:
            This function relies on various attributes and methods of the `self` object,
             which should be properly initialized before calling this function. The
             `get_fully_qualified_function_name()` method is also used to generate a fully
             qualified function name.
            """
            action_taken = "did nothing"
            function_name = updated_node.name.value
            fully_qualified_function_name = self.get_fully_qualified_function_name()

            if self.function_level > self.options.depth or self.class_level > self.options.depth:
                action_taken = f'skipped due to high nesting level -- function_level: {self.function_level}, class_level: {self.class_level}'
                if self.functions_of_interest is not None and fully_qualified_function_name in self.functions_of_interest:
                    action_taken = f'ignored: you specified {fully_qualified_function_name} to be processed, but the depth setting is too low ({self.options.depth}). Increase the depth with the "--depth {max(self.function_level, self.class_level)}" option.'
                    self.logging.warning(action_taken)
            else:
                do_process = True
                if self.functions_of_interest is not None:
                    do_process = fully_qualified_function_name in self.functions_of_interest 
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
        Initializes an object with specified options and a logging mechanism.

        This special method is called when an object of this class is created. It sets
        up essential attributes, such as the logger and Ollama service, using the
        provided options and logger.

        Parameters:
        self (object): The object being initialized.
        options (object): Options to be used for the initialization process.
        logger (logging mechanism): The logging mechanism to use for this object.

        Returns:
        void: Does not return any value.

        Examples:
        Initializes an object with default options and a custom logger.   __init__(self,
         options, logger)
        """
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, functions_of_interest):
        """
        Updates the docstrings of specific functions within a Python file based on the
        provided list of functions of interest.

        This function reads a Python file, parses its source code using CST, and updates
        the docstrings of the specified functions using a DocstringService. The modified
        source code is then returned along with any reports and modifications made to
        the original code.

        Parameters:
        file_path (string): The path to the Python file whose docstrings need updating.
        functions_of_interest (list<string>): A list of function names for which their
                    docstrings should be updated.

        Returns:
        tuple: Returns a tuple containing the modified source code, any reports
               generated during processing, and any functions that were modified.

        Errors:
        FileNotFoundError: Thrown if the specified file cannot be found at the given
                    path.
        SyntaxError: Thrown if the source code file contains syntax errors that prevent
                    CST parsing.

        Examples:
        Updates the docstrings of 'function1' and 'function2' in 'example.py'.
         document_file('example.py', ['function1', 'function2'])

        Notes:
        This function relies on the 'cst' library to parse Python source code. Ensure
         this library is installed for proper operation.
        """
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, functions_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
