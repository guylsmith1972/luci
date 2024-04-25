from ollama import OllamaService
import libcst as cst
import queries
import re
import warnings


class DocstringService:
    class DocstringUpdater(cst.CSTTransformer):
        def __init__(self, docstring_service, default_indent, paths_of_interest):
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
            

        def convert_functiondef_to_string(self, function_def):
            code = cst.Module([])
            code.body.append(function_def)
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
        
        def get_function_path(self):
            return '.'.join(self.function_path)
            
        def visit_ClassDef(self, node):
            self.class_level += 1
            self.function_path.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.debug(f"Examining class: {self.get_function_path()}")

        def leave_ClassDef(self, original_node, updated_node):
            self.class_level -= 1
            self.function_path.pop()
            self.remove_leading_whitespace()
            return updated_node

        def visit_FunctionDef(self, node):
            self.function_level += 1
            self.function_path.append(node.name.value)
            self.add_leading_whitespace(node)
            self.logger.debug(f"Examining function: {self.get_function_path()}")
            
        def pad_docstring(self, docstring):
            leading_whitespace = self.get_leading_whitespace()
            lines = docstring.split('\n')
            lws = '\n' + leading_whitespace
            return lws.join(lines)
            
        def update_docstring(self, function_name, function_code, current_docstring, updated_node, action_taken):
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
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_name, function_code, current_docstring, self.options)
                body_statements = list(updated_node.body.body)
                if isinstance(body_statements[0], cst.SimpleStatementLine) and isinstance(body_statements[0].body[0], cst.Expr):
                    if isinstance(body_statements[0].body[0].value, cst.SimpleString):
                        body_statements[0] = cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{self.pad_docstring(new_docstring)}"""'))])
                        action_taken = "updated existing docstring"
                        self.logger.debug(f'new docstring: {new_docstring}')
                updated_body = cst.IndentedBlock(body=body_statements)
                updated_node = updated_node.with_changes(body=updated_body)
            return updated_node, action_taken
        
        def create_docstring(self, function_name, function_code, current_docstring, updated_node, action_taken):
            if self.options.create:
                # Append new docstring
                self.logger.debug('Creating a new docstring')
                new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_name, function_code, current_docstring, self.options)
                if new_docstring is not None:
                    body_statements = [cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{self.pad_docstring(new_docstring)}"""'))])] + list(updated_node.body.body)
                    updated_body = cst.IndentedBlock(body=body_statements)
                    updated_node = updated_node.with_changes(body=updated_body)
                    self.logger.debug(f'new docstring: {new_docstring}')
                    action_taken = "created a new docstring"
                else:
                    action_taken = "failed to create new docstring, leaving as-is" 
            return updated_node, action_taken
                                
        def leave_FunctionDef(self, original_node, updated_node):
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
                        updated_node, action_taken = self.create_docstring(function_name, function_code, current_docstring, updated_node, action_taken)
                    else:
                        updated_node, action_taken = self.update_docstring(function_name, function_code, current_docstring, updated_node, action_taken)
            self.remove_leading_whitespace()


            self.function_level -= 1
            report = f"{function_path}: {action_taken}"
            self.logger.info(report)
            self.reports.append(report)
            self.function_path.pop()
            return updated_node

    def __init__(self, options, logger):
        self.logger = logger
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, paths_of_interest):
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = cst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, paths_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports
