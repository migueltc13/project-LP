from __future__ import annotations

from dataclasses import dataclass

import abstract_syntax_tree as ast
from error import record_node_error


UNKNOWN   = "UNKNOWN"
INTEGER   = "INTEGER"
REAL      = "REAL"
DOUBLE    = "DOUBLE"
LOGICAL   = "LOGICAL"
CHARACTER = "CHARACTER"

NUMERIC_TYPES = {INTEGER, REAL, DOUBLE}
SCALAR_TYPES = NUMERIC_TYPES | {LOGICAL, CHARACTER, UNKNOWN}


@dataclass
class TypeCheckResult:
    """
    Type checker metadata.

    expression_types:
        Maps id(expression_node) to its inferred type.
        This is useful for code generation.
    """

    expression_types: dict[int, str]


def is_numeric(type_name: str) -> bool:
    return type_name in NUMERIC_TYPES


def is_assignable(expected_type: str, actual_type: str) -> bool:
    """
    Return True if a value of actual_type can be assigned to expected_type.

    Strict but practical Fortran-like rules:
        INTEGER -> REAL      allowed
        INTEGER -> DOUBLE    allowed
        REAL    -> DOUBLE    allowed
        same type            allowed

    Narrowing conversions such as REAL -> INTEGER are rejected for now.
    """

    if expected_type == UNKNOWN or actual_type == UNKNOWN:
        return True

    if expected_type == actual_type:
        return True

    if expected_type == REAL and actual_type == INTEGER:
        return True

    if expected_type == DOUBLE and actual_type in {INTEGER, REAL}:
        return True

    return False


def widest_numeric_type(left_type: str, right_type: str) -> str:
    """
    Return the resulting type for a numeric binary operation.
    """

    if left_type == UNKNOWN or right_type == UNKNOWN:
        return UNKNOWN

    if DOUBLE in {left_type, right_type}:
        return DOUBLE

    if REAL in {left_type, right_type}:
        return REAL

    if left_type == INTEGER and right_type == INTEGER:
        return INTEGER

    return UNKNOWN


def type_name_for_literal(node) -> str:
    if isinstance(node, ast.Integer):
        return INTEGER

    if isinstance(node, ast.Real):
        return REAL

    if isinstance(node, ast.Double):
        return DOUBLE

    if isinstance(node, ast.String):
        return CHARACTER

    if isinstance(node, ast.Bool):
        return LOGICAL

    return UNKNOWN


class TypeChecker:
    def __init__(self, parser, semantic_info):
        self.parser = parser
        self.semantic_info = semantic_info
        self.expression_types: dict[int, str] = {}

        self.current_scope = None

    def check(self, tree) -> TypeCheckResult:
        self.visit(tree)

        return TypeCheckResult(
            expression_types=self.expression_types,
        )

    def set_expression_type(self, node, type_name: str) -> str:
        self.expression_types[id(node)] = type_name
        return type_name

    def get_variable_info(self, name: str):
        if self.current_scope is None:
            return None

        return self.current_scope.variables.get(name)

    def variable_type(self, name: str) -> str:
        info = self.get_variable_info(name)

        if info is None:
            return UNKNOWN

        return info.type_name

    def find_scope(self, name: str, kind: str):
        for scope in self.semantic_info.scopes:
            if scope.name == name and scope.kind == kind:
                return scope

        return None

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
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "program")

            self.visit(node.statements)

            self.current_scope = previous_scope
            return

        if isinstance(node, ast.Subroutine):
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "subroutine")

            self.visit(node.statements)

            self.current_scope = previous_scope
            return

        if isinstance(node, ast.Function):
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "function")

            self.visit(node.statements)

            self.current_scope = previous_scope
            return

        if isinstance(node, ast.Label):
            self.visit(node.statement)
            return

        if isinstance(node, ast.Declare):
            self.check_declaration(node)
            return

        if isinstance(node, ast.Assign):
            self.check_assignment(node)
            return

        if isinstance(node, ast.Print):
            for item in node.items:
                self.infer_expression(item)
            return

        if isinstance(node, ast.Write):
            for item in node.items:
                self.infer_expression(item)
            return

        if isinstance(node, ast.Read):
            for variable in node.variables:
                self.check_assignment_target(variable)
            return

        if isinstance(node, ast.If):
            condition_type = self.infer_expression(node.condition)

            if condition_type not in {LOGICAL, UNKNOWN}:
                record_node_error(
                    self.parser,
                    node.condition,
                    message=(
                        "IF condition must be LOGICAL, "
                        f"got {condition_type}"
                    ),
                )

            self.visit(node.then_branch)

            if node.else_branch is not None:
                self.visit(node.else_branch)

            return

        if isinstance(node, ast.Do):
            self.check_do(node)
            return

        if isinstance(node, ast.CallStatement):
            self.check_call_statement(node)
            return

        if isinstance(node, (ast.Goto, ast.Stop, ast.Return, ast.Continue)):
            return

        raise RuntimeError(f"unsupported AST node in type checker: {node!r}")

    def check_declaration(self, node: ast.Declare) -> None:
        for declarator in node.declarators:
            if isinstance(declarator, ast.ArrayDeclarator):
                for dimension in declarator.dimensions:
                    dimension_type = self.infer_expression(dimension)

                    if dimension_type not in {INTEGER, UNKNOWN}:
                        record_node_error(
                            self.parser,
                            dimension,
                            message=(
                                "array dimension must be INTEGER, "
                                f"got {dimension_type}"
                            ),
                        )

    def check_assignment(self, node: ast.Assign) -> None:
        target_type = self.check_assignment_target(node.target)
        value_type = self.infer_expression(node.value)

        if not is_assignable(target_type, value_type):
            record_node_error(
                self.parser,
                node.value,
                message=(
                    f"cannot assign {value_type} value "
                    f"to {target_type} variable"
                ),
            )

    def check_assignment_target(self, node) -> str:
        if isinstance(node, ast.Var):
            return self.variable_type(node.name)

        if isinstance(node, ast.ArrayRef):
            array_type = self.variable_type(node.name)

            for index in node.indices:
                index_type = self.infer_expression(index)

                if index_type not in {INTEGER, UNKNOWN}:
                    record_node_error(
                        self.parser,
                        index,
                        message=(
                            "array index must be INTEGER, "
                            f"got {index_type}"
                        ),
                    )

            return array_type

        raise RuntimeError(f"invalid assignment target in type checker: {node!r}")

    def check_do(self, node: ast.Do) -> None:
        loop_type = self.variable_type(node.variable.name)

        if loop_type not in {INTEGER, UNKNOWN}:
            # Fortran variants may allow real DO variables historically, but
            # INTEGER loop variables keep this compiler simpler and safer.
            record_node_error(
                self.parser,
                node.variable,
                message=(
                    "DO loop variable must be INTEGER, "
                    f"got {loop_type}"
                ),
            )

        start_type = self.infer_expression(node.start)
        end_type = self.infer_expression(node.end)
        step_type = (
            self.infer_expression(node.step)
            if node.step is not None
            else INTEGER
        )

        if start_type not in {INTEGER, UNKNOWN}:
            record_node_error(
                self.parser,
                node.start,
                message=(
                    "DO loop lower bound must be INTEGER, "
                    f"got {start_type}"
                ),
            )

        if end_type not in {INTEGER, UNKNOWN}:
            record_node_error(
                self.parser,
                node.end,
                message=(
                    "DO loop upper bound must be INTEGER, "
                    f"got {end_type}"
                ),
            )

        if step_type not in {INTEGER, UNKNOWN}:
            record_node_error(
                self.parser,
                node.step,
                message=(
                    "DO loop step must be INTEGER, "
                    f"got {step_type}"
                ),
            )

        if isinstance(node.step, ast.Integer) and node.step.value <= 0:
            record_node_error(
                self.parser,
                node.step,
                message="DO loop step must be a positive INTEGER",
            )

        if (
            isinstance(node.step, ast.Unary)
            and node.step.op == "-"
            and isinstance(node.step.value, ast.Integer)
        ):
            record_node_error(
                self.parser,
                node.step,
                message="DO loop step must be a positive INTEGER",
            )

    def check_call_statement(self, node: ast.CallStatement) -> None:
        for argument in node.arguments:
            self.infer_expression(argument)

    def infer_expression(self, node) -> str:
        literal_type = type_name_for_literal(node)

        if literal_type != UNKNOWN:
            return self.set_expression_type(node, literal_type)

        if isinstance(node, ast.Var):
            return self.set_expression_type(
                node,
                self.variable_type(node.name),
            )

        if isinstance(node, ast.ArrayRef):
            for index in node.indices:
                index_type = self.infer_expression(index)

                if index_type not in {INTEGER, UNKNOWN}:
                    record_node_error(
                        self.parser,
                        index,
                        message=(
                            "array index must be INTEGER, "
                            f"got {index_type}"
                        ),
                    )

            return self.set_expression_type(
                node,
                self.variable_type(node.name),
            )

        if isinstance(node, ast.Call):
            return self.infer_call_expression(node)

        if isinstance(node, ast.Unary):
            return self.infer_unary(node)

        if isinstance(node, ast.Arith):
            return self.infer_arith(node)

        if isinstance(node, ast.Rel):
            return self.infer_rel(node)

        if isinstance(node, ast.Logical):
            return self.infer_logical(node)

        if isinstance(node, ast.IndexedOrCall):
            raise RuntimeError(
                f"unresolved IndexedOrCall reached type checker: {node!r}"
            )

        raise RuntimeError(f"unsupported expression in type checker: {node!r}")

    def infer_call_expression(self, node: ast.Call) -> str:
        for argument in node.arguments:
            self.infer_expression(argument)

        procedure = self.semantic_info.procedures.get(node.name.upper())

        if procedure is None:
            return self.set_expression_type(node, UNKNOWN)

        if procedure.return_type is None:
            return self.set_expression_type(node, UNKNOWN)

        return self.set_expression_type(node, procedure.return_type)

    def infer_unary(self, node: ast.Unary) -> str:
        value_type = self.infer_expression(node.value)

        if node.op == "+":
            if value_type not in NUMERIC_TYPES | {UNKNOWN}:
                record_node_error(
                    self.parser,
                    node.value,
                    message=(
                        "unary '+' requires numeric operand, "
                        f"got {value_type}"
                    ),
                )

            return self.set_expression_type(node, value_type)

        if node.op == "-":
            if value_type not in NUMERIC_TYPES | {UNKNOWN}:
                record_node_error(
                    self.parser,
                    node.value,
                    message=(
                        "unary '-' requires numeric operand, "
                        f"got {value_type}"
                    ),
                )

            return self.set_expression_type(node, value_type)

        if node.op in {".NOT.", "NOT"}:
            if value_type not in {LOGICAL, UNKNOWN}:
                record_node_error(
                    self.parser,
                    node.value,
                    message=(
                        "NOT requires LOGICAL operand, "
                        f"got {value_type}"
                    ),
                )

            return self.set_expression_type(node, LOGICAL)

        raise RuntimeError(f"unsupported unary operator in type checker: {node.op!r}")

    def infer_arith(self, node: ast.Arith) -> str:
        left_type = self.infer_expression(node.left)
        right_type = self.infer_expression(node.right)

        if left_type not in NUMERIC_TYPES | {UNKNOWN}:
            record_node_error(
                self.parser,
                node.left,
                message=(
                    "left arithmetic operand must be numeric, "
                    f"got {left_type}"
                ),
            )

        if right_type not in NUMERIC_TYPES | {UNKNOWN}:
            record_node_error(
                self.parser,
                node.right,
                message=(
                    "right arithmetic operand must be numeric, "
                    f"got {right_type}"
                ),
            )

        result_type = widest_numeric_type(left_type, right_type)

        return self.set_expression_type(node, result_type)

    def infer_rel(self, node: ast.Rel) -> str:
        left_type = self.infer_expression(node.left)
        right_type = self.infer_expression(node.right)

        if left_type == UNKNOWN or right_type == UNKNOWN:
            return self.set_expression_type(node, LOGICAL)

        if is_numeric(left_type) and is_numeric(right_type):
            return self.set_expression_type(node, LOGICAL)

        if left_type == right_type:
            return self.set_expression_type(node, LOGICAL)

        record_node_error(
            self.parser,
            node,
            message=(
                "relational operands must have compatible types, "
                f"got {left_type} and {right_type}"
            ),
        )

        return self.set_expression_type(node, LOGICAL)

    def infer_logical(self, node: ast.Logical) -> str:
        left_type = self.infer_expression(node.left)
        right_type = self.infer_expression(node.right)

        if left_type not in {LOGICAL, UNKNOWN}:
            record_node_error(
                self.parser,
                node.left,
                message=(
                    "left logical operand must be LOGICAL, "
                    f"got {left_type}"
                ),
            )

        if right_type not in {LOGICAL, UNKNOWN}:
            record_node_error(
                self.parser,
                node.right,
                message=(
                    "right logical operand must be LOGICAL, "
                    f"got {right_type}"
                ),
            )

        return self.set_expression_type(node, LOGICAL)


def check_types(parser, tree, semantic_info) -> TypeCheckResult:
    checker = TypeChecker(parser, semantic_info)
    return checker.check(tree)
