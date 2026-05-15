from error import record_diagnostic, get_source_line


def check_loops(parser):
    """
    Check flat Fortran 77 DO-loop constraints.

    Checks if each DO target label exists and is a CONTINUE statement.

    Undefined labels are already reported by check_labels().

    Arguments:
        parser: The parser object containing loop and label information.
    """

    continue_labels = {
        location["label"]
        for location in parser.continue_locations
        if location["label"] is not None
    }

    for do_reference in parser.do_references:
        end_label = do_reference["end_label"]

        # Do not duplicate undefined-label errors.
        # check_labels(parser) already reports those.
        if end_label not in parser.defined_labels:
            continue

        if end_label not in continue_labels:
            record_diagnostic(
                parser,
                error=(
                    f"DO loop target label {end_label} "
                    "does not label a CONTINUE statement"
                ),
                line=get_source_line(parser, do_reference["lineno"]),
                lineno=do_reference["lineno"],
                col_start=do_reference["col_start"],
                length=do_reference["length"],
                filename=parser.source_filename
            )
