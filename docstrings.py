import textwrap
from ollama import OllamaService
import libcst as cst
import queries
import re
import warnings


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, default_indent, functions_of_interest):
            """
            Initializes an instance of the class.

            Parameters:
            self (object): The instance itself.
            docstring_service (object): A service that provides necessary tools for working
            with Python docstrings.
            default_indent (int): The default indentation level to use when generating
            docstrings.
            functions_of_interest (list or tuple): A list of functions whose docstrings will
            be analyzed and generated.

            Attributes:
            class_level (int): The current level of nesting within a class definition.
            function_level (int): The current level of nesting within a function definition.
            fully_qualified_function_name (list): A list containing the fully qualified name
            of the function being processed.
            default_indent (int): The default indentation level used when generating
            docstrings.
            docstring_service (object): The service providing tools for working with Python
            docstrings.
            options (dict): Options passed to the docstring generation process.
            reports (list): A list of reports generated during the docstring analysis and
            generation process.
            functions_of_interest (list or tuple): A list of functions whose docstrings will
            be analyzed and generated.
            logger (logging.Logger): The logger used for logging messages during the
            docstring processing process.
            leading_whitespace (list): A list containing leading whitespace characters in
            the input code.
            modified (bool): Indicates whether any modifications were made to the input
            code.

            Note: This is a constructor method, which is called when an instance of this
            class is created. It initializes the instance's attributes with the provided
            values and sets up necessary tools for processing Python docstrings.
            """
            self.class_level = 0
            self.function_level = 0
            self.fully_qualified_function_name = []
            self.default_indent = default_indent
            self.docstring_service = docstring_service
            self.options = docstring_service.options
            self.reports = []
            self.functions_of_interest = functions_of_interest
            self.logger = docstring_service.logger
            self.leading_whitespace = []
            self.modified = False

        def convert_functiondef_to_string(self, function_def, remove_docstring=False):
            """
            Converts a function definition (FunctionDef) to its string representation.
            The conversion process can remove the docstring if `remove_docstring` is set to
            True.
            This function is intended for use with the `cst` module, which provides abstract
            syntax trees (ASTs) of Python code.

            Parameters:
            self: The instance or class using this method. This parameter is typically not
            used in this method.
            function_def: A FunctionDef object representing a Python function definition.
            remove_docstring (bool): If True, removes the docstring from the function
            definition.

            Returns:
            str: The string representation of the function definition, possibly without its
            docstring.
            Raises:
            ValueError: If an error occurs during the conversion process.
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
            Adds the leading whitespace from a given AST node to this object's list of
            leading whitespaces.
            This function takes an Abstract Syntax Tree (AST) node as input and extracts the
            leading whitespace(s) from it. The extracted leading whitespace is then added to
            this object's list of leading whitespaces, which can be useful in certain
            context where leading whitespaces need to be preserved or manipulated.
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
            Returns the leading whitespace characters from this object's internal state.

            This method provides a read-only access to the leading whitespace characters
            stored in this object. The returned string contains all leading whitespaces
            accumulated by this object.
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """
            Removes the leading whitespace from the stack.

            This method is used to remove the leading whitespace from the stack,
            which helps in processing the file correctly.
            It does not return any value. It modifies the internal state of the class.
            """
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            """
            Returns the fully qualified name of a function, which is its module path and
            name separated by dots.

            This method returns the fully qualified name of the function, which is useful
            for logging or debugging purposes.

            Example:
            >>> get_fully_qualified_function_name()
            # This will return the fully qualified name of the function.
            """
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            """
            Visits a ClassDef node in the Abstract Syntax Tree (AST) and collects relevant
            information about the class.

            This method is part of a recursive descent parser that walks through an AST
            representation of a Python source code file. It handles ClassDef nodes by
            incrementing the class level, appending the class name to the fully qualified
            function name, and adding leading whitespace for nested classes. The method also
            logs a message indicating which class it is currently examining.

            Parameters:
            node (ast.ClassDef): The node representing the class definition in the AST.
            self: An object with attributes that are modified by this method.

            Returns:
            None
            """
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Updates the node representing a class definition and its contents.
            This method is used to transform AST nodes during the process of updating
            docstrings in Python source code.
            It decrements the class level, removes the fully qualified function name from
            the stack, removes leading whitespace, and returns the updated node.
            """
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """
            Visits a FunctionDef AST node in the abstract syntax tree (AST) and processes
            its attributes.
            This method is called during an AST traversal, allowing the visitor to inspect
            or modify the nodes being visited.

            Parameters:
            node (ast.FunctionDef): The current FunctionDef node being visited in the AST.
            """
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            """
            Formats a given docstring to conform to a specific width and indentation.
            The function first calculates the total width based on the leading whitespace
            and a fixed value. It then splits the docstring into lines, wraps each line
            accordingly using the calculated width and initial indentation, and joins
            the wrapped lines back together. The resulting formatted docstring is
            returned.

            Parameters:
            self: The instance of the class that this method belongs to.
            docstring (str): The original docstring to be formatted.

            Returns:
            str: The formatted docstring with the specified leading whitespace and width.

            Note:
            This function uses the `textwrap` module from Python's standard library
            to perform the wrapping operation.
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
            Updates the docstring of a given function in a Python source file.
            This function takes into account the existence of an existing docstring and can
            either replace it or strip it based on user options.

            Parameters:
            self (object): The object containing the context for this method.
            fully_qualified_function_name (str): The fully qualified name of the function.
            function_name (str): The name of the function to update.
            current_docstring (str): The current docstring of the function.
            updated_node (object): An updated ast node representing the function with the
            new docstring.
            action_taken (str): A string indicating whether the existing docstring was
            stripped or replaced.

            Returns:
            tuple: A tuple containing the updated node and a description of the action
            taken.
            """
            function_code = self.convert_functiondef_to_string(updated_node)
            do_update = self.options.update
            strip_docstring = self.options.strip
            if self.options.validate:
                self.logger.debug('Validating existing docstring')
                validated, assessment = queries.validate_docstring(self.docstring_service.ollama, function_name, function_code, f'"""{current_docstring}"""', self.options)
                if validated:
                    do_update = False
                    strip_docstring = False
                report = f'Validation report for {function_name}: {"PASS" if validated else "FAILED"}: {assessment}'
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
                        new_docstring = queries.generate_docstring(self.docstring_service.ollama, fully_qualified_function_name, function_name, function_code, current_docstring, self.options)
                        new_docstring = self.format_docstring(new_docstring)
                        print(new_docstring)
                        body_statements[0] = cst.SimpleStatementLine([cst.Expr(cst.SimpleString(new_docstring))])
                        action_taken = "updated existing docstring"
                        self.modified = True

            updated_body = cst.IndentedBlock(body=body_statements)
            updated_node = updated_node.with_changes(body=updated_body)
            return updated_node, action_taken
        
        def create_docstring(self, fully_qualified_function_name, function_name, current_docstring, updated_node, action_taken):
            """
            Creates a new docstring for the given function based on the provided parameters.
            This function is part of a larger process that updates the docstrings of
            functions.
            It takes in the fully qualified name of the function, its name within the
            module,
            the current docstring, and the updated node representing the function
            definition.
            The function then generates a new docstring using an external service (Ollama),
            formats it according to certain rules, appends it to the function definition,
            and returns both the updated node and the action taken.

            Parameters:
            self (object): The instance of the class that this method is part of.
            fully_qualified_function_name (str): The full name of the function,
            including its module and class if applicable. This parameter is used to
            generate the new docstring using Ollama.
            function_name (str): The name of the function within its module.
            current_docstring (str): The current docstring of the function, which may
            be None or an empty string.
            updated_node (cst.FunctionDef): The node representing the updated
            function definition.
            action_taken (str): The action taken by this method, such as "created a new
            docstring" or "failed to create new docstring".

            Returns:
            updated_node (cst.FunctionDef): The updated function node with its new
            docstring appended.
            action_taken (str): The action taken by this method.

            Raises:
            None: This method does not raise any exceptions. It may fail to create a
            new docstring in certain circumstances, but it will still return the
            updated node and an appropriate message indicating what happened.
            """
            if self.options.create:
                # Append new docstring
                self.logger.debug('Creating a new docstring')
                function_code = self.convert_functiondef_to_string(updated_node)
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, fully_qualified_function_name, function_name, function_code, current_docstring, self.options)
                if new_docstring is not None:
                    new_docstring = self.format_docstring(new_docstring)
                    print(new_docstring)
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
            This method is part of a class that processes Python functions and their
            docstrings.
            It is called when a FunctionDef node is encountered during the processing of a
            Python file.

            The method checks if the function is within the allowed depth level. If it's
            not, or if it's not in the list of decorated functions to document, it skips
            processing this function.

            If the function is within the allowed depth and should be processed, the method
            either creates a new docstring for the function if it doesn't have one, or
            updates its existing docstring.

            After processing the function, the method removes leading whitespace from the
            function's body and decrements the current nesting level.
            Finally, it logs the action taken and appends the report to the list of reports.
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
        Initializes a new instance of the class.

         Parameters:
        self: The instance of the class to be initialized.
        options (dict): A dictionary containing initialization options.
        logger (Logger): A logging object used for logging messages during the life
        cycle of this instance.

         Note:
        This is a constructor method that sets up the necessary state and resources for
        the class to function properly. It does not return any value, as its primary
        purpose is to initialize the instance.
        """
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, functions_of_interest):
        """
        Updates the docstrings of a list of function names within a Python source file.
        This method takes a file path and a list of function names as input. It parses
        the source code,
        updates the docstrings for the specified functions, and returns the modified
        source code along with any error reports.

        Parameters:
        file_path (str): The path to the Python source file where the functions are
        defined.
        functions_of_interest (list[str]): A list of function names whose docstrings
        need to be updated.

        Returns:
        tuple: A tuple containing the modified source code as a string, a dictionary of
        error reports, and a boolean indicating whether any changes were made.

        Note:
        This method does not handle functions defined within classes or other scopes;
        only top-level functions are supported.
        """
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, functions_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
