from __future__ import annotations

from dataclasses import replace

import abstract_syntax_tree as ast
from abstract_syntax_tree import AST


def expression_simplification(tree: AST) -> AST:
    """
    Simplify algebraic and logical expressions.

    This pass is especially effective after constant folding.

    Examples:
        X + 0              -> X
        0 + X              -> X
        X - 0              -> X
        X * 1              -> X
        1 * X              -> X
        X * 0              -> 0, when X is side-effect-free
        0 * X              -> 0, when X is side-effect-free
        X / 1              -> X
        X ** 1             -> X
        X ** 0             -> 1, when X is side-effect-free
        .TRUE. .AND. X     -> X
        X .AND. .TRUE.     -> X
        .FALSE. .AND. X    -> .FALSE., when X is side-effect-free
        X .AND. .FALSE.    -> .FALSE., when X is side-effect-free
        .FALSE. .OR. X     -> X
        X .OR. .FALSE.     -> X
        .TRUE. .OR. X      -> .TRUE., when X is side-effect-free
        X .OR. .TRUE.      -> .TRUE., when X is side-effect-free
        .NOT. (.NOT. X)    -> X
        +X                 -> X

    Notes:
        - This pass assumes constant_folding() already ran before it.
        - It avoids removing expressions containing function calls.
        - It preserves AST immutability by using dataclasses.replace().
    """

    simplifier = ExpressionSimplifier()
    return simplifier.visit(tree)


class ExpressionSimplifier:
    def visit(self, node):
        if node is None:
            return None

        if isinstance(node, list):
            return [self.visit(item) for item in node]

        if isinstance(node, ast.File):
            return replace(
                node,
                program_units=[
                    self.visit(unit)
                    for unit in node.program_units
                ],
            )

        if isinstance(node, ast.Program):
            return replace(
                node,
                statements=self.visit(node.statements),
            )

        if isinstance(node, ast.Subroutine):
            return replace(
                node,
                statements=self.visit(node.statements),
            )

        if isinstance(node, ast.Function):
            return replace(
                node,
                statements=self.visit(node.statements),
            )

        if isinstance(node, ast.Block):
            return replace(
                node,
                statements=self.visit(node.statements),
            )

        if isinstance(node, ast.Declare):
            return replace(
                node,
                declarators=[
                    self.visit_declarator(declarator)
                    for declarator in node.declarators
                ],
            )

        if isinstance(node, ast.Assign):
            return replace(
                node,
                target=self.visit_variable(node.target),
                value=self.visit_expression(node.value),
            )

        if isinstance(node, ast.Print):
            return replace(
                node,
                items=[
                    self.visit_expression(item)
                    for item in node.items
                ],
            )

        if isinstance(node, ast.Write):
            return replace(
                node,
                items=[
                    self.visit_expression(item)
                    for item in node.items
                ],
            )

        if isinstance(node, ast.Read):
            return replace(
                node,
                variables=[
                    self.visit_variable(variable)
                    for variable in node.variables
                ],
            )

        if isinstance(node, ast.Label):
            return replace(
                node,
                statement=self.visit(node.statement),
            )

        if isinstance(node, ast.If):
            return replace(
                node,
                condition=self.visit_expression(node.condition),
                then_branch=self.visit(node.then_branch),
                else_branch=(
                    self.visit(node.else_branch)
                    if node.else_branch is not None
                    else None
                ),
            )

        if isinstance(node, ast.Do):
            return replace(
                node,
                variable=node.variable,
                start=self.visit_expression(node.start),
                end=self.visit_expression(node.end),
                step=(
                    self.visit_expression(node.step)
                    if node.step is not None
                    else None
                ),
            )

        if isinstance(node, ast.CallStatement):
            return replace(
                node,
                arguments=[
                    self.visit_expression(argument)
                    for argument in node.arguments
                ],
            )

        if isinstance(node, (
            ast.Goto,
            ast.Stop,
            ast.Return,
            ast.Continue,
        )):
            return node

        raise RuntimeError(
            f"unsupported AST node in expression simplification: {node!r}"
        )

    def visit_declarator(self, node):
        if isinstance(node, ast.VarDeclarator):
            return node

        if isinstance(node, ast.ArrayDeclarator):
            return replace(
                node,
                dimensions=[
                    self.visit_expression(dimension)
                    for dimension in node.dimensions
                ],
            )

        raise RuntimeError(
            f"unsupported declarator in expression simplification: {node!r}"
        )

    def visit_variable(self, node):
        if isinstance(node, ast.Var):
            return node

        if isinstance(node, ast.ArrayRef):
            return replace(
                node,
                indices=[
                    self.visit_expression(index)
                    for index in node.indices
                ],
            )

        raise RuntimeError(
            f"unsupported variable in expression simplification: {node!r}"
        )

    def visit_expression(self, node):
        if isinstance(node, (
            ast.Integer,
            ast.Real,
            ast.Double,
            ast.String,
            ast.Bool,
            ast.Var,
        )):
            return node

        if isinstance(node, ast.ArrayRef):
            return replace(
                node,
                indices=[
                    self.visit_expression(index)
                    for index in node.indices
                ],
            )

        if isinstance(node, ast.Call):
            return replace(
                node,
                arguments=[
                    self.visit_expression(argument)
                    for argument in node.arguments
                ],
            )

        if isinstance(node, ast.IndexedOrCall):
            return replace(
                node,
                arguments=[
                    self.visit_expression(argument)
                    for argument in node.arguments
                ],
            )

        if isinstance(node, ast.Unary):
            value = self.visit_expression(node.value)
            simplified = replace(node, value=value)
            return self.simplify_unary(simplified)

        if isinstance(node, ast.Arith):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            simplified = replace(node, left=left, right=right)
            return self.simplify_arith(simplified)

        if isinstance(node, ast.Rel):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            return replace(node, left=left, right=right)

        if isinstance(node, ast.Logical):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            simplified = replace(node, left=left, right=right)
            return self.simplify_logical(simplified)

        raise RuntimeError(
            f"unsupported expression in expression simplification: {node!r}"
        )

    ###
    # Literal helpers
    ###

    def is_integer_zero(self, node) -> bool:
        return isinstance(node, ast.Integer) and node.value == 0

    def is_integer_one(self, node) -> bool:
        return isinstance(node, ast.Integer) and node.value == 1

    def is_numeric_zero(self, node) -> bool:
        return (
            isinstance(node, (ast.Integer, ast.Real, ast.Double))
            and node.value == 0
        )

    def is_numeric_one(self, node) -> bool:
        return (
            isinstance(node, (ast.Integer, ast.Real, ast.Double))
            and node.value == 1
        )

    def zero_like(self, node, location):
        if isinstance(node, ast.Double):
            return ast.Double(0.0, location)

        if isinstance(node, ast.Real):
            return ast.Real(0.0, location)

        return ast.Integer(0, location)

    def one_like(self, node, location):
        if isinstance(node, ast.Double):
            return ast.Double(1.0, location)

        if isinstance(node, ast.Real):
            return ast.Real(1.0, location)

        return ast.Integer(1, location)

    ###
    # Safety helpers
    ###

    def is_side_effect_free(self, node) -> bool:
        """
        Return True if removing this expression should not remove procedure
        calls or other potentially meaningful runtime behavior.

        This compiler currently treats function calls as potentially effectful.
        """

        if isinstance(node, (
            ast.Integer,
            ast.Real,
            ast.Double,
            ast.String,
            ast.Bool,
            ast.Var,
        )):
            return True

        if isinstance(node, ast.ArrayRef):
            return all(
                self.is_side_effect_free(index)
                for index in node.indices
            )

        if isinstance(node, ast.Unary):
            return self.is_side_effect_free(node.value)

        if isinstance(node, ast.Arith):
            return (
                self.is_side_effect_free(node.left)
                and self.is_side_effect_free(node.right)
            )

        if isinstance(node, ast.Rel):
            return (
                self.is_side_effect_free(node.left)
                and self.is_side_effect_free(node.right)
            )

        if isinstance(node, ast.Logical):
            return (
                self.is_side_effect_free(node.left)
                and self.is_side_effect_free(node.right)
            )

        if isinstance(node, ast.Call):
            return False

        if isinstance(node, ast.IndexedOrCall):
            return False

        return False

    ###
    # Simplification rules
    ###

    def simplify_unary(self, node: ast.Unary):
        value = node.value

        if node.op == "+":
            return value

        if node.op in {".NOT.", "NOT"}:
            if isinstance(value, ast.Unary) and value.op in {".NOT.", "NOT"}:
                return value.value

        return node

    def simplify_arith(self, node: ast.Arith):
        left = node.left
        right = node.right

        if node.op == "+":
            if self.is_numeric_zero(right):
                return left

            if self.is_numeric_zero(left):
                return right

            return node

        if node.op == "-":
            if self.is_numeric_zero(right):
                return left

            return node

        if node.op == "*":
            if self.is_numeric_one(right):
                return left

            if self.is_numeric_one(left):
                return right

            if self.is_numeric_zero(right) and self.is_side_effect_free(left):
                return self.zero_like(right, node.location)

            if self.is_numeric_zero(left) and self.is_side_effect_free(right):
                return self.zero_like(left, node.location)

            return node

        if node.op == "/":
            if self.is_numeric_one(right):
                return left

            return node

        if node.op == "**":
            if self.is_numeric_one(right):
                return left

            if self.is_numeric_zero(right) and self.is_side_effect_free(left):
                return self.one_like(left, node.location)

            return node

        return node

    def simplify_logical(self, node: ast.Logical):
        left = node.left
        right = node.right

        if node.op == ".AND.":
            if isinstance(left, ast.Bool):
                if left.value:
                    return right

                if self.is_side_effect_free(right):
                    return ast.Bool(False, node.location)

                return node

            if isinstance(right, ast.Bool):
                if right.value:
                    return left

                if self.is_side_effect_free(left):
                    return ast.Bool(False, node.location)

                return node

            return node

        if node.op == ".OR.":
            if isinstance(left, ast.Bool):
                if not left.value:
                    return right

                if self.is_side_effect_free(right):
                    return ast.Bool(True, node.location)

                return node

            if isinstance(right, ast.Bool):
                if not right.value:
                    return left

                if self.is_side_effect_free(left):
                    return ast.Bool(True, node.location)

                return node

            return node

        return node
