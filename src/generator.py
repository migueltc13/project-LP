#!/usr/bin/env python3


def main():
    """
    Main function to compile Fortran 77 source code into EWVM assembly language.
    """

    import argparse
    import sys
    from pathlib import Path

    from common import read_input, detect_source_format, open_file  # , write_output
    from preprocessor import preprocess
    from lexer import lexer, clear_lexer_state
    from parser import parser, clear_parser_state
    from semantics import semantic_checks
    from semantics.semantic_info import print_semantic_info
    from optimizations import optimizations
    from abstract_syntax_tree import (
        pretty_print,
        visualize,
        DEFAULT_VIS_OUTPUT_PATH
    )

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Compile Fortran 77 source code into EWVM assembly language."
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file to compile. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "--output", "-o",
        metavar="OUTPUT",
        help="Output file for the generated EWVM assembly code. "
             "If omitted, output to stdout."
    )

    parser_args.add_argument(
        "--optimize", "-O",
        action="store_true",
        default=False,
        help="Enable optimizations in the generated assembly code."
    )

    parser_args.add_argument(
        "--debug", "-g",
        action="store_true",
        default=False,
        help="Enable debug comments in the generated assembly code."
    )

    parser_args.add_argument(
        "--format",
        choices=["fixed", "free"],
        default=None,
        help="The source format. If omitted, inferred from file extension; "
             "stdin defaults to fixed."
    )

    parser_args.add_argument(
        "--no-preprocess",
        action="store_true",
        default=False,
        help="Skip preprocessing and parse the raw input directly",
    )

    parser_args.add_argument(
        "--visualize", "--vis",
        nargs="?",
        const=DEFAULT_VIS_OUTPUT_PATH,
        metavar="OUTPUT",
        help="Generate a Graphviz image of the AST "
             f"(default output: {DEFAULT_VIS_OUTPUT_PATH})"
    )

    parser_args.add_argument(
        "--show-intrinsics",
        action="store_true",
        default=False,
        help="Include intrinsic procedures in verbose semantic information output",
    )

    parser_args.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose output during compilation"
             "(e.g. print intermediate ASTs, semantic info, etc.)"
    )

    args = parser_args.parse_args()

    # Read input data
    try:
        source_filename, source_data = read_input(args.input_file)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Detect source format based on file extension
    source_format = detect_source_format(args.input_file, args.format)

    # Pre-process the input data
    if not args.no_preprocess:
        try:
            source_data = preprocess(source_data, format=source_format)
        except Exception as e:
            print(f"Preprocessing error: {e}", file=sys.stderr)
            sys.exit(1)

    # Set up lexer and parser state
    clear_lexer_state(lexer)
    clear_parser_state(parser)

    source_lines = source_data.splitlines()

    lexer.source_lines = source_lines
    lexer.source_filename = source_filename

    parser.source_lines = source_lines
    parser.source_filename = source_filename

    # Parse the input data
    result = parser.parse(source_data, lexer=lexer, debug=False)

    # Propagate lexer errors to parser error state,
    # since the lexer doesn't exit on error
    if lexer.has_error:
        parser.has_error = True

    if result is None:
        sys.exit(1)

    # Semantic checks
    semantic_info = semantic_checks(parser, ast=result)

    # Check for semantic errors before proceeding to optimizations and code generation
    if parser.has_error:
        sys.exit(1)

    # Verbose output of semantic information and initial AST
    if args.verbose:
        print()
        print_semantic_info(semantic_info, show_intrinsics=args.show_intrinsics)

        print()
        pretty_print(result)

    # Visualize initial AST
    if args.visualize:
        try:
            visualize_file = visualize(result, output_path=args.visualize)
            print(f"\nAST visualization generated at: {visualize_file}")
            open_file(visualize_file)
        except Exception as e:
            print(f"AST Visualization error: {e}", file=sys.stderr)

    # TODO optimizations here (e.g. constant folding, dead code elimination, etc.)
    if args.optimize:
        # TODO Check if optimizations can use (and enjoy) semantic_info
        result = optimizations(result)
        # TODO perhaps code optimization will also need to propagate changes
        # to semantic_info in this case we could re-run:
        # semantic_info = semantic_checks(parser, ast=result)
        # NOTE this can be a bit expensive so we have to check of it's worth it
        # But ensure new code generation receives the updated semantic_info for
        # memory allocation, etc.
        # Alternatively we could have optimizations return both the optimized
        # AST and updated semantic_info.

        # Verbose output of optimized AST
        if args.verbose:
            print("\nOptimized AST:")
            pretty_print(result)

        # Visualize optimized AST
        if args.visualize:
            try:
                vis_path = Path(args.visualize)
                output_path = str(vis_path.with_name(f"{vis_path.stem}_optimized{vis_path.suffix}"))
                optimized_vis_file = visualize(result, output_path=output_path)
                print(f"\nOptimized AST visualization generated at: {optimized_vis_file}")
                open_file(optimized_vis_file)
            except Exception as e:
                print(f"Optimized AST Visualization error: {e}", file=sys.stderr)

    # TODO code generation logic here (add try-catch if needed)
    # assembly = generate(result, semantic_info, debug=args.debug)

    # TODO Write output assembly code to file or stdout
    try:
        # write_output(args.output, assembly)
        pass
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
