from .constant_folding import constant_folding
from .expression_simplification import expression_simplification
from .dead_code import dead_code_elimination
from .vectorization import vectorization

from abstract_syntax_tree import AST


def optimizations(ast: AST) -> AST:
    """
    Run AST-level optimization passes.

    Optimizations include:
        1. constant folding
        2. expression simplification
        3. dead code elimination
        4. vectorization
    """

    ast = constant_folding(ast)
    ast = expression_simplification(ast)
    ast = dead_code_elimination(ast)
    ast = vectorization(ast)

    return ast
