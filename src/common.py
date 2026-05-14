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


def write_output(output_path: Optional[str], data: str) -> None:
    """
    Writes the given data to a file or standard output.

    Arguments:
        output_path (Optional[str]): The path to the output file. If None,
                                     writes to standard output.
        data (str): The data to write.

    Raises:
        OSError: If there is an error accessing the file.
        IOError: If there is an error writing to the file.
    """

    if output_path is None:
        sys.stdout.write(data)
    else:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(data)
