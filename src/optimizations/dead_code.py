from abstract_syntax_tree import AST


def dead_code_elimination(ast: AST) -> AST:
    """
    Remove unreachable or unused code.

    Planned examples:
        - unreachable statements after STOP / RETURN
        - IF branches with constant conditions
        - unused variables
        - unused functions/subroutines

    Currently a no-op placeholder.
    """

    return ast
