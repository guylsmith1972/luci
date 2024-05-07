from ollama import OllamaService
import libcst as cst
import queries
import re
import textwrap


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, qualified_function_names):
            """
            Initializes the object's state and prepares it for use.

            This special method is called when an instance of the class is created. It sets
            up various attributes, such as the current fully qualified function name (FQFN),
            the docstring service, command-line options, and logging facilities.

            Parameters:
            self (object): The object being initialized.
            docstring_service (object): The service responsible for managing docstrings and
                        related operations.
            qualified_function_names (list): A list of mostly-qualified function names,
                        which represent the complete nesting of functions excluding the
                        module name.

            Returns:
            void: Does not return any value. This method's primary effect is initializing
                  the object's state.

            Examples:
            Initializes an instance of the class with a given docstring service and
             qualified function names.   __init__(self, docstring_service,
             qualified_function_names)

            Notes:
            This special method is called automatically when creating an instance of the
             class. The purpose of this initialization process is to set up essential
             attributes for subsequent operations.
            """
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
            """
            Converts a function definition to a string, optionally removing the docstring.

            This function takes a function definition and an optional parameter
            'remove_docstring'. If set to True, it removes the docstring from the function.
            It then converts the possibly modified function definition into a code string.

            Parameters:
            self (object): The object instance that this function belongs to.
            function_def (cst.FunctionDef): The function definition to be converted to a
                        string.
            remove_docstring (boolean): A flag indicating whether the docstring should be
                        removed from the function.

            Returns:
            string: The code string representation of the function definition.

            Errors:
            ValueError: Thrown if the input 'function_def' is not a valid function
                        definition.

            Examples:
            Converts a function definition to a string without removing the docstring.
             convert_functiondef_to_string(my_function, False)
            Converts a function definition to a string and removes its docstring.
             convert_functiondef_to_string(my_function, True)

            Notes:
            This function assumes that the input 'function_def' is a valid function
             definition.
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
            Adds the leading whitespace from a given AST node to a list for later use.

            This function takes an abstract syntax tree (AST) node as input, extracts the
            leading whitespace from its code string, and appends it to a list. This can be
            used in further processing or analysis of the source code.

            Parameters:
            self (object): The object instance that this method belongs to.
            node (object): The abstract syntax tree node from which the leading whitespace
                        is extracted.

            Returns:
            void: Does not return any value. This function modifies the 'leading_whitespace'
                  list.

            Examples:
            Adds the leading whitespace from a given AST node to the
             'self.leading_whitespace' list.   add_leading_whitespace(self, node)

            Notes:
            This function appears to be inefficient in its current implementation.
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
            Returns the leading whitespace characters of an object.

            This function returns a string containing the leading whitespace characters of
            the object it belongs to. It does not modify the original whitespace characters,
            but rather provides a copy as a string.

            Parameters:
            self (object): The object whose leading whitespace characters are to be
                        retrieved.

            Returns:
            string: A string containing the leading whitespace characters of the object.

            Examples:
            Gets the leading whitespace characters of an object.   leading_whitespace =
             get_leading_whitespace()
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """
            Removes the leading whitespace fragment from a stack.

            This method pops the last-added whitespace fragment from the stack, effectively
            removing any leading whitespace.

            Parameters:
            self (object): The object instance that contains the leading whitespace stack.

            Returns:
            void: Does not return any value.

            Examples:
            Removes the leading whitespace from the stack.   self.leading_whitespace.pop()
            """
            # Pop the last-added whitespace fragment from the stack.
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            """
            Returns the fully qualified name of a function, excluding the module name.

            This method returns the fully qualified name of a function, excluding the module
            name. It takes no parameters and does not modify any external state.

            Parameters:
            self (object): The instance of the class containing this method.

            Returns:
            string: The fully qualified name of the function, excluding the module name.

            Examples:
            Get the fully qualified name of a function.   fully_qualified_function_name =
             get_fully_qualified_function_name()
            """
            # NOTE: This does not include the module name in the result.
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            """
            Visits a ClassDef node in an Abstract Syntax Tree (AST) and updates the current
            class level, fully qualified function name, and adds leading whitespace as
            needed.

            This function is part of a visitor pattern used to traverse and process Python
            source code. It handles ClassDef nodes by incrementing the class level, updating
            the fully qualified function name, adding leading whitespace if necessary, and
            logging information about the visited class.

            Parameters:
            self (object): The instance of a visitor class containing references to various
                        variables used during the traversal process.
            node (ClassDef): The ClassDef node being visited in the AST.

            Returns:
            void: Does not return any value.

            Errors:
            SyntaxError: Thrown if the source code contains syntax errors that prevent AST
                        parsing.

            Examples:
            Visits a ClassDef node with name 'MyClass' in an AST.   visit_ClassDef(self,
             ast.ClassDef(name='MyClass', ...))

            Notes:
            This function is part of a larger visitor pattern used to traverse and process
             Python source code. Ensure the instance of the visitor class is properly
             initialized before calling this method.
            """
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Updates the state and returns a modified node after leaving a ClassDef node.

            This function decrements the class level, pops the fully qualified function
            name, removes leading whitespace, and then returns an updated node. It is likely
            part of a larger processing pipeline for Python source code.

            Parameters:
            self (object): The object instance being processed.
            original_node (object): The original node being processed, likely a ClassDef
                        node.
            updated_node (object): The updated node resulting from processing the original
                        node.

            Returns:
            object: Returns the updated node after processing the ClassDef node.

            Examples:
            Leaves a ClassDef node and updates the state.   leave_ClassDef(self,
             original_node, updated_node)
            """
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """
            Visits a FunctionDef node in an Abstract Syntax Tree (AST), incrementing a
            counter, adding to a list of fully qualified function names, and logging
            information about the examined function.

            This function is part of an abstract syntax tree visitor that processes Python
            source code. It increments a counter, adds the current function name to a list
            of fully qualified function names, and logs information about the examined
            function using the logger.

            Parameters:
            self (object): The object instance of the visitor class that is being used to
                        visit the AST nodes.
            node (ast.FunctionDef): The current FunctionDef node being visited in the AST.

            Returns:
            void: Does not return any value. The function's primary effect is logging
                  information about the examined function.

            Errors:
            None: No specific error is thrown by this function, as it only logs information
                  and does not have any exceptional behavior.

            Examples:
            Examines the 'my_function' node in an AST and increments a counter, adds the
             fully qualified function name to a list, and logs information about the
             examined function.   visit_FunctionDef(self,
             ast.FunctionDef(name='my_function'))

            Notes:
            This function is part of a larger AST visitor class that processes Python source
             code. The specific behavior and side effects of this function depend on the
             context in which it is used.
            """
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            """
            Formats a docstring to add indentation and wrapping for readability.

            This function takes a docstring as input, calculates the total width for
            wrapping based on the leading whitespace and a default width, then formats the
            lines of the docstring using the TextWrapper class from the textwrap module. It
            returns the formatted docstring with triple quotes added at the beginning and
            end.

            Parameters:
            self (object): The instance of the class that this function is a part of.
            docstring (string): The docstring to be formatted.

            Returns:
            string: The formatted docstring with triple quotes added at the beginning and
                    end.

            Examples:
            Formats a simple docstring to add indentation and wrapping.
             format_docstring(None, 'This is a sample docstring.')

            Notes:
            This function uses the textwrap module to format the docstring.
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
            Updates the docstring of a specified function in a code file.

            This function updates the docstring of a specified function by parsing the code,
            validating the existing docstring if requested, and then updating or stripping
            the docstring based on options provided. It returns the updated node and an
            action taken string indicating the outcome.

            Parameters:
            self (object): The object instance of the class containing this method.
            fully_qualified_function_name (string): The fully qualified name of the function
                        whose docstring is to be updated.
            function_name (string): The name of the function whose docstring is to be
                        updated.
            current_docstring (string): The current docstring of the function.
            updated_node (object): The updated node representing the function's AST.
            action_taken (string): A string indicating the action taken by this method, such
                        as 'updated existing docstring' or 'stripped existing docstring'.

            Returns:
            tuple: Returns a tuple containing the updated node and an action taken string.

            Errors:
            ValueError: Thrown if the input parameters are invalid or do not match expected
                        types.
            SyntaxError: Thrown if the code contains syntax errors that prevent parsing.

            Examples:
            Updates the docstring of a function in a code file.   update_docstring(self,
             'example.module.example_function', 'example_function', current_docstring,
             updated_node, action_taken)

            Notes:
            This method relies on various libraries and services to parse and generate code.
             Ensure these are installed and the input parameters are valid for proper
             operation.
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
            Creates a new docstring for a given function and updates its source code.

            This function appends a new docstring to an existing function's source code,
            using information from the `fully_qualified_function_name`, `function_name`,
            `current_docstring`, and `updated_node` parameters. If the option to create a
            new docstring is enabled, it generates and formats the new docstring before
            updating the function's body.

            Parameters:
            self (object): The object instance of this class.
            fully_qualified_function_name (string): The fully qualified name of the function
                        for which to create a new docstring.
            function_name (string): The name of the function for which to create a new
                        docstring.
            current_docstring (string): The current docstring of the function, used as a
                        starting point for generating the new docstring.
            updated_node (object): The updated node representing the function's source code
                        after modifications.
            action_taken (string): A string indicating what action was taken by this
                        function (e.g., 'created a new docstring' or 'failed to create new
                        docstring, leaving as-is').

            Returns:
            tuple: Returns a tuple containing the updated node and an action taken string.

            Errors:
            NoneError: Thrown if the generated new docstring is None, indicating failure to
                       create a new docstring.

            Examples:
            Creates a new docstring for the function 'my_function' with fully qualified name
             'package.module.my_function'.   create_docstring(self,
             'package.module.my_function', 'my_function', current_docstring, updated_node,
             action_taken)

            Notes:
            This function relies on other class instances and services to generate and
             format the new docstring. Ensure these dependencies are properly set up for
             proper operation.
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
            Handles the processing of a FunctionDef node in the abstract syntax tree (AST)
            of Python source code.

            This function determines whether to process or skip the given FunctionDef node
            based on its nesting level and the qualified function names list. If the node is
            processed, it updates the docstring if necessary and removes leading whitespace
            from the node's body. Finally, it logs a report of the action taken and returns
            the updated node.

            Parameters:
            self (object): The instance of the class containing this method.
            original_node (ast.FunctionDef): The original FunctionDef node in the AST.
            updated_node (ast.FunctionDef): The updated FunctionDef node after processing.

            Returns:
            ast.FunctionDef: The processed FunctionDef node.

            Errors:
            ValueError: Thrown if the function level or class level exceeds the specified
                        depth limit.

            Examples:
            Processes a FunctionDef node and updates its docstring if necessary.
             leave_FunctionDef(self, original_node, updated_node)

            Notes:
            This function relies on the 'ast' library to work with Python source code.
             Ensure this library is installed for proper operation.
            """
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
