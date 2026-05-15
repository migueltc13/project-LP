from .constant_folding import constant_folding
from .expression_simplification import expression_simplification
from .dead_code import dead_code_elimination
from .loop_unrolling import loop_unrolling

from abstract_syntax_tree import AST


def optimizations(ast: AST) -> AST:
    """
    Run AST-level optimization passes.

    Pass order matters:
        1. constant folding
        2. expression simplification
        3. dead code elimination
        4. loop unrolling

    Later, some passes may be repeated because one optimization can expose
    new opportunities for another one.
    """

    ast = constant_folding(ast)
    ast = expression_simplification(ast)
    ast = dead_code_elimination(ast)
    ast = loop_unrolling(ast)

    return ast
