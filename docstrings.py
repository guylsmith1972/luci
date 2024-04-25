from ollama import OllamaService
import libcst as cst
import queries
import re
import warnings


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, default_indent, paths_of_interest):
            """Initializes a DocStringParser object.
            
            This constructor sets up the necessary attributes and configurations for parsing and analyzing Python source code. It takes in three main parameters: a `docstring_service` instance, a default indentation level, and a list of paths that are considered of interest for analysis.
            
            These parameters determine how this object behaves when it's used to parse and analyze Python source files.
            
            Note: This constructor is only intended to be called by the class itself, not directly by external code. It sets up internal state variables that are used throughout the class's methods."""
            self.class_level = 0
            self.function_level = 0
            self.function_path = []
            self.default_indent = default_indent
            self.docstring_service = docstring_service
            self.options = docstring_service.options
            self.reports = []
            self.paths_of_interest = paths_of_interest
            self.logger = docstring_service.logger
            self.leading_whitespace = []
            self.modified = False

        def convert_functiondef_to_string(self, function_def, remove_docstring=False):
            """
            Convert a CST FunctionDef node to its string representation and optionally remove its docstring.
    
            Parameters:
            self (object): The instance of the class this method belongs to.
            function_def (cst.FunctionDef): The CST node representing a Python function definition.
            remove_docstring (bool): If True, removes the function's docstring before generating the source code.
    
            Returns:
            str: The string representation of the given function definition.
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
            Adds leading whitespace to a CST node.
            
            This function is used to add leading whitespace to a given CST (Concrete Syntax Tree) node. The added whitespace is taken from the CST node itself, specifically from the last line of its code. This can be useful when working with CSTs and needing to preserve or modify their original structure.
            
            Parameters:
            self: The object that this function belongs to.
            node: The CST node whose leading whitespace needs to be updated.
            
            Note:
            This function is quite inefficient and may not work well for large CSTs, but it is a simple way to achieve the desired result. It is up to the developer to decide whether or not to use this method in their code."""
            # This is outrageously ineffient, but I haven't found a better way (yet)
            code = cst.Module([])
            code.body.append(node.body)
            match = re.match(r'\s*', code.code)
            lws = match.group(0) if match else ''
            lws = lws.split('\n')[-1]
            self.leading_whitespace.append(lws)
            
        def get_leading_whitespace(self):
            """
            Returns the leading whitespace characters stored in this object.
            
            This method is used to retrieve the leading whitespace characters that were encountered when parsing a source file. The leading whitespace is stored as a string and can be accessed through this method.
            
            Note: This method does not handle cases where the leading whitespace changes. It simply returns the stored value.
            """
            return ''.join(self.leading_whitespace)
        
        def remove_leading_whitespace(self):
            """Removes the last character from the internal buffer of leading whitespace."""
            self.leading_whitespace.pop()
        
        def get_function_path(self):
            """
            Returns the full path to the function, including its module and package structure.
            This method returns a string representing the full path to the function,
            including the module name and package structure. The returned path is in the form "package.module:function".
            Note: This method assumes that the 'function_path' attribute has been set previously, which represents the path from the root directory to the function."""
            return '.'.join(self.function_path)
        def visit_ClassDef(self, node):
            """
            Visits a ClassDef AST node.
            
            This method is part of an abstract syntax tree (AST) visitor and is called when the
            visitor encounters a class definition. It increments the class level, updates the function path,
            and adds leading whitespace before visiting any child nodes.
            """
            self.class_level += 1
            self.function_path.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.debug(f"Examining class: {self.get_function_path()}")

        def leave_ClassDef(self, original_node, updated_node):
            """
            Replaces a ClassDef node in an Abstract Syntax Tree (AST) with an updated version.
            
            This method is part of the AST visitor pattern and is responsible for updating the class-level information when a ClassDef node is replaced. It decrements the class level counter, removes the current function path from the stack, and then removes leading whitespace from the updated node before returning it."""
            self.class_level -= 1
            self.function_path.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            """Visits a FunctionDef node in the AST and processes its contents.
            This method is part of a traversal mechanism that inspects each function
            definition in a Python module. It records the current function's level,
            name, and path within the module hierarchy, and then calls another
            method to add leading whitespace to the function's contents."""
            self.function_level += 1
            self.function_path.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.debug(f"Examining function: {self.get_function_path()}")
            
        def pad_docstring(self, docstring):
            """Pads a given docstring with consistent leading whitespace, making it suitable for use as the docstring of a class or function.
            
            This method takes a docstring string and returns the same string but with each line padded with the same amount of whitespace that the longest line already has. This ensures that all lines have the same indentation level.
            
            Parameters:
            self: The instance of the class this method is part of.
            docstring (str): The docstring string to be padded.
            
            Returns:
            The padded docstring string."""
            leading_whitespace = self.get_leading_whitespace()
            lines = docstring.split('\n')
            lws = '\n' + leading_whitespace
            return lws.join([l.strip() for l in lines])
        
        def update_docstring(self, function_path, function_name, function_code, current_docstring, updated_node, action_taken):
            """Updates the docstring of a function based on provided code and options.
            
            This method checks if the update option is enabled. If it is, it validates
            the existing docstring using Ollama and generates a new one based on the
            function's path, name, code, and current docstring. It then updates the
            existing docstring with the new one and logs the action taken. If the
            validate option is also enabled, it reports the validation results.
            
            Parameters:
            self (object): The object instance that this method belongs to.
            function_path (str): The path of the function.
            function_name (str): The name of the function.
            function_code (str): The code of the function.
            current_docstring (str): The current docstring of the function.
            updated_node (cst.Node): The updated node representing the function's
            code with the new docstring.
            action_taken (str): A string indicating what action was taken on the
            docstring.
            
            Returns:
            tuple: A tuple containing the updated node and a string indicating the
            action taken. If no update is needed, an empty tuple is returned."""
            do_update = self.options.update
            if self.options.validate:
                self.logger.debug('Validating existing docstring')
                validated, assessment = queries.validate_docstring(self.docstring_service.ollama, function_name, function_code, f'"""{current_docstring}"""', self.options)
                if validated:
                    do_update = False
                report = f'Validation report for {function_name}: {"PASS" if validated else "FAILED"}: {assessment}'
                self.reports.append(report)
            if do_update:
                # Replace existing docstring
                self.logger.debug('Replacing existing docstring')
                self.logger.debug(f'existing docstring: {current_docstring}')
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_path, function_name, function_code, current_docstring, self.options)
                body_statements = list(updated_node.body.body)
                if isinstance(body_statements[0], cst.SimpleStatementLine) and isinstance(body_statements[0].body[0], cst.Expr):
                    if isinstance(body_statements[0].body[0].value, cst.SimpleString):
                        body_statements[0] = cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{self.pad_docstring(new_docstring)}"""'))])
                        action_taken = "updated existing docstring"
                        self.modified = True
                updated_body = cst.IndentedBlock(body=body_statements)
                updated_node = updated_node.with_changes(body=updated_body)
            return updated_node, action_taken
        
        def create_docstring(self, function_path, function_name, function_code, current_docstring, updated_node, action_taken):
            """Creates and updates the documentation for a given function. This method takes in the current function code, the desired new documentation, and other necessary parameters. It then uses these inputs to generate a new documentation string and updates the function's body with this new information. If the generation of the new documentation fails, it will leave the function's existing documentation unchanged.
            
            Parameters:
            self (object): The object containing the methods and attributes required for this operation.
            function_path (str): The path to the Python file where the function is located.
            function_name (str): The name of the function being processed.
            function_code (str): The source code of the function.
            current_docstring (str): The existing documentation string for the function.
            updated_node (ast.FunctionDef): The parsed AST node representing the function's updated body.
            action_taken (str): A message indicating what action was taken on the function's documentation.
            
            Returns:
            tuple: A tuple containing the updated function node and a description of the action taken. If an error occurs during the generation process, this method will return the original function node with a corresponding failure message."""
            if self.options.create:
                # Append new docstring
                self.logger.debug('Creating a new docstring')
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_path, function_name, function_code, current_docstring, self.options)
                if new_docstring is not None:
                    body_statements = [cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{self.pad_docstring(new_docstring)}"""'))])] + list(updated_node.body.body)
                    updated_body = cst.IndentedBlock(body=body_statements)
                    updated_node = updated_node.with_changes(body=updated_body)
                    self.logger.debug(f'new docstring: {new_docstring}')
                    action_taken = "created a new docstring"
                    self.modified = True
                else:
                    action_taken = "failed to create new docstring, leaving as-is" 
            return updated_node, action_taken
        
        def leave_FunctionDef(self, original_node, updated_node):
            """
            Leave a FunctionDef node, but first check the depth and paths of interest.
            If the function is too deeply nested or not in the list of decorated filenames,
            skip processing. If it's in the list, process it by updating its docstring if necessary,
            and then remove leading whitespace from the updated node.
            Finally, decrement the function level and append a report to the logger.
            The updated node is returned.
            Parameters:
            self
            original_node (FunctionDef): The original FunctionDef node
            updated_node (FunctionDef): The updated FunctionDef node
            Returns:
            updated_node: The updated FunctionDef node after processing
            Raises:
            None: No exceptions are raised by this function
            Note:
            This function does not handle functions defined within classes or other scopes; only top-level functions are supported.
            Example:
            leave_FunctionDef(self, original_node, updated_node)
            """
            action_taken = "did nothing"
            function_name = updated_node.name.value
            function_path = self.get_function_path()

            if self.function_level > self.options.depth or self.class_level > self.options.depth:
                action_taken = f'skipped due to high nesting level -- function_level: {self.function_level}, class_level: {self.class_level}'
                if self.paths_of_interest is not None and function_path in self.paths_of_interest:
                    warnings.warn(f'You specified {function_path} to be processed, but the depth setting is too low ({self.options.depth}) to process this. Increase the depth with the "--depth {max(self.function_level, self.class_level)}" option.')
            else:
                do_process = True
                if self.paths_of_interest is not None:
                    do_process = function_path in self.paths_of_interest 
                    if not do_process:
                        action_taken = f'Skipped because it is not in the decorated filename list of functions to document.'
                if do_process:
                    current_docstring = updated_node.get_docstring()
                    function_code = self.convert_functiondef_to_string(updated_node)
                            
                    if current_docstring is None:
                        updated_node, action_taken = self.create_docstring(function_path, function_name, function_code, current_docstring, updated_node, action_taken)
                    else:
                        updated_node, action_taken = self.update_docstring(function_path, function_name, function_code, current_docstring, updated_node, action_taken)
            self.remove_leading_whitespace()


            self.function_level -= 1
            report = f"{function_path}: {action_taken}"
            self.logger.info(report)
            self.reports.append(report)
            self.function_path.pop()
            return updated_node

    def __init__(self, options, logger):
        """Initializes a new instance of this class.
        
        This is the constructor method for this class. It sets up the necessary
        objects and attributes to start working with the provided options and
        logger. The logger is used to write logs, and OllamaService provides
        integration with Ollama API. The options parameter allows customization
        of the class's behavior.
        
        Parameters:
        self (object): The new instance of this class.
        options (dict): A dictionary containing options and their values.
        logger (logging.Logger): A logging logger object."""
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, paths_of_interest):
        """
        Documents a Python file by updating its docstrings according to the provided paths of interest.
        This function reads a Python source file, parses its source code using cst (a parsing library), and then updates the docstrings of relevant functions and classes based on the given paths of interest.
        
        Parameters:
        file_path (str): The path to the Python source file that needs documentation.
        paths_of_interest (list[str]): A list of strings representing the paths of interest within the file. These can be function names or class names.
        
        Returns:
        A tuple containing two values:
        
        * The modified source code with updated docstrings.
        * A report object containing information about the docstring updates, including any errors or warnings that occurred during processing.
        
        Example:
        >>> document_file(self, "example.py", ["path.to.module1", "path.to.module2"])
        # This will update the docstrings of modules "module1" and "module2" in the file "example.py".
        
        Note: 
        This function assumes that the provided paths of interest are valid identifiers within the Python source file. It does not perform any validation or error handling for these paths, so it may raise exceptions if they are invalid."""
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, paths_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
