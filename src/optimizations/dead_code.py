from __future__ import annotations

from dataclasses import replace

import abstract_syntax_tree as ast
from abstract_syntax_tree import AST


def dead_code_elimination(tree: AST) -> AST:
    """
    Remove code that cannot affect program output.

    Optimizations:
        - Remove unreachable code after STOP, RETURN, and GOTO.
        - Replace IF statements with constant conditions by the selected branch.
        - Remove unused labels.
        - Remove unused function/subroutine program units.
        - Remove dead assignments to variables that are never read.
        - Remove declarations for variables that no longer appear.

    Notes:
        - This pass is conservative around labels.
        - This pass does not remove READ statements, even if the target is not
          later used, because removing READ changes input consumption.
        - Function calls are treated as potentially effectful, so expressions
          containing calls are not removed as dead stores.
    """

    eliminator = DeadCodeEliminator()
    return eliminator.visit(tree)


class DeadCodeEliminator:
    ###
    # Entry points
    ###

    def visit(self, node):
        if node is None:
            return None

        if isinstance(node, list):
            return self.optimize_statement_list(node)

        if isinstance(node, ast.File):
            program_units = [
                self.visit_program_unit(unit)
                for unit in node.program_units
            ]

            return replace(
                node,
                program_units=self.remove_unused_program_units(program_units),
            )

        return self.visit_program_unit(node)

    def visit_program_unit(self, node):
        if isinstance(node, ast.Program):
            statements = self.optimize_statement_list(node.statements)
            optimized = replace(node, statements=statements)
            optimized = self.remove_unused_variables(optimized)
            statements = self.optimize_statement_list(optimized.statements)
            return replace(optimized, statements=statements)

        if isinstance(node, ast.Subroutine):
            statements = self.optimize_statement_list(node.statements)
            optimized = replace(node, statements=statements)
            optimized = self.remove_unused_variables(optimized)
            statements = self.optimize_statement_list(optimized.statements)
            return replace(optimized, statements=statements)

        if isinstance(node, ast.Function):
            statements = self.optimize_statement_list(node.statements)
            optimized = replace(node, statements=statements)
            optimized = self.remove_unused_variables(optimized)
            statements = self.optimize_statement_list(optimized.statements)
            return replace(optimized, statements=statements)

        raise RuntimeError(
            f"unsupported program unit in dead code elimination: {node!r}"
        )

    def optimize_statement_list(self, statements):
        optimized = []

        for statement in statements:
            result = self.visit_statement(statement)

            if isinstance(result, list):
                optimized.extend(result)
            elif result is not None:
                optimized.append(result)

        optimized = self.remove_unreachable_code(optimized)
        optimized = self.remove_unused_labels(optimized)

        return optimized

    ###
    # Statement rewriting
    ###

    def visit_statement(self, node):
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
            inner = self.visit_statement(node.statement)

            if isinstance(inner, list):
                if not inner:
                    return ast.Label(node.number, ast.Continue())

                return [
                    ast.Label(node.number, inner[0]),
                    *inner[1:],
                ]

            return replace(node, statement=inner)

        if isinstance(node, ast.If):
            condition = self.visit_expression(node.condition)
            then_branch = self.optimize_statement_list(node.then_branch)
            else_branch = (
                self.optimize_statement_list(node.else_branch)
                if node.else_branch is not None
                else None
            )

            if isinstance(condition, ast.Bool):
                if condition.value:
                    return then_branch

                return else_branch if else_branch is not None else []

            return replace(
                node,
                condition=condition,
                then_branch=then_branch,
                else_branch=else_branch,
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
            f"unsupported statement in dead code elimination: {node!r}"
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
            f"unsupported declarator in dead code elimination: {node!r}"
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
            f"unsupported variable in dead code elimination: {node!r}"
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
            return replace(
                node,
                value=self.visit_expression(node.value),
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

        raise RuntimeError(
            f"unsupported expression in dead code elimination: {node!r}"
        )

    ###
    # Unreachable code
    ###

    def remove_unreachable_code(self, statements):
        label_references = self.collect_label_references_from_statements(
            statements
        )

        result = []
        unreachable = False

        for statement in statements:
            if (
                isinstance(statement, ast.Label)
                and statement.number in label_references
            ):
                unreachable = False

            if unreachable:
                continue

            result.append(statement)

            if self.statement_always_terminates(statement):
                unreachable = True

        return result

    def statement_always_terminates(self, statement) -> bool:
        statement = self.unwrap_label(statement)

        if isinstance(statement, (ast.Stop, ast.Return, ast.Goto)):
            return True

        if isinstance(statement, ast.If):
            if statement.else_branch is None:
                return False

            return (
                self.statement_list_always_terminates(statement.then_branch)
                and self.statement_list_always_terminates(statement.else_branch)
            )

        return False

    def statement_list_always_terminates(self, statements) -> bool:
        if not statements:
            return False

        return self.statement_always_terminates(statements[-1])

    def unwrap_label(self, statement):
        while isinstance(statement, ast.Label):
            statement = statement.statement

        return statement

    ###
    # Label elimination
    ###

    def remove_unused_labels(self, statements):
        label_references = self.collect_label_references_from_statements(
            statements
        )

        return self.remove_unused_labels_from_statements(
            statements,
            label_references,
        )

    def remove_unused_labels_from_statements(self, statements, label_references):
        result = []

        for statement in statements:
            optimized = self.remove_unused_labels_from_statement(
                statement,
                label_references,
            )

            if isinstance(optimized, list):
                result.extend(optimized)
            else:
                result.append(optimized)

        return result

    def remove_unused_labels_from_statement(self, statement, label_references):
        if isinstance(statement, ast.Label):
            inner = self.remove_unused_labels_from_statement(
                statement.statement,
                label_references,
            )

            if isinstance(inner, list):
                if statement.number in label_references:
                    if not inner:
                        return ast.Label(statement.number, ast.Continue())

                    return [
                        ast.Label(statement.number, inner[0]),
                        *inner[1:],
                    ]

                return inner

            if statement.number in label_references:
                return replace(statement, statement=inner)

            return inner

        if isinstance(statement, ast.If):
            return replace(
                statement,
                then_branch=self.remove_unused_labels_from_statements(
                    statement.then_branch,
                    label_references,
                ),
                else_branch=(
                    self.remove_unused_labels_from_statements(
                        statement.else_branch,
                        label_references,
                    )
                    if statement.else_branch is not None
                    else None
                ),
            )

        return statement

    def collect_label_references_from_statements(self, statements):
        references = set()

        for statement in statements:
            references.update(
                self.collect_label_references_from_statement(statement)
            )

        return references

    def collect_label_references_from_statement(self, statement):
        if isinstance(statement, ast.Label):
            return self.collect_label_references_from_statement(
                statement.statement
            )

        if isinstance(statement, ast.Goto):
            return {statement.label}

        if isinstance(statement, ast.Do):
            return {statement.end_label}

        if isinstance(statement, ast.If):
            references = set()

            references.update(
                self.collect_label_references_from_statements(
                    statement.then_branch
                )
            )

            if statement.else_branch is not None:
                references.update(
                    self.collect_label_references_from_statements(
                        statement.else_branch
                    )
                )

            return references

        return set()

    ###
    # Unused procedure elimination
    ###

    def remove_unused_program_units(self, program_units):
        procedure_units = {
            unit.name.upper(): unit
            for unit in program_units
            if isinstance(unit, (ast.Subroutine, ast.Function))
        }

        reachable = set()
        worklist = []

        for unit in program_units:
            if isinstance(unit, ast.Program):
                worklist.extend(self.collect_calls_from_statements(
                    unit.statements
                ))

        while worklist:
            name = worklist.pop().upper()

            if name in reachable:
                continue

            procedure = procedure_units.get(name)

            if procedure is None:
                continue

            reachable.add(name)
            worklist.extend(
                self.collect_calls_from_statements(procedure.statements)
            )

        result = []

        for unit in program_units:
            if isinstance(unit, ast.Program):
                result.append(unit)
                continue

            if unit.name.upper() in reachable:
                result.append(unit)

        return result

    def collect_calls_from_statements(self, statements):
        calls = set()

        for statement in statements:
            calls.update(self.collect_calls_from_statement(statement))

        return calls

    def collect_calls_from_statement(self, statement):
        if isinstance(statement, ast.Label):
            return self.collect_calls_from_statement(statement.statement)

        if isinstance(statement, ast.Assign):
            return self.collect_calls_from_expression(statement.value)

        if isinstance(statement, ast.Print):
            return self.collect_calls_from_expressions(statement.items)

        if isinstance(statement, ast.Write):
            return self.collect_calls_from_expressions(statement.items)

        if isinstance(statement, ast.Read):
            return set()

        if isinstance(statement, ast.If):
            calls = self.collect_calls_from_expression(statement.condition)
            calls.update(self.collect_calls_from_statements(
                statement.then_branch
            ))

            if statement.else_branch is not None:
                calls.update(self.collect_calls_from_statements(
                    statement.else_branch
                ))

            return calls

        if isinstance(statement, ast.Do):
            calls = self.collect_calls_from_expression(statement.start)
            calls.update(self.collect_calls_from_expression(statement.end))

            if statement.step is not None:
                calls.update(self.collect_calls_from_expression(statement.step))

            return calls

        if isinstance(statement, ast.CallStatement):
            calls = {statement.name.upper()}
            calls.update(self.collect_calls_from_expressions(
                statement.arguments
            ))
            return calls

        return set()

    def collect_calls_from_expressions(self, expressions):
        calls = set()

        for expression in expressions:
            calls.update(self.collect_calls_from_expression(expression))

        return calls

    def collect_calls_from_expression(self, expression):
        if isinstance(expression, ast.Call):
            calls = {expression.name.upper()}
            calls.update(
                self.collect_calls_from_expressions(expression.arguments)
            )
            return calls

        if isinstance(expression, ast.ArrayRef):
            return self.collect_calls_from_expressions(expression.indices)

        if isinstance(expression, ast.Unary):
            return self.collect_calls_from_expression(expression.value)

        if isinstance(expression, ast.Arith):
            calls = self.collect_calls_from_expression(expression.left)
            calls.update(self.collect_calls_from_expression(expression.right))
            return calls

        if isinstance(expression, ast.Rel):
            calls = self.collect_calls_from_expression(expression.left)
            calls.update(self.collect_calls_from_expression(expression.right))
            return calls

        if isinstance(expression, ast.Logical):
            calls = self.collect_calls_from_expression(expression.left)
            calls.update(self.collect_calls_from_expression(expression.right))
            return calls

        if isinstance(expression, ast.IndexedOrCall):
            calls = {expression.name.upper()}
            calls.update(
                self.collect_calls_from_expressions(expression.arguments)
            )
            return calls

        return set()

    ###
    # Unused variable and dead assignment elimination
    ###

    def remove_unused_variables(self, unit):
        protected_names = self.protected_variable_names(unit)
        statements = unit.statements

        while True:
            value_uses = self.collect_value_uses_from_statements(statements)
            protected = protected_names | self.collect_read_targets(statements)

            statements_without_dead_assignments = (
                self.remove_dead_assignments_from_statements(
                    statements,
                    value_uses | protected,
                    protected,
                )
            )

            references = self.collect_variable_references_from_statements(
                statements_without_dead_assignments
            ) | protected

            cleaned = self.remove_unused_declarations_from_statements(
                statements_without_dead_assignments,
                references,
                self.collect_label_references_from_statements(
                    statements_without_dead_assignments
                ),
            )

            if cleaned == statements:
                break

            statements = cleaned

        return replace(unit, statements=statements)

    def protected_variable_names(self, unit):
        names = set()

        if isinstance(unit, (ast.Subroutine, ast.Function)):
            names.update(name.upper() for name in unit.arguments)

        if isinstance(unit, ast.Function):
            names.add(unit.name.upper())

        return names

    def collect_read_targets(self, statements):
        targets = set()

        for statement in statements:
            targets.update(self.collect_read_targets_from_statement(statement))

        return targets

    def collect_read_targets_from_statement(self, statement):
        if isinstance(statement, ast.Label):
            return self.collect_read_targets_from_statement(statement.statement)

        if isinstance(statement, ast.Read):
            return {
                self.variable_base_name(variable)
                for variable in statement.variables
            }

        if isinstance(statement, ast.If):
            targets = self.collect_read_targets(statement.then_branch)

            if statement.else_branch is not None:
                targets.update(self.collect_read_targets(statement.else_branch))

            return targets

        return set()

    def remove_dead_assignments_from_statements(
        self,
        statements,
        live_names,
        protected_names,
    ):
        result = []

        for statement in statements:
            optimized = self.remove_dead_assignments_from_statement(
                statement,
                live_names,
                protected_names,
            )

            if isinstance(optimized, list):
                result.extend(optimized)
            elif optimized is not None:
                result.append(optimized)

        return result

    def remove_dead_assignments_from_statement(
        self,
        statement,
        live_names,
        protected_names,
    ):
        if isinstance(statement, ast.Label):
            inner = self.remove_dead_assignments_from_statement(
                statement.statement,
                live_names,
                protected_names,
            )

            if inner is None:
                return ast.Label(statement.number, ast.Continue())

            if isinstance(inner, list):
                if not inner:
                    return ast.Label(statement.number, ast.Continue())

                return [
                    ast.Label(statement.number, inner[0]),
                    *inner[1:],
                ]

            return replace(statement, statement=inner)

        if isinstance(statement, ast.Assign):
            target_name = self.variable_base_name(statement.target)

            if (
                target_name not in live_names
                and target_name not in protected_names
                and self.is_side_effect_free(statement.target)
                and self.is_side_effect_free(statement.value)
            ):
                return None

            return statement

        if isinstance(statement, ast.If):
            return replace(
                statement,
                then_branch=self.remove_dead_assignments_from_statements(
                    statement.then_branch,
                    live_names,
                    protected_names,
                ),
                else_branch=(
                    self.remove_dead_assignments_from_statements(
                        statement.else_branch,
                        live_names,
                        protected_names,
                    )
                    if statement.else_branch is not None
                    else None
                ),
            )

        return statement

    def remove_unused_declarations_from_statements(
        self,
        statements,
        references,
        label_references,
    ):
        result = []

        for statement in statements:
            optimized = self.remove_unused_declarations_from_statement(
                statement,
                references,
                label_references,
            )

            if isinstance(optimized, list):
                result.extend(optimized)
            elif optimized is not None:
                result.append(optimized)

        return result

    def remove_unused_declarations_from_statement(
        self,
        statement,
        references,
        label_references,
    ):
        if isinstance(statement, ast.Label):
            inner = self.remove_unused_declarations_from_statement(
                statement.statement,
                references,
                label_references,
            )

            if inner is None:
                if statement.number in label_references:
                    return ast.Label(statement.number, ast.Continue())

                return None

            if isinstance(inner, list):
                if statement.number in label_references:
                    if not inner:
                        return ast.Label(statement.number, ast.Continue())

                    return [
                        ast.Label(statement.number, inner[0]),
                        *inner[1:],
                    ]

                return inner

            if statement.number in label_references:
                return replace(statement, statement=inner)

            return inner

        if isinstance(statement, ast.Declare):
            declarators = [
                declarator
                for declarator in statement.declarators
                if self.declarator_name(declarator) in references
            ]

            if not declarators:
                return None

            return replace(statement, declarators=declarators)

        if isinstance(statement, ast.If):
            return replace(
                statement,
                then_branch=self.remove_unused_declarations_from_statements(
                    statement.then_branch,
                    references,
                    label_references,
                ),
                else_branch=(
                    self.remove_unused_declarations_from_statements(
                        statement.else_branch,
                        references,
                        label_references,
                    )
                    if statement.else_branch is not None
                    else None
                ),
            )

        return statement

    ###
    # Variable reference collection
    ###

    def collect_value_uses_from_statements(self, statements):
        uses = set()

        for statement in statements:
            uses.update(self.collect_value_uses_from_statement(statement))

        return uses

    def collect_value_uses_from_statement(self, statement):
        if isinstance(statement, ast.Label):
            return self.collect_value_uses_from_statement(statement.statement)

        if isinstance(statement, ast.Declare):
            return self.collect_value_uses_from_declarators(
                statement.declarators
            )

        if isinstance(statement, ast.Assign):
            uses = self.collect_value_uses_from_expression(statement.value)

            if isinstance(statement.target, ast.ArrayRef):
                uses.update(self.collect_value_uses_from_expressions(
                    statement.target.indices
                ))

            return uses

        if isinstance(statement, ast.Print):
            return self.collect_value_uses_from_expressions(statement.items)

        if isinstance(statement, ast.Write):
            return self.collect_value_uses_from_expressions(statement.items)

        if isinstance(statement, ast.Read):
            uses = set()

            for variable in statement.variables:
                if isinstance(variable, ast.ArrayRef):
                    uses.update(self.collect_value_uses_from_expressions(
                        variable.indices
                    ))

            return uses

        if isinstance(statement, ast.If):
            uses = self.collect_value_uses_from_expression(statement.condition)
            uses.update(self.collect_value_uses_from_statements(
                statement.then_branch
            ))

            if statement.else_branch is not None:
                uses.update(self.collect_value_uses_from_statements(
                    statement.else_branch
                ))

            return uses

        if isinstance(statement, ast.Do):
            uses = {statement.variable.name.upper()}
            uses.update(self.collect_value_uses_from_expression(
                statement.start
            ))
            uses.update(self.collect_value_uses_from_expression(statement.end))

            if statement.step is not None:
                uses.update(self.collect_value_uses_from_expression(
                    statement.step
                ))

            return uses

        if isinstance(statement, ast.CallStatement):
            return self.collect_value_uses_from_expressions(
                statement.arguments
            )

        return set()

    def collect_value_uses_from_declarators(self, declarators):
        uses = set()

        for declarator in declarators:
            if isinstance(declarator, ast.ArrayDeclarator):
                uses.update(self.collect_value_uses_from_expressions(
                    declarator.dimensions
                ))

        return uses

    def collect_value_uses_from_expressions(self, expressions):
        uses = set()

        for expression in expressions:
            uses.update(self.collect_value_uses_from_expression(expression))

        return uses

    def collect_value_uses_from_expression(self, expression):
        if isinstance(expression, ast.Var):
            return {expression.name.upper()}

        if isinstance(expression, ast.ArrayRef):
            uses = {expression.name.upper()}
            uses.update(self.collect_value_uses_from_expressions(
                expression.indices
            ))
            return uses

        if isinstance(expression, ast.Call):
            return self.collect_value_uses_from_expressions(
                expression.arguments
            )

        if isinstance(expression, ast.IndexedOrCall):
            uses = {expression.name.upper()}
            uses.update(self.collect_value_uses_from_expressions(
                expression.arguments
            ))
            return uses

        if isinstance(expression, ast.Unary):
            return self.collect_value_uses_from_expression(expression.value)

        if isinstance(expression, ast.Arith):
            uses = self.collect_value_uses_from_expression(expression.left)
            uses.update(self.collect_value_uses_from_expression(
                expression.right
            ))
            return uses

        if isinstance(expression, ast.Rel):
            uses = self.collect_value_uses_from_expression(expression.left)
            uses.update(self.collect_value_uses_from_expression(
                expression.right
            ))
            return uses

        if isinstance(expression, ast.Logical):
            uses = self.collect_value_uses_from_expression(expression.left)
            uses.update(self.collect_value_uses_from_expression(
                expression.right
            ))
            return uses

        return set()

    def collect_variable_references_from_statements(self, statements):
        references = set()

        for statement in statements:
            references.update(
                self.collect_variable_references_from_statement(statement)
            )

        return references

    def collect_variable_references_from_statement(self, statement):
        if isinstance(statement, ast.Label):
            return self.collect_variable_references_from_statement(
                statement.statement
            )

        if isinstance(statement, ast.Declare):
            references = set()

            for declarator in statement.declarators:
                references.add(self.declarator_name(declarator))

                if isinstance(declarator, ast.ArrayDeclarator):
                    references.update(
                        self.collect_value_uses_from_expressions(
                            declarator.dimensions
                        )
                    )

            return references

        if isinstance(statement, ast.Assign):
            references = {self.variable_base_name(statement.target)}
            references.update(self.collect_value_uses_from_expression(
                statement.value
            ))

            if isinstance(statement.target, ast.ArrayRef):
                references.update(self.collect_value_uses_from_expressions(
                    statement.target.indices
                ))

            return references

        if isinstance(statement, ast.Read):
            references = {
                self.variable_base_name(variable)
                for variable in statement.variables
            }

            for variable in statement.variables:
                if isinstance(variable, ast.ArrayRef):
                    references.update(self.collect_value_uses_from_expressions(
                        variable.indices
                    ))

            return references

        if isinstance(statement, ast.Print):
            return self.collect_value_uses_from_expressions(statement.items)

        if isinstance(statement, ast.Write):
            return self.collect_value_uses_from_expressions(statement.items)

        if isinstance(statement, ast.If):
            references = self.collect_value_uses_from_expression(
                statement.condition
            )
            references.update(self.collect_variable_references_from_statements(
                statement.then_branch
            ))

            if statement.else_branch is not None:
                references.update(
                    self.collect_variable_references_from_statements(
                        statement.else_branch
                    )
                )

            return references

        if isinstance(statement, ast.Do):
            references = {statement.variable.name.upper()}
            references.update(self.collect_value_uses_from_expression(
                statement.start
            ))
            references.update(self.collect_value_uses_from_expression(
                statement.end
            ))

            if statement.step is not None:
                references.update(self.collect_value_uses_from_expression(
                    statement.step
                ))

            return references

        if isinstance(statement, ast.CallStatement):
            return self.collect_value_uses_from_expressions(
                statement.arguments
            )

        return set()

    ###
    # Side-effect helpers
    ###

    def is_side_effect_free(self, node) -> bool:
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
    # Small helpers
    ###

    def variable_base_name(self, node) -> str:
        if isinstance(node, ast.Var):
            return node.name.upper()

        if isinstance(node, ast.ArrayRef):
            return node.name.upper()

        raise RuntimeError(f"unsupported variable target: {node!r}")

    def declarator_name(self, node) -> str:
        if isinstance(node, ast.VarDeclarator):
            return node.name.upper()

        if isinstance(node, ast.ArrayDeclarator):
            return node.name.upper()

        raise RuntimeError(f"unsupported declarator: {node!r}")
