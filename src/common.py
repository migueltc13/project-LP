from typing import Optional, Tuple
import sys


def read_input(input_file: Optional[str] = None) -> Tuple[str, str]:
    """
    Reads the input data from a file or standard input.

    Args:
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
