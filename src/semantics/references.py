from dataclasses import replace

import abstract_syntax_tree as ast


class ReferenceResolver:
    """
    Resolve ambiguous IDENTIFIER(...) expressions.

    In Fortran, A(I) can mean either:
        - array reference
        - function call

    The parser cannot decide this syntactically, so it emits IndexedOrCall.
    This pass resolves IndexedOrCall using variable scope information:

        if name is declared as an array in the current scope:
            IndexedOrCall -> ArrayRef
        else:
            IndexedOrCall -> Call
    """

    def __init__(self, semantic_info):
        self.semantic_info = semantic_info
        self.current_scope = None

    def resolve(self, tree):
        return self.visit(tree)

    def find_scope(self, name: str, kind: str):
        for scope in self.semantic_info.scopes:
            if scope.name == name and scope.kind == kind:
                return scope

        return None

    def is_array_in_current_scope(self, name: str) -> bool:
        if self.current_scope is None:
            return False

        info = self.current_scope.variables.get(name)

        if info is None:
            return False

        return info.is_array

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
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "program")

            resolved = replace(
                node,
                statements=self.visit(node.statements),
            )

            self.current_scope = previous_scope
            return resolved

        if isinstance(node, ast.Subroutine):
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "subroutine")

            resolved = replace(
                node,
                statements=self.visit(node.statements),
            )

            self.current_scope = previous_scope
            return resolved

        if isinstance(node, ast.Function):
            previous_scope = self.current_scope
            self.current_scope = self.find_scope(node.name, "function")

            resolved = replace(
                node,
                statements=self.visit(node.statements),
            )

            self.current_scope = previous_scope
            return resolved

        if isinstance(node, ast.Label):
            return replace(
                node,
                statement=self.visit(node.statement),
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
                target=self.visit_assignment_target(node.target),
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
                    self.visit_assignment_target(variable)
                    for variable in node.variables
                ],
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
                start=self.visit_expression(node.start),
                end=self.visit_expression(node.end),
            )

        if isinstance(node, ast.CallStatement):
            return replace(
                node,
                arguments=[
                    self.visit_expression(argument)
                    for argument in node.arguments
                ],
            )

        if isinstance(node, (ast.Goto, ast.Stop, ast.Return, ast.Continue)):
            return node

        raise RuntimeError(
            f"unsupported AST node in reference resolver: {node!r}"
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
            f"unsupported declarator in reference resolver: {node!r}"
        )

    def visit_assignment_target(self, node):
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

        # Usually IndexedOrCall does not appear as assignment target because
        # statement variables are already parsed as Var/ArrayRef.
        if isinstance(node, ast.IndexedOrCall):
            return ast.ArrayRef(
                node.name,
                [
                    self.visit_expression(argument)
                    for argument in node.arguments
                ],
                node.location,
            )

        raise RuntimeError(
            f"unsupported assignment target in reference resolver: {node!r}"
        )

    def visit_expression(self, node):
        if isinstance(node, ast.IndexedOrCall):
            resolved_arguments = [
                self.visit_expression(argument)
                for argument in node.arguments
            ]

            if self.is_array_in_current_scope(node.name):
                return ast.ArrayRef(
                    node.name,
                    resolved_arguments,
                    node.location,
                )

            return ast.Call(
                node.name,
                resolved_arguments,
                node.location,
            )

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

        if isinstance(node, ast.Arith):
            return replace(
                node,
                left=self.visit_expression(node.left),
                right=self.visit_expression(node.right),
            )

        if isinstance(node, ast.Rel):
            return replace(
                node,
                left=self.visit_expression(node.left),
                right=self.visit_expression(node.right),
            )

        if isinstance(node, ast.Logical):
            return replace(
                node,
                left=self.visit_expression(node.left),
                right=self.visit_expression(node.right),
            )

        if isinstance(node, ast.Unary):
            return replace(
                node,
                value=self.visit_expression(node.value),
            )

        if isinstance(node, (
            ast.Integer,
            ast.Real,
            ast.Double,
            ast.String,
            ast.Bool,
            ast.Var,
        )):
            return node

        raise RuntimeError(
            f"unsupported expression in reference resolver: {node!r}"
        )


def resolve_references(tree, semantic_info):
    resolver = ReferenceResolver(semantic_info)
    return resolver.resolve(tree)
