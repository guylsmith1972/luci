python_specification = {
    "class_definition": ["class", ["identifier"]],
    "function_definition": ["function", ["identifier"]]
}


cpp_specification = {
    "class_specifier": ["class", ["type_identifier"]],
    "function_definition": ["function", [lambda nt: nt=="function_declarator" or nt=="parenthesized_declarator", lambda nt: nt == "field_identifier" or nt == "identifier"]]
}


language_specifications = {
    "c": cpp_specification,
    "cpp": cpp_specification,
    "python": python_specification
}
