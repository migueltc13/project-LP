from semantic_checks.type_checker import SemanticError

###
# Label Checker
# Semantic checks for labels, including:
# - Label redefinition
# - Use of undefined labels
# - DO loop label matching with CONTINUE statements
###


# Main entry point for label validation. Traverses the AST to collect defined
# and referenced labels, then checks for any undefined labels and raises errors
# as needed.
def validate_labels(ast):
    defined_labels = set()
    referenced_labels = set()
    _visit(ast, defined_labels, referenced_labels)

    undefined_labels = sorted(referenced_labels - defined_labels)
    if undefined_labels:
        joined = ", ".join(str(label) for label in undefined_labels)
        raise SemanticError(f"Undefined label(s): {joined}")

    return ast

# Recursive AST visitor to collect defined and referenced labels.
# Handles label definitions, GOTO statements, and DO loops with CONTINUE labels.
def _visit(node, defined_labels, referenced_labels):
    if node is None:
        return

    if isinstance(node, list):
        for item in node:
            _visit(item, defined_labels, referenced_labels)
        return

    if not isinstance(node, tuple) or not node:
        return

    node_type = node[0]

    if node_type == "label":
        label = node[1]
        if label in defined_labels:
            raise SemanticError(f"Label {label} redefined")
        defined_labels.add(label)
        _visit(node[2], defined_labels, referenced_labels)
        return

    if node_type == "goto":
        referenced_labels.add(node[1])
        return

    if node_type == "do":
        do_label = node[1]
        continue_label = node[6]
        if do_label != continue_label:
            raise SemanticError(
                f"DO loop label {do_label} does not match CONTINUE label {continue_label}"
            )
        if continue_label in defined_labels:
            raise SemanticError(f"Label {continue_label} redefined")
        defined_labels.add(continue_label)
        _visit(node[5], defined_labels, referenced_labels)
        return

    for child in node[1:]:
        if isinstance(child, (list, tuple)):
            _visit(child, defined_labels, referenced_labels)
