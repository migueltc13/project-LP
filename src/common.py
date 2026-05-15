import sys
from pathlib import Path
from typing import Optional, Tuple


def detect_source_format(input_file: Optional[str],
                         explicit_format: Optional[str]) -> str:
    """
    Determine source format from an explicit CLI value or file extension.

    Priority:
        1. Explicit --format flag value
        2. File extension
        3. Fixed format fallback

    Note: Alternatively, we could detect format by analyzing the content of the
          file.

    Arguments:
        input_file (Optional[str]): The path to the input file.
        explicit_format (Optional[str]): The explicitly provided format
                                         ("fixed" or "free").

    Returns:
        str: The detected source format ("fixed" or "free").
    """

    if explicit_format is not None:
        return explicit_format

    if input_file is None:
        return "fixed"

    suffix = Path(input_file).suffix.lower()

    if suffix in {".f", ".for", ".ftn"}:
        return "fixed"

    if suffix in {".f90", ".f95", ".f03", ".f08"}:
        return "free"

    return "fixed"


def read_input(input_file: Optional[str] = None) -> Tuple[str, str]:
    """
    Reads the input data from a file or standard input.

    Arguments:
        input_file(Optional[str]): The path to the input file.
                                   If None, reads from standard input.

    Returns:
        Tuple[str, str]: A tuple containing the source filename and the source
                        data.

    Raises:
        OSError: If there is an error accessing the file.
        IOError: If there is an error reading the file.
    """
    if input_file is None:
        return "<stdin>", sys.stdin.read()

    with open(input_file, "r", encoding="utf-8") as file:
        return input_file, file.read()


def open_file(path: str) -> None:
    """
    Open a generated file using the operating system's default application.

    Arguments:
        path(str): The file path to open.
    """

    import os
    import platform
    import subprocess

    system = platform.system()

    if system == "Darwin":
        subprocess.run(["open", path], check=False)
    elif system == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", path], check=False)


def visualize_ast(
    ast,
    *,
    output_path: str,
    optimized: bool = False,
) -> None:
    """
    Generate and open an AST visualization.

    If optimized=True, write to a sibling file with '_optimized' appended to
    the original output filename stem.

    Examples:
        /tmp/ast.png              -> /tmp/ast.png
        /tmp/ast.png optimized    -> /tmp/ast_optimized.png
    """

    from abstract_syntax_tree import visualize

    try:
        final_output_path = output_path

        if optimized:
            vis_path = Path(output_path)
            final_output_path = str(
                vis_path.with_name(
                    f"{vis_path.stem}_optimized{vis_path.suffix}"
                )
            )

        visualize_file = visualize(ast, output_path=final_output_path)

        if optimized:
            print(
                "\nOptimized AST visualization generated at: "
                f"{visualize_file}"
            )
        else:
            print(f"\nAST visualization generated at: {visualize_file}")

        open_file(visualize_file)

    except Exception as e:
        if optimized:
            print(f"Optimized AST Visualization error: {e}", file=sys.stderr)
        else:
            print(f"AST Visualization error: {e}", file=sys.stderr)


def write_output(
    output_path: Optional[str],
    data: str,
    verbose: bool = False
) -> None:
    """
    Writes the given data to a file or standard output.

    Arguments:
        output_path (Optional[str]): The path to the output file. If None,
                                     writes to standard output.
        data (str): The data to write.
        verbose (bool): Prints header message when writing to standard output,
                        or prints output path when writing to a file, when
                        True.

    Raises:
        OSError: If there is an error accessing the file.
        IOError: If there is an error writing to the file.
    """

    if output_path is None:
        if verbose:
            print("\nEWVM Assembly:\n==============\n")
        sys.stdout.write(data)
    else:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(data)
        if verbose:
            print(f"EWVM Assembly written to: {output_path}")
