from __future__ import annotations

import copy
from dataclasses import replace
from typing import Optional

import abstract_syntax_tree as ast
from abstract_syntax_tree import AST


DEFAULT_VECTOR_SIZE = 4
MAX_VECTORIZED_ITERATIONS = 256


def vectorization(
    tree: AST,
    *,
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> AST:
    """
    Vectorize simple compile-time bounded labelled DO loops.

    This is a source-level loop vectorization/unrolling transform for the
    current AST representation, where a labelled DO loop is encoded as a flat
    statement region:

        DO 100 I = 1, 10, S
          BODY(I)
    100 CONTINUE

    With vector_size = 4, this becomes:

        DO 100 I = 1, MAIN_END, 4*S
          BODY(I)
          BODY(I + S)
          BODY(I + 2*S)
          BODY(I + 3*S)
    100 CONTINUE

        BODY(I)          ! remainder 0
        BODY(I + S)      ! remainder 1
        ...

    The transform is conservative and only applies when:
        - loop bounds are compile-time integer constants;
        - the step is omitted or a positive compile-time integer constant;
        - the trip count is at least vector_size;
        - the loop body has no labels, GOTO, nested DO, STOP, or RETURN;
        - the loop body does not assign to the loop variable;
        - no GOTO targets the loop's terminal CONTINUE label.

    Notes:
        - This pass preserves the original loop variable final value produced
          by the current positive-step DO code generator.
        - This is not SIMD EWVM code generation. It is AST-level vector-style
          loop expansion that reduces loop-control overhead.
    """

    vectorizer = LoopVectorizer(vector_size=vector_size)
    return vectorizer.visit(tree)


class LoopVectorizer:
    def __init__(self, *, vector_size: int):
        if vector_size < 2:
            raise ValueError("vector_size must be >= 2")

        self.vector_size = vector_size

    ###
    # Entry points
    ###

    def visit(self, node):
        if node is None:
            return None

        if isinstance(node, list):
            return self.visit_statement_list(node)

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
                statements=self.visit_statement_list(node.statements),
            )

        if isinstance(node, ast.Subroutine):
            return replace(
                node,
                statements=self.visit_statement_list(node.statements),
            )

        if isinstance(node, ast.Function):
            return replace(
                node,
                statements=self.visit_statement_list(node.statements),
            )

        if isinstance(node, ast.Block):
            return replace(
                node,
                statements=self.visit_statement_list(node.statements),
            )

        raise RuntimeError(f"unsupported AST node in vectorization: {node!r}")

    def visit_statement_list(self, statements):
        result = []
        i = 0

        while i < len(statements):
            statement = statements[i]

            if isinstance(statement, ast.Do):
                end_index = self.find_do_end_index(
                    statements,
                    start_index=i,
                    end_label=statement.end_label,
                )

                if end_index is not None:
                    body = statements[i + 1:end_index]
                    end_statement = statements[end_index]

                    optimized_body = self.visit_statement_list(body)

                    if self.can_vectorize_loop(
                        loop=statement,
                        body=optimized_body,
                        surrounding_statements=statements,
                    ):
                        result.extend(
                            self.vectorize_loop(
                                loop=statement,
                                body=optimized_body,
                                end_statement=end_statement,
                            )
                        )
                    else:
                        result.append(self.visit_do(statement))
                        result.extend(optimized_body)
                        result.append(self.visit_statement(end_statement))

                    i = end_index + 1
                    continue

            visited = self.visit_statement(statement)

            if isinstance(visited, list):
                result.extend(visited)
            elif visited is not None:
                result.append(visited)

            i += 1

        return result

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
            return replace(
                node,
                statement=self.visit_statement(node.statement),
            )

        if isinstance(node, ast.If):
            return replace(
                node,
                condition=self.visit_expression(node.condition),
                then_branch=self.visit_statement_list(node.then_branch),
                else_branch=(
                    self.visit_statement_list(node.else_branch)
                    if node.else_branch is not None
                    else None
                ),
            )

        if isinstance(node, ast.Do):
            return self.visit_do(node)

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

        raise RuntimeError(f"unsupported statement in vectorization: {node!r}")

    def visit_do(self, node):
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

        raise RuntimeError(f"unsupported declarator in vectorization: {node!r}")

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

        raise RuntimeError(f"unsupported variable in vectorization: {node!r}")

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

        raise RuntimeError(f"unsupported expression in vectorization: {node!r}")

    ###
    # DO-region discovery
    ###

    def find_do_end_index(self, statements, *, start_index: int, end_label: int):
        """
        Find the matching labelled CONTINUE for a DO statement.

        The current parser represents DO loops as:
            ast.Do(...)
            body statements...
            ast.Label(end_label, ast.Continue())
        """

        for i in range(start_index + 1, len(statements)):
            statement = statements[i]

            if (
                isinstance(statement, ast.Label)
                and statement.number == end_label
                and isinstance(statement.statement, ast.Continue)
            ):
                return i

        return None

    ###
    # Applicability checks
    ###

    def can_vectorize_loop(
        self,
        *,
        loop: ast.Do,
        body,
        surrounding_statements,
    ) -> bool:
        loop_info = self.loop_info(loop)

        if loop_info is None:
            return False

        trip_count = loop_info["trip_count"]

        if trip_count < self.vector_size:
            return False

        if trip_count > MAX_VECTORIZED_ITERATIONS:
            return False

        if self.has_goto_to_label(surrounding_statements, loop.end_label):
            return False

        if not self.body_is_safe_to_duplicate(body, loop.variable.name):
            return False

        return True

    def loop_info(self, loop: ast.Do) -> Optional[dict[str, int]]:
        if not isinstance(loop.start, ast.Integer):
            return None

        if not isinstance(loop.end, ast.Integer):
            return None

        step = 1

        if loop.step is not None:
            if not isinstance(loop.step, ast.Integer):
                return None

            if loop.step.value <= 0:
                return None

            step = loop.step.value

        start = loop.start.value
        end = loop.end.value

        if start > end:
            return None

        trip_count = ((end - start) // step) + 1

        return {
            "start": start,
            "end": end,
            "step": step,
            "trip_count": trip_count,
        }

    def body_is_safe_to_duplicate(self, statements, loop_variable_name: str) -> bool:
        loop_variable_name = loop_variable_name.upper()

        for statement in statements:
            if not self.statement_is_safe_to_duplicate(
                statement,
                loop_variable_name,
            ):
                return False

        return True

    def statement_is_safe_to_duplicate(
        self,
        statement,
        loop_variable_name: str,
    ) -> bool:
        if isinstance(statement, ast.Label):
            return False

        if isinstance(statement, (ast.Goto, ast.Do, ast.Stop, ast.Return)):
            return False

        if isinstance(statement, ast.Declare):
            return False

        if isinstance(statement, ast.Assign):
            if self.variable_base_name(statement.target) == loop_variable_name:
                return False

            return True

        if isinstance(statement, ast.Read):
            for variable in statement.variables:
                if self.variable_base_name(variable) == loop_variable_name:
                    return False

            return True

        if isinstance(statement, ast.If):
            return (
                self.body_is_safe_to_duplicate(
                    statement.then_branch,
                    loop_variable_name,
                )
                and (
                    statement.else_branch is None
                    or self.body_is_safe_to_duplicate(
                        statement.else_branch,
                        loop_variable_name,
                    )
                )
            )

        if isinstance(statement, (
            ast.Print,
            ast.Write,
            ast.CallStatement,
            ast.Continue,
        )):
            return True

        return False

    def has_goto_to_label(self, statements, label: int) -> bool:
        for statement in statements:
            if self.statement_has_goto_to_label(statement, label):
                return True

        return False

    def statement_has_goto_to_label(self, statement, label: int) -> bool:
        if isinstance(statement, ast.Label):
            return self.statement_has_goto_to_label(statement.statement, label)

        if isinstance(statement, ast.Goto):
            return statement.label == label

        if isinstance(statement, ast.If):
            if self.has_goto_to_label(statement.then_branch, label):
                return True

            if (
                statement.else_branch is not None
                and self.has_goto_to_label(statement.else_branch, label)
            ):
                return True

        return False

    ###
    # Vectorization
    ###

    def vectorize_loop(self, *, loop: ast.Do, body, end_statement):
        info = self.loop_info(loop)

        if info is None:
            return [
                self.visit_do(loop),
                *body,
                self.visit_statement(end_statement),
            ]

        start = info["start"]
        step = info["step"]
        trip_count = info["trip_count"]

        full_chunks = trip_count // self.vector_size
        remainder = trip_count % self.vector_size

        if full_chunks == 0:
            return [
                self.visit_do(loop),
                *body,
                self.visit_statement(end_statement),
            ]

        main_loop_end = start + ((full_chunks - 1) * self.vector_size * step)
        vector_step = step * self.vector_size

        vectorized_loop = replace(
            loop,
            start=ast.Integer(start, loop.start.location),
            end=ast.Integer(main_loop_end, loop.end.location),
            step=ast.Integer(
                vector_step,
                loop.step.location if loop.step is not None else loop.variable.location,
            ),
        )

        result = [vectorized_loop]

        for offset_index in range(self.vector_size):
            offset = offset_index * step
            result.extend(
                self.body_with_loop_offset(
                    body,
                    loop.variable.name,
                    offset,
                )
            )

        result.append(self.visit_statement(end_statement))

        for offset_index in range(remainder):
            offset = offset_index * step
            result.extend(
                self.body_with_loop_offset(
                    body,
                    loop.variable.name,
                    offset,
                )
            )

        return result

    def body_with_loop_offset(self, body, loop_variable_name: str, offset: int):
        return [
            self.statement_with_loop_offset(
                copy.deepcopy(statement),
                loop_variable_name,
                offset,
            )
            for statement in body
        ]

    def statement_with_loop_offset(
        self,
        statement,
        loop_variable_name: str,
        offset: int,
    ):
        if isinstance(statement, ast.Assign):
            return replace(
                statement,
                target=self.variable_with_loop_offset(
                    statement.target,
                    loop_variable_name,
                    offset,
                ),
                value=self.expression_with_loop_offset(
                    statement.value,
                    loop_variable_name,
                    offset,
                ),
            )

        if isinstance(statement, ast.Print):
            return replace(
                statement,
                items=[
                    self.expression_with_loop_offset(
                        item,
                        loop_variable_name,
                        offset,
                    )
                    for item in statement.items
                ],
            )

        if isinstance(statement, ast.Write):
            return replace(
                statement,
                items=[
                    self.expression_with_loop_offset(
                        item,
                        loop_variable_name,
                        offset,
                    )
                    for item in statement.items
                ],
            )

        if isinstance(statement, ast.Read):
            return replace(
                statement,
                variables=[
                    self.variable_with_loop_offset(
                        variable,
                        loop_variable_name,
                        offset,
                    )
                    for variable in statement.variables
                ],
            )

        if isinstance(statement, ast.If):
            return replace(
                statement,
                condition=self.expression_with_loop_offset(
                    statement.condition,
                    loop_variable_name,
                    offset,
                ),
                then_branch=[
                    self.statement_with_loop_offset(
                        branch_statement,
                        loop_variable_name,
                        offset,
                    )
                    for branch_statement in statement.then_branch
                ],
                else_branch=(
                    [
                        self.statement_with_loop_offset(
                            branch_statement,
                            loop_variable_name,
                            offset,
                        )
                        for branch_statement in statement.else_branch
                    ]
                    if statement.else_branch is not None
                    else None
                ),
            )

        if isinstance(statement, ast.CallStatement):
            return replace(
                statement,
                arguments=[
                    self.expression_with_loop_offset(
                        argument,
                        loop_variable_name,
                        offset,
                    )
                    for argument in statement.arguments
                ],
            )

        if isinstance(statement, ast.Continue):
            return statement

        raise RuntimeError(
            f"unsupported statement during loop vectorization: {statement!r}"
        )

    def variable_with_loop_offset(
        self,
        variable,
        loop_variable_name: str,
        offset: int,
    ):
        if isinstance(variable, ast.Var):
            return variable

        if isinstance(variable, ast.ArrayRef):
            return replace(
                variable,
                indices=[
                    self.expression_with_loop_offset(
                        index,
                        loop_variable_name,
                        offset,
                    )
                    for index in variable.indices
                ],
            )

        raise RuntimeError(
            f"unsupported variable during loop vectorization: {variable!r}"
        )

    def expression_with_loop_offset(
        self,
        expression,
        loop_variable_name: str,
        offset: int,
    ):
        if isinstance(expression, ast.Var):
            if expression.name.upper() == loop_variable_name.upper():
                return self.offset_loop_variable(expression, offset)

            return expression

        if isinstance(expression, ast.ArrayRef):
            return replace(
                expression,
                indices=[
                    self.expression_with_loop_offset(
                        index,
                        loop_variable_name,
                        offset,
                    )
                    for index in expression.indices
                ],
            )

        if isinstance(expression, ast.Call):
            return replace(
                expression,
                arguments=[
                    self.expression_with_loop_offset(
                        argument,
                        loop_variable_name,
                        offset,
                    )
                    for argument in expression.arguments
                ],
            )

        if isinstance(expression, ast.IndexedOrCall):
            return replace(
                expression,
                arguments=[
                    self.expression_with_loop_offset(
                        argument,
                        loop_variable_name,
                        offset,
                    )
                    for argument in expression.arguments
                ],
            )

        if isinstance(expression, ast.Unary):
            return replace(
                expression,
                value=self.expression_with_loop_offset(
                    expression.value,
                    loop_variable_name,
                    offset,
                ),
            )

        if isinstance(expression, ast.Arith):
            return replace(
                expression,
                left=self.expression_with_loop_offset(
                    expression.left,
                    loop_variable_name,
                    offset,
                ),
                right=self.expression_with_loop_offset(
                    expression.right,
                    loop_variable_name,
                    offset,
                ),
            )

        if isinstance(expression, ast.Rel):
            return replace(
                expression,
                left=self.expression_with_loop_offset(
                    expression.left,
                    loop_variable_name,
                    offset,
                ),
                right=self.expression_with_loop_offset(
                    expression.right,
                    loop_variable_name,
                    offset,
                ),
            )

        if isinstance(expression, ast.Logical):
            return replace(
                expression,
                left=self.expression_with_loop_offset(
                    expression.left,
                    loop_variable_name,
                    offset,
                ),
                right=self.expression_with_loop_offset(
                    expression.right,
                    loop_variable_name,
                    offset,
                ),
            )

        if isinstance(expression, (
            ast.Integer,
            ast.Real,
            ast.Double,
            ast.String,
            ast.Bool,
        )):
            return expression

        raise RuntimeError(
            f"unsupported expression during loop vectorization: {expression!r}"
        )

    def offset_loop_variable(self, variable: ast.Var, offset: int):
        if offset == 0:
            return variable

        return ast.Arith(
            op="+",
            left=ast.Var(variable.name, variable.location),
            right=ast.Integer(offset, variable.location),
            location=variable.location,
        )

    ###
    # Small helpers
    ###

    def variable_base_name(self, node) -> str:
        if isinstance(node, ast.Var):
            return node.name.upper()

        if isinstance(node, ast.ArrayRef):
            return node.name.upper()

        raise RuntimeError(f"unsupported variable target: {node!r}")
