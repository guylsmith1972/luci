from ollama import OllamaService
import libcst
import queries
import warnings


def comment_brief(str, options):
    if options.log_level > 0:
        print(str)
                
def comment_verbose(str, options):
    if options.log_level > 1:
        print(str)

class DocstringService:
    class DocstringUpdater(libcst.CSTTransformer):
        def __init__(self, docstring_service, default_indent, paths_of_interest):
            self.class_level = 0
            self.function_level = 0
            self.function_path = []
            self.default_indent = default_indent
            self.docstring_service = docstring_service
            self.options = docstring_service.options
            self.reports = []
            self.paths_of_interest = paths_of_interest
            
        def convert_functiondef_to_string(self, function_def):
            code = libcst.Module([])
            code.body.append(function_def)
            return code.code
        
        def get_function_path(self):
            return '.'.join(self.function_path)
            
        def visit_ClassDef(self, node):
            self.class_level += 1
            self.function_path.append(node.name.value)
            comment_brief(f"Examining class: {self.get_function_path()}", self.options)

        def leave_ClassDef(self, original_node, updated_node):
            self.class_level -= 1
            self.function_path.pop()
            return updated_node

        def visit_FunctionDef(self, node):
            self.function_level += 1
            self.function_path.append(node.name.value)
            comment_brief(f"Examining function: {self.get_function_path()}", self.options)
            
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
                    if function_path not in self.paths_of_interest:
                        action_taken = f'Skipped because it is not in the decorated filename list of functions to document.'
                        do_process = False
                if do_process:
                    current_docstring = updated_node.get_docstring()
                    function_code = self.convert_functiondef_to_string(updated_node)
                            
                    if current_docstring is not None:
                        do_update = self.options.update
                        if self.options.validate:
                            comment_brief('Validating existing docstring', self.options)
                            validated, assessment = queries.validate_docstring(self.docstring_service.ollama, function_name, function_code, f'"""{current_docstring}"""', self.options)
                            if validated:
                                do_update = False
                            report = f'Validation report for {function_name}: {"PASS" if validated else "FAILED"}: {assessment}'
                            self.reports.append(report)
                        if do_update:
                            # Replace existing docstring
                            comment_brief('Replacing existing docstring', self.options)
                            comment_verbose(f'existing docstring: {current_docstring}', self.options)
                            new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_name, function_code, current_docstring, self.options)
                            body_statements = list(updated_node.body.body)
                            if isinstance(body_statements[0], libcst.SimpleStatementLine) and isinstance(body_statements[0].body[0], libcst.Expr):
                                if isinstance(body_statements[0].body[0].value, libcst.SimpleString):
                                    body_statements[0] = libcst.SimpleStatementLine([libcst.Expr(libcst.SimpleString(f'"""{new_docstring}"""'))])
                                    action_taken = "updated existing docstring"
                                    comment_verbose(f'new docstring: {new_docstring}', self.options)
                            updated_body = libcst.IndentedBlock(body=body_statements)
                            updated_node = updated_node.with_changes(body=updated_body)
                    else:
                        if self.options.create:
                            # Append new docstring
                            comment_brief('Creating a new docstring', self.options)
                            new_docstring = queries.generate_docstring(self.docstring_service.ollama, function_name, function_code, current_docstring, self.options)
                            if new_docstring is not None:
                                body_statements = [libcst.SimpleStatementLine([libcst.Expr(libcst.SimpleString(f'"""{new_docstring}"""'))])] + list(updated_node.body.body)
                                updated_body = libcst.IndentedBlock(body=body_statements)
                                updated_node = updated_node.with_changes(body=updated_body)
                                comment_verbose(f'new docstring: {new_docstring}', self.options)
                                action_taken = "created a new docstring"
                            else:
                                action_taken = "failed to create new docstring, leaving as-is"

            self.function_level -= 1
            report = f"{function_name}: {action_taken}"
            comment_brief(report, self.options)
            self.reports.append(report)
            self.function_path.pop()
            return updated_node

    def __init__(self, options):
        self.ollama = OllamaService()
        self.options = options

    def document_file(self, file_path, paths_of_interest):
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = libcst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree, paths_of_interest)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports
