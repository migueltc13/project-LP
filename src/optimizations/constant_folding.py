from abstract_syntax_tree import AST


def constant_folding(ast: AST) -> AST:
    """
    Fold compile-time constant expressions.

    Examples:
        2 + 3        -> 5
        4 * 10       -> 40
        .TRUE. .AND. .FALSE. -> .FALSE.

    Currently a no-op placeholder.
    """

    return ast
