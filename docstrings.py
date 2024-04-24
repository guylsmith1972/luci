from tkinter import CURRENT
from ollama import OllamaService
import libcst
import queries


def comment_brief(str, options):
    if options.log_level > 0:
        print(str)
                
def comment_verbose(str, options):
    if options.log_level > 1:
        print(str)


class DocstringService:
    class DocstringUpdater(libcst.CSTTransformer):
        def __init__(self, docstring_service, default_indent):
            self.class_level = 0
            self.function_level = 0
            self.default_indent = default_indent
            self.docstring_service = docstring_service
            self.options = docstring_service.options
            self.reports = []
            
        def convert_functiondef_to_string(self, function_def):
            code = libcst.Module([])
            code.body.append(function_def)
            return code.code
            
        def visit_ClassDef(self, node):
            comment_brief(f"Examining class: {node.name.value}", self.options)
            self.class_level += 1

        def leave_ClassDef(self, original_node, updated_node):
            self.class_level -= 1
            return updated_node

        def visit_FunctionDef(self, node):
            self.function_level += 1
            comment_brief(f"Examining function: {node.name.value}", self.options)
            
        def leave_FunctionDef(self, original_node, updated_node):
            action_taken = "did nothing"

            function_name = updated_node.name.value

            if self.function_level > self.options.depth or self.class_level > self.options.depth:
                action_taken = f'skipped due to high nesting level -- function_level: {self.function_level}, class_level: {self.class_level}'
            else:
                current_docstring = updated_node.get_docstring()
                function_code = self.convert_functiondef_to_string(updated_node)
                            
                if current_docstring is not None:
                    do_update = self.options.update
                    if self.options.validate:
                        comment_brief('Validating existing docstring', self.options)
                        validated, assessment = self.docstring_service.validate_docstring(function_name, function_code, f'"""{current_docstring}"""')
                        if validated:
                            do_update = False
                        report = f'Validation report for {function_name}: {"PASS" if validated else "FAILED"}: {assessment}'
                        self.reports.append(report)
                    if do_update:
                        # Replace existing docstring
                        comment_brief('Replacing existing docstring', self.options)
                        comment_verbose(f'existing docstring: {current_docstring}', self.options)
                        new_docstring = self.docstring_service.generate_docstring(function_name, function_code, current_docstring)
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
                        new_docstring = self.docstring_service.generate_docstring(function_name, function_code, current_docstring)
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
            return updated_node

    def __init__(self, options):
        self.ollama = OllamaService()
        
        with open('samples/example_docstring.txt', 'r') as infile:
            self.example_docstring = infile.read()
        with open('samples/example_function.txt', 'r') as infile:
            self.example_function = infile.read()
            
        self.options = options

    def document_file(self, file_path):
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = libcst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree)
        modified_tree = tree.visit(transformer)
        return modified_tree.code, transformer.reports

    def generate_docstring(self, function_name, function_body, current_docstring):
        query = queries.generate_docstring_query(function_body, self.example_function, self.example_docstring)
        print(query)
        for i in range(self.options.attempts):
            docstring = self.ollama.query(query)
            if self.validate_docstring(function_name, function_body, docstring):
                return docstring.strip('"').strip("'")
        return None
    
    def validate_docstring(self, function_name, function_body, docstring):
        report = None
        if not docstring.startswith('"""') or not docstring.endswith('"""') or '"""' in docstring[3:-3]:
            report = f'Failed simple string test (incorrect quoting): {docstring}'
        else:
            query = queries.generate_validation_query(function_body, docstring, self.example_docstring)
            for i in range(self.options.attempts):
                result = self.ollama.query(query)
                if result.strip().lower().startswith('correct'):
                    return True, result
                else:
                    report = result
                    
        return False, report
