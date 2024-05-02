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
            Initializes the object with necessary components for processing Python code.

            Parameters:
              self (object): The object being initialized.
              docstring_service (obj): An instance of a class that provides services
                                     related to documenting Python functions and classes.
              default_indent (int): The default indentation level used when formatting
                                   docstrings.
              functions_of_interest (list): A list of function names or patterns
                                            that should be processed for generating
                                            reports. These may include wildcards or
                                            regular expressions.

                Returns:
              None: This method does not return any value. It initializes the object's
                   attributes and prepares it for further processing.
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
            Converts a `cst.FunctionDef` node into its string representation.

            Parameters:
              self: The instance of the class this method belongs to. (Not used in this
            function)
              function_def: The `FunctionDef` node to convert.
              remove_docstring: If True, removes any existing docstring from the function
            definition.

            Returns:
              A string representing the `function_def` node.

            Note:
              This method does not modify the original `function_def` object. It creates a
            new code representation based on the provided FunctionDef.
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
            Adds the leading whitespace of a given node to the list of tracked leading
            whitespace.

            This method reads the source code of the node, identifies the leading
            whitespace,
            and appends it to the internal list. This list is used elsewhere in the class.
            The identified leading whitespace is taken from the last line of the code block,
            assuming that this is representative of the overall leading whitespace pattern.

            Parameters:
              self (object): The instance of the class that contains this method.
              node (cst.Node): The node for which to extract and store the leading
            whitespace.
            Returns:
              None: This method does not return any value. It modifies the internal state
                    by appending the identified leading whitespace to the list.
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
            Gets the leading whitespace from this object.

            Returns:
              str: The leading whitespace.

            Example:
            > obj.get_leading_whitespace()
            # This returns the leading whitespace for the given object.
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """
            Removes one occurrence of leading whitespace from the internal stack.

            This method is used to simulate the behavior of a tape in a Turing machine,
            where the leading whitespace represents the current position on the tape. It
            effectively moves the tape one step to the right.
            """
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
            """
            Returns the fully qualified name of a function, including its module and class
            (if any), in dot-separated format.

            Parameters:
              None: This method does not take any parameters.

            Raises:
              AttributeError: If the object this method is called on does not have an
            attribute named `fully_qualified_function_name`.

            Example:
            > obj.get_fully_qualified_function_name()
            # Returns the fully qualified name of a function in dot-separated format.
            """
            return '.'.join(self.fully_qualified_function_name)

        def visit_ClassDef(self, node):
            """
            This method is a visitor for the ClassDef node in an Abstract Syntax Tree (AST).
            When visiting a ClassDef, it increments its internal class level counter,
            appends the class name to the fully qualified function name list, and
            adds leading whitespace to subsequent nodes. Finally, it logs a message
            indicating that it has started examining the class.

            Parameters:
              self: The instance of this visitor class.
              node: The ClassDef node in the AST.

            Returns:
              None: This method does not return any value. It modifies the internal state
                    of this visitor and logs a message.

            Example:
              Visit a ClassDef node in an AST, examine its properties,
              and log a message about it.
            """
            self.class_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining class: {self.get_fully_qualified_function_name()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Remove a class definition from the abstract syntax tree (AST).
            This method is called by the `visit` method of the AST visitor.
            It updates the internal state and returns the modified node.

            Parameters:
              self: The current object, which should be an instance of this class.
              original_node (ast.ClassDef): The original class definition node.
              updated_node (ast.ClassDef): The updated class definition node.

            Returns:
              ast.ClassDef: The updated class definition node.
            """
            self.class_level -= 1
            self.fully_qualified_function_name.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """
            Visit a FunctionDef AST node.

            This method is called when the parser encounters a Python function definition.
            It increments the current function level, appends the function name to
            the fully qualified function name list, and adds leading whitespace according
            to the function level. It also logs an informational message indicating
            which function it is examining.

            Parameters:
              self (object): The object instance that this method belongs to.
              node (ast.FunctionDef): The AST node representing a Python function
            definition.

            Raises:
              None: This method does not raise any exceptions.

            Returns:
              None: This method does not return any value. It modifies the object instance
                    and logs information.

            Example:
            > visit_FunctionDef(self, node)
            # This will examine the given FunctionDef node.
            """
            self.function_level += 1
            self.fully_qualified_function_name.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.info(f"Examining function: {self.get_fully_qualified_function_name()}")

        def format_docstring(self, docstring):
            """
            Formats a given docstring by wrapping it to fit within a certain width.

            This method takes into account the leading whitespace of the original
            docstring and uses this information to properly indent the wrapped lines.
            The resulting formatted docstring is then returned as a new string,
            surrounded by triple quotes, suitable for pasting into Python code.

            Parameters:
              self: The object that this method belongs to (not used in this implementation)
              docstring: The original docstring to be formatted

            Returns:
              str: The formatted docstring with the specified leading whitespace and
                   width constraints.
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
            This method updates the docstring of a given function in a Python file.
            It takes four parameters: self (the instance), fully_qualified_function_name,
            function_name, current_docstring, and updated_node. It uses these inputs to
            validate the existing docstring if validation is enabled, strip or update
            the existing docstring as needed, format the new docstring if necessary,
            and then returns the updated node along with a description of the action
            taken.

            Parameters:
              self (object): The instance.
              fully_qualified_function_name (str): The full name of the function.
              function_name (str): The simple name of the function.
              current_docstring (str): The existing docstring of the function.
              updated_node (cst node): The updated node with the new docstring.

            Returns:
              tuple: A tuple containing the updated node and a description of the action
            taken, such as "stripped existing docstring" or "updated existing docstring".
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
            Creates a new docstring for a given function based on its name and code.

            This method takes the fully qualified function name, function name, current
            docstring,
            updated node representing the function, and an action taken flag. It uses these
            inputs
            to generate a new docstring using the OLLAMA service. The generated docstring is
            then
            formatted and appended to the updated node's body. The method returns the
            updated node
            and the corresponding action taken.

            Parameters:
              self: The object instance.
              fully_qualified_function_name (str): The fully qualified name of the function.
              function_name (str): The name of the function.
              current_docstring (str): The current docstring of the function.
              updated_node: The node representing the function, updated with new code.
              action_taken (str): A flag indicating the action taken.

            Returns:
              tuple: A tuple containing the updated node and the corresponding action taken.
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
            Updates the FunctionDef node.

            Parameters:
              original_node (ast.FunctionDef): The original function definition.
              updated_node (ast.FunctionDef): The updated function definition.

            Returns:
              ast.FunctionDef: The updated function definition.
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
        Initializes an instance of this class.

        Parameters:
          self (object): The instance itself.
          options (dict): A dictionary containing the command-line options passed to the
        script.
          logger (Logger): An object used for logging messages.

        Note:
        This constructor does not perform any validation or processing on the input
        parameters. It simply assigns them to instance variables and initializes an
        OllamaService instance.
        """
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, functions_of_interest):
        """
        Updates the docstrings of one or more specified functions within a Python source
        file.
        This method reads a Python file, parses its source code to find and update the
        docstrings of the functions listed in `functions_of_interest`, using information
        provided by the object passed as `self`. The updated source code is then
        returned along with any reports of modifications made and a list of modified
        functions. If no functions are found that match those specified, an empty string
        is returned for the code.

        Parameters:
          self: An instance of a class containing information used to update
                docstrings.
          file_path (str): The path to the Python source file where the functions
                          whose docstrings need updating are located.
          functions_of_interest (list[str]): A list of function names whose docstrings
                                             should be updated.

        Returns:
          tuple: A tuple containing the updated code, a report of modifications made,
                 and a list of modified functions. If no matching functions were found,
                 an empty string is returned for the code.
        """
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, functions_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
