from __future__ import annotations

from typing import Optional
from difflib import SequenceMatcher

import abstract_syntax_tree as ast
from error import record_node_error

from .semantic_info import ProcedureInfo


INTRINSIC_FUNCTIONS = {
    "ABS", "IABS", "DABS",
    "POW",
    "SQRT", "DSQRT",
    "EXP", "DEXP",
    "INT", "REAL", "DBLE", "FLOAT",
    "MAX", "MIN",
    "MOD",
}

INTRINSIC_FUNCTION_ARITY = {
    "ABS":   (1, 1),
    "IABS":  (1, 1),
    "DABS":  (1, 1),

    "POW":   (2, 2),

    "SQRT":  (1, 1),
    "DSQRT": (1, 1),

    "EXP":   (1, 1),
    "DEXP":  (1, 1),

    "INT":   (1, 1),
    "REAL":  (1, 1),
    "DBLE":  (1, 1),
    "FLOAT": (1, 1),

    # Fortran MAX/MIN are variadic, but require at least 2 arguments.
    "MAX":   (2, None),
    "MIN":   (2, None),

    "MOD":   (2, 2),
}

INTRINSIC_SUBROUTINES = set()


def similarity_ratio(left: str, right: str) -> float:
    """
    Return a similarity score between 0.0 and 1.0.
    """

    return SequenceMatcher(None, left.upper(), right.upper()).ratio()


def similar_names(name: str, candidates: set[str], *, threshold: float = 0.65) -> list[str]:
    """
    Return candidate names similar to name, ordered by similarity.
    """

    scored = [
        (similarity_ratio(name, candidate), candidate)
        for candidate in candidates
    ]

    scored = [
        (score, candidate)
        for score, candidate in scored
        if score >= threshold
    ]

    scored.sort(key=lambda item: (-item[0], item[1]))

    return [candidate for _, candidate in scored[:3]]


def suggestion_hint(name: str, candidates: set[str]) -> Optional[str]:
    """
    Build a 'perhaps you meant ...' hint for an unknown procedure.
    """

    suggestions = similar_names(name, candidates)

    if not suggestions:
        return None

    if len(suggestions) == 1:
        return f"perhaps you meant {suggestions[0]!r}"

    if len(suggestions) == 2:
        return f"perhaps you meant {suggestions[0]!r} or {suggestions[1]!r}"

    return (
        f"perhaps you meant {suggestions[0]!r}, "
        f"{suggestions[1]!r}, or {suggestions[2]!r}"
    )


class ProcedureChecker:
    def __init__(self, parser):
        self.parser = parser
        self.procedures: dict[str, ProcedureInfo] = {}

    def check(self, tree):
        self.register_builtins()
        self.collect_definitions(tree)
        self.check_calls(tree)
        return self.procedures

    def register_builtins(self):
        for name in INTRINSIC_FUNCTIONS:
            self.procedures[name] = ProcedureInfo(
                name=name,
                kind="intrinsic_function",
                arguments=[],
                node=None,
                return_type="UNKNOWN",
            )

        for name in INTRINSIC_SUBROUTINES:
            self.procedures[name] = ProcedureInfo(
                name=name,
                kind="intrinsic_subroutine",
                arguments=[],
                node=None,
                return_type=None,
            )

    def collect_definitions(self, node):
        if isinstance(node, ast.File):
            for unit in node.program_units:
                self.collect_definitions(unit)
            return

        if isinstance(node, ast.Program):
            self.define_procedure(
                name=node.name,
                kind="program",
                arguments=[],
                node=node,
                return_type=None,
            )
            return

        if isinstance(node, ast.Subroutine):
            self.define_procedure(
                name=node.name,
                kind="subroutine",
                arguments=node.arguments,
                node=node,
                return_type=None,
            )
            return

        if isinstance(node, ast.Function):
            self.define_procedure(
                name=node.name,
                kind="function",
                arguments=node.arguments,
                node=node,
                return_type=node.return_type,
            )
            return

    def define_procedure(
        self,
        *,
        name: str,
        kind: str,
        arguments: list[str],
        node,
        return_type: Optional[str],
    ):
        normalized_name = name.upper()

        existing = self.procedures.get(normalized_name)

        if existing is not None and existing.kind not in {
            "intrinsic_function",
            "intrinsic_subroutine",
        }:
            record_node_error(
                self.parser,
                node,
                message=(
                    f"{kind} {name!r} already defined as "
                    f"{existing.kind} {existing.name!r}"
                )
            )
            return

        if existing is not None and existing.kind.startswith("intrinsic"):
            record_node_error(
                self.parser,
                node,
                message=f"{kind} {name!r} conflicts with intrinsic procedure {existing.name!r}",
                hint="choose a different procedure name; intrinsic procedure names are reserved"
            )
            return

        self.procedures[normalized_name] = ProcedureInfo(
            name=name,
            kind=kind,
            arguments=arguments,
            node=node,
            return_type=return_type,
        )

    def check_calls(self, node):
        if node is None:
            return

        if isinstance(node, list):
            for item in node:
                self.check_calls(item)
            return

        if isinstance(node, ast.File):
            for unit in node.program_units:
                self.check_calls(unit)
            return

        if isinstance(node, ast.Program):
            self.check_calls(node.statements)
            return

        if isinstance(node, ast.Subroutine):
            self.check_calls(node.statements)
            return

        if isinstance(node, ast.Function):
            self.check_calls(node.statements)
            return

        if isinstance(node, ast.Label):
            self.check_calls(node.statement)
            return

        if isinstance(node, ast.Declare):
            for declarator in node.declarators:
                if isinstance(declarator, ast.ArrayDeclarator):
                    self.check_calls(declarator.dimensions)
            return

        if isinstance(node, ast.Assign):
            self.check_calls(node.target)
            self.check_calls(node.value)
            return

        if isinstance(node, ast.Print):
            self.check_calls(node.items)
            return

        if isinstance(node, ast.Write):
            self.check_calls(node.items)
            return

        if isinstance(node, ast.Read):
            self.check_calls(node.variables)
            return

        if isinstance(node, ast.If):
            self.check_calls(node.condition)
            self.check_calls(node.then_branch)
            if node.else_branch is not None:
                self.check_calls(node.else_branch)
            return

        if isinstance(node, ast.Do):
            self.check_calls(node.start)
            self.check_calls(node.end)
            return

        if isinstance(node, ast.CallStatement):
            self.check_subroutine_call(node)
            for argument in node.arguments:
                self.check_calls(argument)
            return

        if isinstance(node, ast.Call):
            self.check_function_call(node)
            for argument in node.arguments:
                self.check_calls(argument)
            return

        if isinstance(node, ast.ArrayRef):
            self.check_calls(node.indices)
            return

        if isinstance(node, ast.Arith):
            self.check_calls(node.left)
            self.check_calls(node.right)
            return

        if isinstance(node, ast.Rel):
            self.check_calls(node.left)
            self.check_calls(node.right)
            return

        if isinstance(node, ast.Logical):
            self.check_calls(node.left)
            self.check_calls(node.right)
            return

        if isinstance(node, ast.Unary):
            self.check_calls(node.value)
            return

        if isinstance(node, (
            ast.Var,
            ast.VarDeclarator,
            ast.ArrayDeclarator,
            ast.Integer,
            ast.Real,
            ast.Double,
            ast.String,
            ast.Bool,
            ast.Goto,
            ast.Stop,
            ast.Return,
            ast.Continue,
        )):
            return

        if isinstance(node, ast.IndexedOrCall):
            raise RuntimeError(
                f"unresolved IndexedOrCall reached procedure checker: {node!r}"
            )

        raise RuntimeError(f"unsupported AST node in procedure checker: {node!r}")

    def check_subroutine_call(self, node: ast.CallStatement):
        name = node.name.upper()
        procedure = self.procedures.get(name)

        if procedure is None:
            self.report_unknown_procedure(
                node,
                name=node.name,
                expected_kind="subroutine",
            )
            return

        if procedure.kind not in {"subroutine", "intrinsic_subroutine"}:
            record_node_error(
                self.parser,
                node,
                message=f"{node.name!r} is not a subroutine",
                hint="use function calls in expressions, and subroutines with CALL",
            )
            return

        self.check_argument_count(node, procedure)
        self.check_reference_arguments(node, procedure)

    def check_function_call(self, node: ast.Call):
        name = node.name.upper()
        procedure = self.procedures.get(name)

        if procedure is None:
            self.report_unknown_procedure(
                node,
                name=node.name,
                expected_kind="function",
            )
            return

        if procedure.kind not in {"function", "intrinsic_function"}:
            record_node_error(
                self.parser,
                node,
                message=f"{node.name!r} is not a function",
                hint="use CALL for subroutines, and function calls inside expressions",
            )
            return

        if procedure.kind == "intrinsic_function":
            self.check_intrinsic_argument_count(node, procedure)
            return

        self.check_argument_count(node, procedure)
        self.check_reference_arguments(node, procedure)

    def report_unknown_procedure(self, node, *, name: str, expected_kind: str):
        candidates = set(self.procedures.keys())

        hint = suggestion_hint(name, candidates)

        record_node_error(
            self.parser,
            node,
            message=f"unknown {expected_kind} {name!r}",
            hint=hint,
        )

    def check_argument_count(self, node, procedure: ProcedureInfo):
        expected = len(procedure.arguments)
        actual = len(node.arguments)

        if expected != actual:
            record_node_error(
                self.parser,
                node,
                message=(
                    f"{procedure.kind} {procedure.name!r} expects "
                    f"{expected} argument(s), got {actual}"
                ),
            )

    def check_reference_arguments(self, node, procedure: ProcedureInfo):
        if procedure.kind not in {"function", "subroutine"}:
            return

        for argument in node.arguments:
            if not isinstance(argument, (ast.Var, ast.ArrayRef)):
                record_node_error(
                    self.parser,
                    argument,
                    message=(
                        f"argument passed to {procedure.kind} "
                        f"{procedure.name!r} must be a variable "
                        "or array element"
                    ),
                    hint=(
                        "this compiler passes procedure arguments by reference"
                    ),
                )

    def check_intrinsic_argument_count(
        self,
        node: ast.Call,
        procedure: ProcedureInfo
    ):
        arity = INTRINSIC_FUNCTION_ARITY.get(procedure.name.upper())

        if arity is None:
            return

        minimum, maximum = arity
        actual = len(node.arguments)

        if actual < minimum:
            if maximum is None:
                expected = f"at least {minimum}"
            else:
                expected = str(minimum)

            record_node_error(
                self.parser,
                node,
                message=(
                    f"intrinsic function {procedure.name!r} expects "
                    f"{expected} argument(s), got {actual}"
                ),
            )
            return

        if maximum is not None and actual > maximum:
            record_node_error(
                self.parser,
                node,
                message=(
                    f"intrinsic function {procedure.name!r} expects "
                    f"{maximum} argument(s), got {actual}"
                ),
            )


def check_procedures(parser, tree) -> dict[str, ProcedureInfo]:
    checker = ProcedureChecker(parser)
    return checker.check(tree)
