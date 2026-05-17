from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional

import abstract_syntax_tree as ast
from error import record_node_error


INTEGER = "INTEGER"
REAL = "REAL"
DOUBLE = "DOUBLE"

NUMERIC_TYPES = {INTEGER, REAL, DOUBLE}

INTEGER_MIN = -2_147_483_648
INTEGER_MAX = 2_147_483_647

# These assume common IEEE-like sizes:
# REAL    -> 32-bit single precision
# DOUBLE  -> 64-bit double precision
# NOTE: EWVM has stricter limits
REAL_MAX = 3.4028235e38
DOUBLE_MAX = 1.7976931348623157e308


@dataclass(frozen=True)
class ConstantNumber:
    value: int | float
    type_name: str


def is_zero(value: ConstantNumber) -> bool:
    return value.value == 0


def widest_numeric_type(left_type: str, right_type: str) -> str:
    if DOUBLE in {left_type, right_type}:
        return DOUBLE

    if REAL in {left_type, right_type}:
        return REAL

    return INTEGER


def range_for_type(type_name: str) -> tuple[Optional[int | float], int | float]:
    if type_name == INTEGER:
        return INTEGER_MIN, INTEGER_MAX

    if type_name == REAL:
        return None, REAL_MAX

    if type_name == DOUBLE:
        return None, DOUBLE_MAX

    raise RuntimeError(f"unsupported numeric type {type_name!r}")


# TODO(numbers): validate intrinsic constant-domain errors, e.g.
#   SQRT(-1)
#   DSQRT(-1)
#   POW(0, negative)
#   EXP(value too large)

class NumberChecker:
    """
    Semantic numeric validation pass.

    Checks:
      - integer literals and constant integer expressions fit target INTEGER;
      - real literals and constant real expressions fit target REAL;
      - double literals and constant double expressions fit target DOUBLE;
      - constant divisions by zero.

    This pass intentionally runs after reference resolution and before type
    checking. Type checking remains responsible for deciding whether operands
    are valid for each operator; this pass only validates numeric values when
    they can be known statically.
    """

    def __init__(self, parser):
        self.parser = parser
        self.reported_range_nodes: set[int] = set()
        self.reported_div_zero_nodes: set[int] = set()

    def check(self, tree) -> None:
        self.visit(tree)

    ###
    # Generic AST traversal
    ###

    def visit(self, node) -> None:
        if node is None:
            return

        if isinstance(node, list):
            for item in node:
                self.visit(item)
            return

        if isinstance(node, ast.File):
            for unit in node.program_units:
                self.visit(unit)
            return

        if isinstance(node, ast.Program):
            self.visit(node.statements)
            return

        if isinstance(node, ast.Subroutine):
            self.visit(node.statements)
            return

        if isinstance(node, ast.Function):
            self.visit(node.statements)
            return

        if isinstance(node, ast.Label):
            self.visit(node.statement)
            return

        if isinstance(node, ast.Declare):
            for declarator in node.declarators:
                self.visit_declarator(declarator)
            return

        if isinstance(node, ast.Assign):
            self.visit_variable(node.target)
            self.visit_expression(node.value)
            return

        if isinstance(node, ast.Print):
            self.visit_expression_list(node.items)
            return

        if isinstance(node, ast.Write):
            self.visit_expression_list(node.items)
            return

        if isinstance(node, ast.Read):
            for variable in node.variables:
                self.visit_variable(variable)
            return

        if isinstance(node, ast.If):
            self.visit_expression(node.condition)
            self.visit(node.then_branch)
            if node.else_branch is not None:
                self.visit(node.else_branch)
            return

        if isinstance(node, ast.Do):
            self.visit_expression(node.start)
            self.visit_expression(node.end)
            if node.step is not None:
                self.visit_expression(node.step)
            return

        if isinstance(node, ast.CallStatement):
            self.visit_expression_list(node.arguments)
            return

        if isinstance(node, (ast.Goto, ast.Stop, ast.Return, ast.Continue)):
            return

        raise RuntimeError(f"unsupported AST node in number checker: {node!r}")

    def visit_declarator(self, node) -> None:
        if isinstance(node, ast.VarDeclarator):
            return

        if isinstance(node, ast.ArrayDeclarator):
            self.visit_expression_list(node.dimensions)
            return

        raise RuntimeError(
            f"unsupported declarator in number checker: {node!r}"
        )

    def visit_variable(self, node) -> None:
        if isinstance(node, ast.Var):
            return

        if isinstance(node, ast.ArrayRef):
            self.visit_expression_list(node.indices)
            return

        raise RuntimeError(f"unsupported variable in number checker: {node!r}")

    def visit_expression_list(self, expressions) -> None:
        for expression in expressions:
            self.visit_expression(expression)

    ###
    # Expression traversal
    ###

    def visit_expression(self, node) -> None:
        if isinstance(node, (ast.Integer, ast.Real, ast.Double)):
            constant = self.constant_number(node)
            if constant is not None:
                self.check_range(node, constant)
            return

        if isinstance(node, (ast.String, ast.Bool, ast.Var)):
            return

        if isinstance(node, ast.ArrayRef):
            self.visit_expression_list(node.indices)
            return

        if isinstance(node, ast.Call):
            self.visit_expression_list(node.arguments)
            return

        if isinstance(node, ast.IndexedOrCall):
            self.visit_expression_list(node.arguments)
            return

        if isinstance(node, ast.Unary):
            # Handle signed numeric literals as a single semantic value.
            # This avoids falsely rejecting -2147483648 just because the lexer
            # first saw the unsigned literal 2147483648.
            if isinstance(node.value, (ast.Integer, ast.Real, ast.Double)):
                constant = self.evaluate_constant_number(node)
                if constant is not None:
                    self.check_range(node, constant)
                return

            self.visit_expression(node.value)

            constant = self.evaluate_constant_number(node)
            if constant is not None:
                self.check_range(node, constant)

            return

        if isinstance(node, ast.Arith):
            self.visit_expression(node.left)
            self.visit_expression(node.right)

            right_constant = self.evaluate_constant_number(node.right)

            if (
                node.op == "/" and
                right_constant is not None and
                is_zero(right_constant)
            ):
                self.report_division_by_zero(node.right)
                return

            constant = self.evaluate_constant_number(node)
            if constant is not None:
                self.check_range(node, constant)

            return

        if isinstance(node, ast.Rel):
            self.visit_expression(node.left)
            self.visit_expression(node.right)
            return

        if isinstance(node, ast.Logical):
            self.visit_expression(node.left)
            self.visit_expression(node.right)
            return

        raise RuntimeError(
            f"unsupported expression in number checker: {node!r}"
        )

    ###
    # Constant numeric evaluation
    ###

    def constant_number(self, node) -> Optional[ConstantNumber]:
        if isinstance(node, ast.Integer):
            return ConstantNumber(node.value, INTEGER)

        if isinstance(node, ast.Real):
            return ConstantNumber(node.value, REAL)

        if isinstance(node, ast.Double):
            return ConstantNumber(node.value, DOUBLE)

        return None

    def evaluate_constant_number(self, node) -> Optional[ConstantNumber]:
        literal = self.constant_number(node)

        if literal is not None:
            return literal

        if isinstance(node, ast.Unary):
            value = self.evaluate_constant_number(node.value)

            if value is None:
                return None

            if node.op == "+":
                return value

            if node.op == "-":
                return ConstantNumber(-value.value, value.type_name)

            return None

        if isinstance(node, ast.Arith):
            left = self.evaluate_constant_number(node.left)
            right = self.evaluate_constant_number(node.right)

            if left is None or right is None:
                return None

            result_type = widest_numeric_type(left.type_name, right.type_name)

            try:
                if node.op == "+":
                    result = left.value + right.value
                elif node.op == "-":
                    result = left.value - right.value
                elif node.op == "*":
                    result = left.value * right.value
                elif node.op == "/":
                    if right.value == 0:
                        return None

                    if (
                        left.type_name == INTEGER and
                        right.type_name == INTEGER
                    ):
                        # Fortran-style integer division truncates toward zero.
                        result = int(left.value / right.value)
                        result_type = INTEGER
                    else:
                        result = left.value / right.value
                elif node.op == "**":
                    result = left.value ** right.value

                    if (
                        left.type_name == INTEGER
                        and right.type_name == INTEGER
                        and right.value >= 0
                    ):
                        result_type = INTEGER
                    elif (
                        left.type_name == INTEGER
                        and right.type_name == INTEGER
                        and right.value < 0
                    ):
                        result_type = REAL
                    else:
                        result_type = widest_numeric_type(
                            left.type_name,
                            right.type_name,
                        )
                else:
                    return None
            except (OverflowError, ZeroDivisionError, ValueError):
                # OverflowError can happen during Python evaluation.
                # Use infinity so the range check reports a clean diagnostic.
                result = math.inf

            return ConstantNumber(result, result_type)

        return None

    ###
    # Diagnostics
    ###

    def check_range(self, node, constant: ConstantNumber) -> None:
        if id(node) in self.reported_range_nodes:
            return

        type_name = constant.type_name
        value = constant.value

        if type_name == INTEGER:
            if not isinstance(value, int):
                return

            if INTEGER_MIN <= value <= INTEGER_MAX:
                return

            self.report_range_error(
                node,
                value=value,
                type_name="integer",
                hint=(
                    f"integer values must be between "
                    f"{INTEGER_MIN} and {INTEGER_MAX}"
                ),
            )
            return

        if type_name in {REAL, DOUBLE}:
            _, max_value = range_for_type(type_name)

            if isinstance(value, float) and math.isnan(value):
                self.report_range_error(
                    node,
                    value=value,
                    type_name=type_name.lower(),
                    hint=f"{type_name.lower()} values cannot be NaN",
                )
                return

            if (
                isinstance(value, float)
                and math.isinf(value)
            ) or abs(value) > max_value:
                self.report_range_error(
                    node,
                    value=value,
                    type_name=type_name.lower(),
                    hint=(
                        f"{type_name.lower()} values must be representable "
                        f"in the target {type_name} range"
                    ),
                )
                return

    def report_range_error(
        self,
        node,
        *,
        value: int | float,
        type_name: str,
        hint: str,
    ) -> None:
        self.reported_range_nodes.add(id(node))

        record_node_error(
            self.parser,
            node,
            message=f"{type_name} value {value!r} out of range",
            hint=hint,
        )

    def report_division_by_zero(self, node) -> None:
        if id(node) in self.reported_div_zero_nodes:
            return

        self.reported_div_zero_nodes.add(id(node))

        record_node_error(
            self.parser,
            node,
            message="division by zero",
        )


def check_numbers(parser, tree) -> None:
    checker = NumberChecker(parser)
    checker.check(tree)
