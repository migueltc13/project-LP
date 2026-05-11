from error import print_label_diagnostic


def check_labels(parser):
    """
    Check labels collected during parsing.

    Reports:
        - errors for redefined labels
        - errors for referenced labels that were never defined
        - warnings for defined labels that were never referenced
    """

    redefined = sorted(parser.redefined_labels)
    undefined = sorted(parser.referenced_labels - parser.defined_labels)
    unused = sorted(parser.defined_labels - parser.referenced_labels)

    for label in redefined:
        locations = parser.label_definition_locations.get(label, [])

        # First definition is allowed. Later definitions are errors.
        for location in locations[1:]:
            print_label_diagnostic(
                parser,
                message=f"label {label} redefined",
                location=location,
            )

        parser.has_error = True

    for label in undefined:
        locations = parser.label_reference_locations.get(label, [])

        for location in locations:
            print_label_diagnostic(
                parser,
                message=f"label {label} referenced but not defined",
                location=location,
            )

        parser.has_error = True

    for label in unused:
        locations = parser.label_definition_locations.get(label, [])

        for location in locations:
            print_label_diagnostic(
                parser,
                message=f"label {label} defined but never referenced",
                location=location,
                warning=True,
            )


def _get_token_column(parser, token) -> int:
    """
    Return the 1-based column number of a token.
    """

    if token is None:
        return 1

    lexpos = token.lexpos
    lexer_data = token.lexer.lexdata

    line_start = lexer_data.rfind("\n", 0, lexpos) + 1

    return lexpos - line_start + 1


def record_label_definition(parser, label: int, lineno: int, col_start: int):
    """
    Record a statement label definition.
    """

    if label in parser.defined_labels:
        parser.redefined_labels.add(label)

    parser.defined_labels.add(label)

    location = {
        "lineno": lineno,
        "col_start": col_start + len("@LABEL("),  # account for prefix
        "length": len(str(label)),
    }

    parser.label_definition_locations.setdefault(label, []).append(location)


def record_label_reference(parser, label: int, lineno: int, col_start: int):
    """
    Record a statement label reference.
    """

    parser.referenced_labels.add(label)

    location = {
        "lineno": lineno,
        "col_start": col_start + len("@LABEL("),  # account for prefix
        "length": len(str(label)),
    }

    parser.label_reference_locations.setdefault(label, []).append(location)
