from __future__ import annotations

from dataclasses import replace
from typing import Optional

import abstract_syntax_tree as ast
from abstract_syntax_tree import AST


def constant_folding(tree: AST) -> AST:
    """
    Fold compile-time constant expressions.

    Examples:
        2 + 3                   -> 5
        4 * 10                  -> 40
        .TRUE. .AND. .FALSE.    -> .FALSE.
        1 .LT. 2                -> .TRUE.
        -5                      -> -5

    Notes:
        - Avoids unsafe folds such as division by zero.
        - Preserves source locations by assigning the folded literal the
          original expression location.
        - Does not fold function calls, because calls may have side effects or
          depend on runtime behavior.
    """

    folder = ConstantFolder()
    return folder.visit(tree)


class ConstantFolder:

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

        raise RuntimeError(f"unsupported AST node in constant folding: {node!r}")

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
            f"unsupported declarator in constant folding: {node!r}"
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
            f"unsupported variable in constant folding: {node!r}"
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
            folded = replace(node, value=value)
            return self.fold_unary(folded)

        if isinstance(node, ast.Arith):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            folded = replace(node, left=left, right=right)
            return self.fold_arith(folded)

        if isinstance(node, ast.Rel):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            folded = replace(node, left=left, right=right)
            return self.fold_rel(folded)

        if isinstance(node, ast.Logical):
            left = self.visit_expression(node.left)
            right = self.visit_expression(node.right)
            folded = replace(node, left=left, right=right)
            return self.fold_logical(folded)

        raise RuntimeError(
            f"unsupported expression in constant folding: {node!r}"
        )

    def is_numeric_literal(self, node) -> bool:
        return isinstance(
            node,
            (
                ast.Integer,
                ast.Real,
                ast.Double,
            ),
        )

    def numeric_value(self, node):
        return node.value

    def numeric_result_literal(self, left, right, value, location):
        if isinstance(left, ast.Double) or isinstance(right, ast.Double):
            return ast.Double(float(value), location)

        if isinstance(left, ast.Real) or isinstance(right, ast.Real):
            return ast.Real(float(value), location)

        return ast.Integer(int(value), location)

    def integer_division(self, left: int, right: int) -> Optional[int]:
        if right == 0:
            return None

        # Fortran-style integer division truncates toward zero.
        return int(left / right)

    def fold_arith(self, node: ast.Arith):
        left = node.left
        right = node.right

        if not self.is_numeric_literal(left):
            return node

        if not self.is_numeric_literal(right):
            return node

        left_value = self.numeric_value(left)
        right_value = self.numeric_value(right)

        if node.op == "+":
            value = left_value + right_value
            return self.numeric_result_literal(
                left,
                right,
                value,
                node.location,
            )

        if node.op == "-":
            value = left_value - right_value
            return self.numeric_result_literal(
                left,
                right,
                value,
                node.location,
            )

        if node.op == "*":
            value = left_value * right_value
            return self.numeric_result_literal(
                left,
                right,
                value,
                node.location,
            )

        if node.op == "/":
            if right_value == 0:
                return node

            if isinstance(left, ast.Integer) and isinstance(right, ast.Integer):
                value = self.integer_division(left_value, right_value)

                if value is None:
                    return node

                return ast.Integer(value, node.location)

            value = left_value / right_value
            return self.numeric_result_literal(
                left,
                right,
                value,
                node.location,
            )

        if node.op == "**":
            try:
                value = left_value ** right_value
            except Exception:
                return node

            if isinstance(left, ast.Integer) and isinstance(right, ast.Integer):
                if right_value < 0:
                    return ast.Real(float(value), node.location)

                return ast.Integer(int(value), node.location)

            return self.numeric_result_literal(
                left,
                right,
                value,
                node.location,
            )

        return node

    def fold_rel(self, node: ast.Rel):
        left = node.left
        right = node.right

        comparable = False

        if self.is_numeric_literal(left) and self.is_numeric_literal(right):
            comparable = True
        elif isinstance(left, ast.String) and isinstance(right, ast.String):
            comparable = True
        elif isinstance(left, ast.Bool) and isinstance(right, ast.Bool):
            comparable = True

        if not comparable:
            return node

        left_value = left.value
        right_value = right.value

        if node.op in {".EQ.", "==", "="}:
            value = left_value == right_value
        elif node.op in {".NE.", "/="}:
            value = left_value != right_value
        elif node.op in {".LT.", "<"}:
            value = left_value < right_value
        elif node.op in {".LE.", "<="}:
            value = left_value <= right_value
        elif node.op in {".GT.", ">"}:
            value = left_value > right_value
        elif node.op in {".GE.", ">="}:
            value = left_value >= right_value
        else:
            return node

        return ast.Bool(value, node.location)

    def fold_logical(self, node: ast.Logical):
        left = node.left
        right = node.right

        if not isinstance(left, ast.Bool):
            return node

        if not isinstance(right, ast.Bool):
            return node

        if node.op == ".AND.":
            return ast.Bool(left.value and right.value, node.location)

        if node.op == ".OR.":
            return ast.Bool(left.value or right.value, node.location)

        return node

    def fold_unary(self, node: ast.Unary):
        value = node.value

        if node.op == "+":
            if isinstance(value, ast.Integer):
                return ast.Integer(+value.value, node.location)

            if isinstance(value, ast.Real):
                return ast.Real(+value.value, node.location)

            if isinstance(value, ast.Double):
                return ast.Double(+value.value, node.location)

            return node

        if node.op == "-":
            if isinstance(value, ast.Integer):
                return ast.Integer(-value.value, node.location)

            if isinstance(value, ast.Real):
                return ast.Real(-value.value, node.location)

            if isinstance(value, ast.Double):
                return ast.Double(-value.value, node.location)

            return node

        if node.op in {".NOT.", "NOT"}:
            if isinstance(value, ast.Bool):
                return ast.Bool(not value.value, node.location)

            return node

        return node
