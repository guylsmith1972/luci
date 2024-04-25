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
            Initializes the object by setting up various attributes and references.
            Sets up logging, default indentation, and other parameters. This method is
            called when an instance of this class is created.
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
            Convert a given `FunctionDef` node to a string, optionally removing the
            docstring.
            This function takes in a `FunctionDef` object and an optional `remove_docstring`
            flag.
            If `remove_docstring` is set to True, it will remove the first line of the
            function's body
            if it matches the format of a Python docstring (i.e., a string literal at the
            start
            of the function). The resulting code string will not include this docstring. If
            `remove_docstring` is False or omitted, the original docstring will be
            preserved.
            This function returns the converted code as a string.
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
            Adds the leading whitespace of a node to a list.

            This function takes a CST (Concrete Syntax Tree) node and extracts its leading
            whitespace. It then appends this whitespace to the `leading_whitespace`
            attribute
            of the current object, which is presumably used to keep track of the leading
            whitespace found in all nodes visited so far.

            Parameters:
            node: The CST node whose leading whitespace needs to be extracted.
            self: The object that will receive the extracted leading whitespace.
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
            Returns the leading whitespace from this TextBuffer object.
            This is the amount of whitespace that comes before any content in this buffer.
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """
            Removes the last leading whitespace character from the internal stack.
            This method is part of a mechanism to keep track of and manage leading
            whitespaces within some context, possibly for formatting or parsing purposes.
            The removed whitespace is assumed to be stored in an internal data structure
            accessible through self.leading_whitespace.
            """
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            """
            Returns the fully qualified name of a function.
            This method returns the fully qualified name of the function,
            including its module and class names if it is defined within a class.
            The returned string is in dot notation, e.g., "module.Class.function".
            """
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            """
            Visit a ClassDef node.

            This method is called when the parser encounters a class definition.
            It increments the current class level, appends the class name to
            the fully qualified function name stack and then visits any nested
            function definitions. This method also adds leading whitespace based on
            the current indentation level and logs a message indicating that the
            class is being examined.

            Parameters:
            self (object): The object instance.

            node (ast.ClassDef): The node representing the class definition.
            Returns:
            None: This method does not return any value.
            """
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Replaces a ClassDef node with its subclass.
            This method is called during the traversal of an AST tree to replace a ClassDef
            node with its subclass.
            It decreases the class level, removes the fully qualified function name from the
            stack, and removes leading whitespace.

            Parameters:
            self: The current state of the visitor
            original_node (ast.ClassDef): The original ClassDef node
            updated_node: The updated ClassDef node

            Returns:
            ast.ClassDef: The updated ClassDef node
            """
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """
            Visit a FunctionDef AST node.

            This method is called when the AST visitor encounters a FunctionDef node.
            It updates the state of the visitor by incrementing the current function level,
            appending the function name to the fully qualified function name, and
            adding leading whitespace for this function. It also logs an informational
            message indicating that it is examining the given function.

            This method is part of an AST visitor class, and its primary purpose is
            to collect information about functions as they are visited in the AST.
            It is designed to be used with the astor library for parsing Python code.
            """
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            """
            Formats a docstring for display.

            This function takes in a docstring and formats it to be displayed nicely.
            It preserves the original formatting of the docstring, but adds some
            leading whitespace to make it look nicer when displayed with other
            docstrings. The formatted docstring is returned as a string, ready for
            display.

            Parameters:
            self (object): This function is called from an object's method,
            so self needs to be included in the parameters.
            docstring (str): The docstring that should be formatted.

            Returns:
            str: The formatted docstring, ready for display.
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
            Updates the docstring of a function in a Python file.

            This function takes an existing node representing a function definition,
            and either strips or updates its docstring based on user options. If
            the update is successful, it returns the updated node and the action
            taken (either "stripped" or "updated"). Otherwise, it does nothing and
            returns None.

            Parameters:
            fully_qualified_function_name (str): The fully qualified name of the function.
            function_name (str): The name of the function.
            current_docstring (object): The current docstring of the function.
            updated_node (object): The updated node representing the function definition.
            action_taken (str): A string indicating whether the docstring was stripped or
            updated.

            Returns:
            tuple: A tuple containing the updated node and the action taken. If no update
            was made, it returns None for both values.
            """
            function_code = self.convert_functiondef_to_string(updated_node)
            do_update = self.options.update
            strip_docstring = self.options.strip
            if self.options.validate:
                self.logger.debug('Validating existing docstring')
                validated, assessment = queries.validate_docstring(self.docstring_service.ollama, function_name, function_code, current_docstring, self.options)
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
            Creates a new docstring for the given function and updates the AST accordingly.
            This method appends a new docstring to the specified function based on the
            provided parameters.
            The new docstring is generated using the Ollama service and formatted according
            to the user's options.

            Parameters:
            fully_qualified_function_name (str): The fully qualified name of the function
            for which the new docstring needs to be created.
            function_name (str): The name of the function for which the new docstring needs
            to be created.
            current_docstring (str): The current docstring of the function, if any.
            updated_node (cst.FunctionDef): The updated AST node representing the function
            with its new docstring.
            action_taken (str): A string indicating what action was taken by this method
            (either creating a new docstring or leaving it as-is).

            Returns:
            updated_node (cst.FunctionDef): The updated AST node with the new docstring.
            action_taken (str): A string indicating whether a new docstring was created or
            not.
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
            Leave the FunctionDef node, updating any relevant actions taken. This function
            is responsible for deciding whether to process a given FunctionDef node based on
            its nesting level and whether it's in the list of functions of interest. If the
            function should be processed, it may create or update its docstring depending on
            its current state. Finally, it removes leading whitespace from the updated node
            and decrements the current nesting level before reporting any actions taken back
            to the logger.

            Parameters:
            self (object): This is a reference to the object that this method belongs to.
            original_node (ast.FunctionDef): The original FunctionDef node being processed.
            updated_node (ast.FunctionDef): The updated FunctionDef node after processing,
            which may have had its docstring created or updated.

            Returns:
            updated_node (ast.FunctionDef): The updated FunctionDef node, potentially with a
            new or updated docstring.
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
        Initialize an instance of this class.

        Parameters:
        options: The options to use for this instance.
        logger: A logger object to use for logging messages.

        Note:
        This is the constructor method, called when a new instance of this class is
        created. It sets up the necessary state variables for this instance.
        """
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, functions_of_interest):
        """
        Updates the docstrings of a list of specified functions within a Python source
        file.
        This function reads a Python file, parses its source code to find the docstrings
        of the specified functions, and then updates their existing docstrings with the
        provided information. The updated source code is not written back to the file,
        but instead returns the modified source code as well as any report messages
        and modified status.
        Parameters: file_path (str): The path to the Python source file where the
        functions are located. functions_of_interest (list[str]): A list of function
        names
        whose docstrings need updating.
        Returns: tuple[code, reports, modified]: A tuple containing the updated code,
        a list of report messages, and a boolean indicating whether any modifications
        were made.
        Example: >>> document_file(self, "example.py", ["my_function1", "my_function2"])
        # This will update the docstrings of `my_function1` and `my_function2` in
        # `example.py` file. Note: This function does not modify the original source
        file.
        """
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, functions_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
