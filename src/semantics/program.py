from error import record_diagnostic, get_source_line


def check_program(parser):
    """
    Check top-level program-unit constraints.

    Fortran source files may contain many subroutines/functions, but should not
    contain more than one main PROGRAM unit.

    Arguments:
        parser: The parser object containing program unit information.
    """

    program_locations = parser.program_locations

    if len(program_locations) <= 1:
        return

    first = program_locations[0]

    for location in program_locations[1:]:
        lineno = location["lineno"]

        record_diagnostic(
            parser,
            error=(
                f"multiple main PROGRAM units: {location['name']!r}; "
                f"first PROGRAM is {first['name']!r}"
            ),
            line=get_source_line(parser, lineno),
            lineno=lineno,
            col_start=location["col_start"],
            length=location["length"],
            filename=parser.source_filename,
            hint="keep only one main PROGRAM unit"
        )
