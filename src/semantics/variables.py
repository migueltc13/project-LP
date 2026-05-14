import abstract_syntax_tree as ast
from error import print_node_error

from .semantic_info import SemanticInfo, ScopeInfo, VariableInfo


def touch_variable(scope: ScopeInfo, name: str) -> VariableInfo:
    if name not in scope.variables:
        scope.variables[name] = VariableInfo(name=name)
        scope.variable_order.append(name)

    return scope.variables[name]


class VariableChecker:
    def __init__(self, parser):
        self.parser = parser
        self.semantic_info = SemanticInfo()
        self.scope: ScopeInfo | None = None

    def check(self, node) -> SemanticInfo:
        self.visit(node)
        return self.semantic_info

    def enter_scope(self, name: str, kind: str) -> ScopeInfo:
        scope = ScopeInfo(name=name, kind=kind)
        self.semantic_info.scopes.append(scope)
        self.scope = scope
        return scope

    def leave_scope(self) -> None:
        self.scope = None

    def declare(self, node, name: str, type_name: str, *, is_array: bool = False):
        info = touch_variable(self.scope, name)

        if info.declared:
            # Function/subroutine arguments are introduced by the argument list
            # with UNKNOWN type. A later declaration gives them their real type.
            if info.is_argument and info.type_name == "UNKNOWN":
                info.type_name = type_name
                info.is_array = is_array
                info.declaration_node = node
                return

            print_node_error(
                self.parser,
                node,
                message=f"variable {name!r} already declared",
            )
            self.parser.has_error = True
            return

        info.type_name = type_name
        info.declared = True
        info.is_array = is_array
        info.declaration_node = node

    def declare_argument(self, name: str):
        info = touch_variable(self.scope, name)
        info.declared = True
        info.initialized = True
        info.is_argument = True
        info.type_name = "UNKNOWN"

    def mark_used(self, node, name: str):
        info = touch_variable(self.scope, name)
        info.used = True

        if not info.declared:
            print_node_error(
                self.parser,
                node,
                message=f"use of undeclared variable {name!r}"
            )
            self.parser.has_error = True

        elif not info.initialized:
            print_node_error(
                self.parser,
                node,
                message=f"variable {name!r} may be used before being initialized",
                warning=True
            )

    def mark_assigned(self, node, name: str):
        info = touch_variable(self.scope, name)
        info.assigned = True
        info.initialized = True

        if not info.declared:
            print_node_error(
                self.parser,
                node,
                message=f"assignment to undeclared variable {name!r}"
            )
            self.parser.has_error = True

    def visit(self, node):
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
            self.enter_scope(node.name, "program")
            self.visit(node.statements)
            self.warn_unused_variables()
            self.leave_scope()
            return

        if isinstance(node, ast.Subroutine):
            self.enter_scope(node.name, "subroutine")

            for arg in node.arguments:
                self.declare_argument(arg)

            self.visit(node.statements)
            self.warn_unused_variables()
            self.leave_scope()
            return

        if isinstance(node, ast.Function):
            self.enter_scope(node.name, "function")

            # Function name is the return variable.
            info = touch_variable(self.scope, node.name)
            info.declared = True
            info.assigned = False
            info.type_name = node.return_type

            for arg in node.arguments:
                self.declare_argument(arg)

            self.visit(node.statements)
            self.warn_unused_variables()
            self.leave_scope()
            return

        if isinstance(node, ast.Label):
            self.visit(node.statement)
            return

        if isinstance(node, ast.Declare):
            for declarator in node.declarators:
                if isinstance(declarator, ast.VarDeclarator):
                    self.declare(
                        declarator,
                        declarator.name,
                        node.type_name,
                    )

                elif isinstance(declarator, ast.ArrayDeclarator):
                    self.declare(
                        declarator,
                        declarator.name,
                        node.type_name,
                        is_array=True,
                    )

                    # Array dimensions can use variables.
                    for dim in declarator.dimensions:
                        self.visit_expression(dim)
            return

        if isinstance(node, ast.Assign):
            self.visit_assignment_target(node.target)
            self.visit_expression(node.value)
            return

        if isinstance(node, ast.Read):
            for var in node.variables:
                self.visit_assignment_target(var)
            return

        if isinstance(node, ast.Print):
            for item in node.items:
                self.visit_expression(item)
            return

        if isinstance(node, ast.Write):
            for item in node.items:
                self.visit_expression(item)
            return

        if isinstance(node, ast.If):
            self.visit_expression(node.condition)
            self.visit(node.then_branch)
            if node.else_branch is not None:
                self.visit(node.else_branch)
            return

        if isinstance(node, ast.Do):
            # Loop variable is assigned/updated by the loop.
            loop_var = ast.Var(node.variable)
            self.mark_assigned(loop_var, node.variable)

            self.visit_expression(node.start)
            self.visit_expression(node.end)
            return

        if isinstance(node, ast.CallStatement):
            for arg in node.arguments:
                self.visit_expression(arg)
            return

        if isinstance(node, (ast.Goto, ast.Stop, ast.Return, ast.Continue)):
            return

        raise RuntimeError(f"unsupported AST node in variable checker: {node!r}")

    def visit_assignment_target(self, node):
        if isinstance(node, ast.Var):
            self.mark_assigned(node, node.name)
            return

        if isinstance(node, ast.ArrayRef):
            self.mark_assigned(node, node.name)

            for index in node.indices:
                self.visit_expression(index)
            return

        raise RuntimeError(f"invalid assignment target: {node!r}")

    def visit_expression(self, node):
        if isinstance(node, ast.Var):
            self.mark_used(node, node.name)
            return

        if isinstance(node, ast.ArrayRef):
            self.mark_used(node, node.name)

            for index in node.indices:
                self.visit_expression(index)
            return

        if isinstance(node, (ast.Integer, ast.Real, ast.Double, ast.String, ast.Bool)):
            return

        if isinstance(node, ast.Arith):
            self.visit_expression(node.left)
            self.visit_expression(node.right)
            return

        if isinstance(node, ast.Rel):
            self.visit_expression(node.left)
            self.visit_expression(node.right)
            return

        if isinstance(node, ast.Logical):
            self.visit_expression(node.left)
            self.visit_expression(node.right)
            return

        if isinstance(node, ast.Unary):
            self.visit_expression(node.value)
            return

        if isinstance(node, ast.IndexedOrCall):
            info = self.scope.variables.get(node.name) if self.scope else None

            if info is not None and info.is_array:
                self.mark_used(node, node.name)

            for argument in node.arguments:
                self.visit_expression(argument)

            return

        if isinstance(node, ast.Call):
            for arg in node.arguments:
                self.visit_expression(arg)
            return

        raise RuntimeError(f"unsupported expression in variable checker: {node!r}")

    def warn_unused_variables(self):
        for info in self.scope.variables.values():
            if info.declared and not info.used and not info.is_argument:
                node = info.declaration_node

                if node is not None:
                    print_node_error(
                        self.parser,
                        node,
                        message=f"variable {info.name!r} declared but never used",
                        warning=True,
                    )


def check_variables(parser, tree) -> SemanticInfo:
    checker = VariableChecker(parser)
    return checker.check(tree)
