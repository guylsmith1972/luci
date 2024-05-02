import textwrap
from ollama import OllamaService
import libcst as cst
import queries
import re
import warnings


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, default_indent, functions_of_interest):
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
            self.leading_whitespace.pop()
        
        def get_fully_qualified_function_name(self):
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
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, functions_of_interest):
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, functions_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports, transformer.modified
