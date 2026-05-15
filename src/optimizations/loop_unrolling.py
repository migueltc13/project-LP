from abstract_syntax_tree import AST


def loop_unrolling(ast: AST) -> AST:
    """
    Unroll simple compile-time bounded DO loops.

    Example:
        DO 100 I = 1, 3
          PRINT *, I
    100 CONTINUE

    may become:
        I = 1
        PRINT *, I
        I = 2
        PRINT *, I
        I = 3
        PRINT *, I

    Currently a no-op placeholder.
    """

    return ast
