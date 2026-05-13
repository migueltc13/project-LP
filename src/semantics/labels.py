from error import print_label_diagnostic

PREPROCESSED_LABEL_PREFIX_LEN = len("@LABEL(")


def check_labels(parser):
    """
    Check labels collected during parsing.

    Reports:
        - errors for redefined labels
        - errors for referenced labels that were never defined
        - warnings for defined labels that were never referenced

    Arguments:
        parser: The parser object containing label information.
    """

    diagnostics = []

    redefined = parser.redefined_labels
    undefined = parser.referenced_labels - parser.defined_labels
    unused = parser.defined_labels - parser.referenced_labels

    for label in redefined:
        locations = parser.label_definition_locations.get(label, [])

        # First definition is allowed. Later definitions are errors.
        for location in locations[1:]:
            diagnostics.append({
                "label": label,
                "message": f"label {label} redefined",
                "location": location,
                "warning": False
            })

    for label in undefined:
        locations = parser.label_reference_locations.get(label, [])

        for location in locations:
            diagnostics.append({
                "label": label,
                "message": f"label {label} referenced but not defined",
                "location": location,
                "warning": False
            })

    for label in unused:
        locations = parser.label_definition_locations.get(label, [])

        for location in locations:
            diagnostics.append({
                "label": label,
                "message": f"label {label} defined but never referenced",
                "location": location,
                "warning": True
            })

    diagnostics.sort(
        key=lambda diagnostic: (
            diagnostic["location"]["lineno"],
            diagnostic["location"]["col_start"],
            diagnostic["location"]["length"],
            diagnostic["message"]
        )
    )

    for diagnostic in diagnostics:
        print_label_diagnostic(
            parser,
            message=diagnostic["message"],
            location=diagnostic["location"],
            warning=diagnostic["warning"]
        )

        if not diagnostic["warning"]:
            parser.has_errors = True


def record_label_definition(parser, label: int, lineno: int, col_start: int):
    """
    Record a statement label definition.

    Note: accounts for the "@LABEL(" prefix added by preprocessor when
          calculating the column start of the label itself.
    """

    if label in parser.defined_labels:
        parser.redefined_labels.add(label)

    parser.defined_labels.add(label)

    location = {
        "lineno": lineno,
        "col_start": col_start + PREPROCESSED_LABEL_PREFIX_LEN,
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
        "col_start": col_start,
        "length": len(str(label)),
    }

    parser.label_reference_locations.setdefault(label, []).append(location)
