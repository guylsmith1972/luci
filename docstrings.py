import os
from tkinter import CURRENT
from ollama import OllamaService
import libcst


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
            self.options = docstring_service.get_options()
            
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

            if self.function_level > self.options.depth or self.class_level > self.options.depth:
                action_taken = f'skipped due to high nesting level -- function_level: {self.function_level}, class_level: {self.class_level}'
            else:
                current_docstring = updated_node.get_docstring()
                
                function_code = self.convert_functiondef_to_string(updated_node)
                            
                if current_docstring is not None:
                    if self.options.update:
                        # Replace existing docstring
                        comment_brief('Replacing existing docstring', self.options)
                        comment_verbose(f'existing docstring: {current_docstring}', self.options)
                        new_docstring = self.docstring_service.generate_docstring(updated_node.name.value, function_code, current_docstring)
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
                        new_docstring = self.docstring_service.generate_docstring(updated_node.name.value, function_code, current_docstring)
                        if new_docstring is not None:
                            body_statements = [libcst.SimpleStatementLine([libcst.Expr(libcst.SimpleString(f'"""{new_docstring}"""'))])] + list(updated_node.body.body)
                            updated_body = libcst.IndentedBlock(body=body_statements)
                            updated_node = updated_node.with_changes(body=updated_body)
                            comment_verbose(f'new docstring: {new_docstring}', self.options)
                            action_taken = "created a new docstring"
                        else:
                            action_taken = "failed to create new docstring, leaving as-is"

            self.function_level -= 1
            comment_brief(f"Action taken: {updated_node.name.value} - {action_taken}", self.options)
            return updated_node

    def __init__(self, options):
        self.ollama = OllamaService()
        
        def load_query(filename):
            """ Load a query from a file in the 'queries' directory. """
            with open(os.path.join('queries', filename)) as infile:
                query = infile.read()
            return query

        self.generate_docstring_template = load_query('generate_docstring_template.txt')
        self.check_docstring_template = load_query('check_docstring_template.txt')
        self.options = options

    def document_file(self, file_path):
        with open(file_path, "r") as source_file:
            source_code = source_file.read()

        tree = libcst.parse_module(source_code)
        transformer = DocstringService.DocstringUpdater(self, tree)
        modified_tree = tree.visit(transformer)
        return modified_tree.code

    def generate_docstring(self, function_name, function_body, current_docstring):
        query = self.generate_docstring_template + f"""{function_body}

            Please write a detailed doc string for the above python function named {function_name}.
            If there is already a docstring, make any necessary corrections to the string.
            Respond with only the text of the docstring.
            """
        comment_verbose(query, self.options)
        for i in range(self.options.attempts):
            docstring = self.ollama.query(query)
            if self.validate_docstring(function_name, function_body, docstring):
                return docstring.strip('"').strip("'")
        return None
    
    def get_options(self):
        return self.options

    def validate_docstring(self, function_name, function_body, docstring):
        if docstring.startswith('"""') and docstring.endswith('"""'):
            if '"""' not in docstring[3:-3]:
                query = self.check_docstring_template + f"""{function_body}

                Please check if the docstring that follows correctly describes the above Python function named {function_name}.
                If the docstring is correct, respond with only the word "correct".
                If the docstring is incorrect, response with only the word "incorrect" followed by a colon and explanation.

                docstring: {docstring}
                """
                for i in range(self.options.attempts):
                    result = self.ollama.query(query)
                    if result.strip().lower().startswith('correct'):
                        return True
                    else:
                        pass
        return False
