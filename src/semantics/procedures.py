from __future__ import annotations

from difflib import SequenceMatcher

import abstract_syntax_tree as ast
from error import print_node_error

from .semantic_info import ProcedureInfo

# TODO remove intrinsics that we don't support
INTRINSIC_FUNCTIONS = {
    "ABS",
    "IABS",
    "DABS",
    "SQRT",
    "DSQRT",
    "SIN",
    "DSIN",
    "COS",
    "DCOS",
    "TAN",
    "EXP",
    "DEXP",
    "LOG",
    "DLOG",
    "LOG10",
    "DLOG10",
    "INT",
    "REAL",
    "DBLE",
    "FLOAT",
    "MAX",
    "MIN",
    "MOD",
    "PRINT",
    "READ",
    "WRITE"
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


def suggestion_hint(name: str, candidates: set[str]) -> str | None:
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
        return_type: str | None,
    ):
        normalized_name = name.upper()

        existing = self.procedures.get(normalized_name)

        if existing is not None and existing.kind not in {
            "intrinsic_function",
            "intrinsic_subroutine",
        }:
            print_node_error(
                self.parser,
                node,
                message=(
                    f"{kind} {name!r} already defined as "
                    f"{existing.kind} {existing.name!r}"
                )
            )
            self.parser.has_error = True
            return

        if existing is not None and existing.kind.startswith("intrinsic"):
            print_node_error(
                self.parser,
                node,
                message=f"{kind} {name!r} conflicts with intrinsic procedure {existing.name!r}",
                hint="choose a different name or explicitly support intrinsic shadowing later",
            )
            self.parser.has_error = True
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
            print_node_error(
                self.parser,
                node,
                message=f"{node.name!r} is not a subroutine",
                hint="use function calls in expressions, and subroutines with CALL",
            )
            self.parser.has_error = True
            return

        self.check_argument_count(node, procedure)

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
            print_node_error(
                self.parser,
                node,
                message=f"{node.name!r} is not a function",
                hint="use CALL for subroutines, and function calls inside expressions",
            )
            self.parser.has_error = True
            return

        if procedure.kind == "intrinsic_function":
            return

        self.check_argument_count(node, procedure)

    def report_unknown_procedure(self, node, *, name: str, expected_kind: str):
        candidates = set(self.procedures.keys())

        hint = suggestion_hint(name, candidates)

        print_node_error(
            self.parser,
            node,
            message=f"unknown {expected_kind} {name!r}",
            hint=hint,
        )

        self.parser.has_error = True

    def check_argument_count(self, node, procedure: ProcedureInfo):
        expected = len(procedure.arguments)
        actual = len(node.arguments)

        if expected != actual:
            print_node_error(
                self.parser,
                node,
                message=(
                    f"{procedure.kind} {procedure.name!r} expects "
                    f"{expected} argument(s), got {actual}"
                ),
            )
            self.parser.has_error = True


def check_procedures(parser, tree) -> dict[str, ProcedureInfo]:
    checker = ProcedureChecker(parser)
    return checker.check(tree)
