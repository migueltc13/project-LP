#!/usr/bin/env python3

DESCRIPTIONS = {
    "invalid_character.f":
        "Tests the presence of an invalid character.",

    "invalid_character_sequence.f":
        "Tests invalid character sequences.",

    "invalid_label.f":
        "Tests invalid label formats.",

    "line_too_long.f":
        "Tests lines that exceed the maximum length for\n"
        "fixed-format source files.",

    "orphaned_continuation.f":
        "Tests orphaned continuation lines.",

    "unterminated_string.f":
        "Tests string literals that are not properly terminated.",

    "duplicate_procedures.f":
        "Tests multiple subroutines with the same name in\n"
        "the same file.",

    "function_used_as_subroutine.f":
        "Tests a function being called without using its\n"
        "return value, like a subroutine call.",

    "subroutine_used_as_function.f":
        "Tests a subroutine being called in an expression,\n"
        "like a function call.",

    "unknown_function.f":
        "Tests a call to an undefined function.",

    "unknown_subroutine.f":
        "Tests a call to an undefined subroutine.",

    "wrong_nr_function_args.f":
        "Tests a function call with the wrong number of\n"
        "arguments.",

    "wrong_nr_subroutine_args.f":
        "Tests a subroutine call with the wrong number of\n"
        "arguments.",

    "labels.f":
        "Tests various label-related errors, like:\n"
        "   - Undefined labels;\n"
        "   - Redefined labels;\n"
        "   - Labels referenced but not defined;\n"
        "   - Labels defined but never referenced;\n"
        "   - DO loop labels that do not match the corresponding\n"
        "     CONTINUE statement.",

    "multiple_program.f":
        "Tests multiple main program units defined in the same\n"
        "source file.",

    "return_outside.f":
        "Tests a RETURN statement outside of any function or \n"
        "subroutine context.",

    "variables.f":
        "Tests many variable-related errors, like:\n"
        "   - Use of undeclared variables;\n"
        "   - Variables already declared;\n"
        "   - Variables used before initialization;\n"
        "   - Assignment to undeclared variables;\n"
        "   - Variables declared but never used.",

    "bad_if_syntax.f":
        "Tests invalid syntax in IF statements, like missing THEN\n"
        "or END IF.",

    "bad_read_syntax.f":
        "Tests invalid syntax in READ statements, like missing a\n"
        "comma.",

    "missing_do_lbl.f":
        "Tests a DO statement without a missing numeric label.",

    "missing_end.f":
        "Tests a program with a missing END statement.",

    "misspelled_function.f":
        "Tests a misspelled function name in a function call.",

    "arith_with_string.f":
        "Tests an arithmetic operation involving a string\n"
        "literal.",

    "if_cond_non_logical.f":
        "Tests an IF statement with a non-logical condition.",

    "invalid_narrowing.f":
        "Tests an assignment of a REAL literal to an INTEGER\n"
        "variable.",

    "logical_expr_mismatch.f":
        "Tests a logical expression with incompatible operand\n"
        "types.",

    "wrong_assignment_type.f":
        "Tests an assignment with incompatible types (assign\n"
        "a CHARACTER to an INTEGER).",

    "arrays.f":
        "Tests if multidimensional arrays are being used, since\n"
        "they're not supported yet.",

    "dynamic_array_in_procedure.f":
        "Tests if dynamic array dimensions are being used in\n"
        "procedures, since it's not supported yet.",

    "intrinsic_function.f":
        "Tests the use of intrinsic functions, since they're not\n"
        "supported yet.",

    "no_program.f":
        "Tests a source file with no main program unit defined."
}