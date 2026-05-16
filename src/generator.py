#!/usr/bin/env python3

import abstract_syntax_tree as ast
from abstract_syntax_tree import AST
from semantics.semantic_info import SemanticInfo


class CodeGenerationError(Exception):
    pass


class EWVMEmitter:
    def __init__(self, *, debug: bool = False):
        self.debug = debug
        self.instructions: list[str] = []

    def emit(self, instruction: str) -> None:
        self.instructions.append(instruction)

    def new_line(self) -> None:
        if self.debug:
            self.emit("")

    def comment(self, text: str) -> None:
        if self.debug:
            self.emit(f"// {text}")

    def label(self, name: str) -> None:
        self.emit(f"{name}:")

    def render(self) -> str:
        return "\n".join(self.instructions) + "\n"

    @staticmethod
    def string_literal(value: str) -> str:
        escaped = (
            value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )

        return f"\"{escaped}\""


class MemoryLayout:
    def __init__(self):
        self.global_slots: dict[tuple[str, str, str], int] = {}
        self.arrays: set[tuple[str, str, str]] = set()

    def key(self, scope, name: str) -> tuple[str, str, str]:
        return (scope.kind, scope.name.upper(), name.upper())

    def allocate_global(self, scope, name: str) -> int:
        key = self.key(scope, name)

        if key not in self.global_slots:
            self.global_slots[key] = len(self.global_slots)

        return self.global_slots[key]

    def global_slot(self, scope, name: str) -> int:
        key = self.key(scope, name)

        try:
            return self.global_slots[key]
        except KeyError:
            raise CodeGenerationError(
                f"internal error: variable {name!r} has no slot "
                f"in {scope.kind} {scope.name!r}"
            )

    def mark_array(self, scope, name: str) -> None:
        self.arrays.add(self.key(scope, name))

    def is_array(self, scope, name: str) -> bool:
        return self.key(scope, name) in self.arrays


class ProcedureRegistry:
    def __init__(self):
        self.labels: dict[str, str] = {}

    def register_from_file(self, tree: ast.File) -> None:
        for unit in tree.program_units:
            if isinstance(unit, (ast.Subroutine, ast.Function)):
                name = unit.name.upper()
                self.labels[name] = f"P{len(self.labels)}"

    def label(self, name: str) -> str:
        try:
            return self.labels[name.upper()]
        except KeyError:
            raise CodeGenerationError(
                f"internal error: procedure {name!r} has no generated label"
            )


class DebugFormatter:
    def expression(self, node) -> str:
        if isinstance(node, ast.Integer):
            return str(node.value)

        if isinstance(node, ast.Real):
            return str(node.value)

        if isinstance(node, ast.Double):
            return str(node.value)

        if isinstance(node, ast.String):
            return repr(node.value)

        if isinstance(node, ast.Bool):
            return ".TRUE." if node.value else ".FALSE."

        if isinstance(node, ast.Var):
            return node.name

        if isinstance(node, ast.ArrayRef):
            return f"{node.name}(...)"

        if isinstance(node, ast.Call):
            return f"{node.name}(...)"

        if isinstance(node, ast.Arith):
            return (
                f"({self.expression(node.left)} "
                f"{node.op} "
                f"{self.expression(node.right)})"
            )

        if isinstance(node, ast.Rel):
            return (
                f"({self.expression(node.left)} "
                f"{node.op} "
                f"{self.expression(node.right)})"
            )

        if isinstance(node, ast.Logical):
            return (
                f"({self.expression(node.left)} "
                f"{node.op} "
                f"{self.expression(node.right)})"
            )

        if isinstance(node, ast.Unary):
            return f"({node.op} {self.expression(node.value)})"

        return type(node).__name__

    def statement(self, node) -> str:
        if isinstance(node, ast.Assign):
            return f"assignment to {self.expression(node.target)}"

        if isinstance(node, ast.Print):
            return "PRINT statement"

        if isinstance(node, ast.Write):
            return "WRITE statement"

        if isinstance(node, ast.Read):
            return "READ statement"

        if isinstance(node, ast.If):
            return "IF statement"

        if isinstance(node, ast.Label):
            return f"label {node.number}"

        if isinstance(node, ast.Goto):
            return f"GOTO {node.label}"

        if isinstance(node, ast.Stop):
            return "STOP statement"

        if isinstance(node, ast.Return):
            return "RETURN statement"

        if isinstance(node, ast.Continue):
            return "CONTINUE statement"

        if isinstance(node, ast.Do):
            return f"DO loop {node.variable.name} -> label {node.end_label}"

        if isinstance(node, ast.CallStatement):
            return f"CALL {node.name}"

        return type(node).__name__


INTEGER_ARITH_OPS = {
    "+": "ADD",
    "-": "SUB",
    "*": "MUL",
    "/": "DIV",
}

FLOAT_ARITH_OPS = {
    "+": "FADD",
    "-": "FSUB",
    "*": "FMUL",
    "/": "FDIV",
}


# TODO(codegen): Support multidimensional arrays.
# TODO(codegen): Support CHARACTER arrays/fixed-length strings.
# TODO(codegen): Support negative DO step termination logic.
# TODO(codegen): Support pass-by-reference procedure arguments.
# TODO(codegen): Support proper local stack-frame allocation.
# TODO(codegen): Support recursion-safe procedure calls.
# TODO(codegen): Support intrinsic function calls.
# TODO(codegen): Support power operator.
# TODO(codegen): Add bounds checks for array indices using CHECK.

class EWVMGenerator:

    ###
    # Construction / Entry point
    ###

    def __init__(self, semantic_info, *, debug: bool = False):
        self.semantic_info = semantic_info
        self.emitter = EWVMEmitter(debug=debug)
        self.layout = MemoryLayout()
        self.procedures = ProcedureRegistry()
        self.debug_formatter = DebugFormatter()
        self.current_scope = None
        self.loop_counter = 0
        self.pending_do_by_label = {}
        self.label_counter = 0

    def generate(self, tree) -> str:
        self.visit_file(tree)
        return self.emitter.render()

    ###
    # Semantic metadata lookup
    ###

    def find_scope(self, name: str, kind: str):
        for scope in self.semantic_info.scopes:
            if scope.name == name and scope.kind == kind:
                return scope
        raise CodeGenerationError(
            f"internal error: missing semantic scope {kind} {name}"
        )

    def procedure_info(self, name: str):
        info = self.semantic_info.procedures.get(name.upper())

        if info is None:
            raise CodeGenerationError(
                f"internal error: missing procedure info for {name!r}"
            )

        return info

    def variable_type(self, name: str) -> str:
        if self.current_scope is None:
            return "UNKNOWN"

        info = self.current_scope.variables.get(name)
        if info is None:
            return "UNKNOWN"

        return info.type_name

    def expression_type(self, node) -> str:
        return self.semantic_info.expression_types.get(id(node), "UNKNOWN")

    def expression_type_hint(self, node) -> str:
        return self.expression_type(node)

    def expression_is_floatish(self, node) -> bool:
        return self.expression_type(node) in {"REAL", "DOUBLE"}

    ###
    # Memory layout / allocation
    ###

    def allocate_scope(self, scope) -> None:
        for name in scope.variable_order:
            self.layout.allocate_global(scope, name)

            info = scope.variables[name]
            if info.is_array:
                self.layout.mark_array(scope, name)

    def allocate_all_scopes(self) -> None:
        for scope in self.semantic_info.scopes:
            self.allocate_scope(scope)

    def variable_slot(self, name: str) -> int:
        if self.current_scope is None:
            raise CodeGenerationError(
                f"internal error: no current scope for variable {name!r}"
            )

        return self.layout.global_slot(self.current_scope, name)

    def emit_array_allocations_for_scope(self, scope):
        previous_scope = self.current_scope
        self.current_scope = scope

        for name in scope.variable_order:
            info = scope.variables[name]

            if not info.is_array:
                continue

            declaration_node = info.declaration_node

            if not isinstance(declaration_node, ast.ArrayDeclarator):
                raise CodeGenerationError(
                    f"internal error: array {name!r} has no array declarator"
                )

            if len(declaration_node.dimensions) != 1:
                raise CodeGenerationError(
                    "only one-dimensional arrays are supported yet"
                )

            self.emitter.new_line()
            self.emitter.comment(f"allocate array {scope.name}.{name}")

            dimension = declaration_node.dimensions[0]

            if isinstance(dimension, ast.Integer):
                self.emitter.emit(f"ALLOC {dimension.value}")
            else:
                if scope.kind != "program":
                    raise CodeGenerationError(
                        "dynamic array dimensions inside procedures "
                        "are not supported yet"
                    )

                self.visit_expression(dimension)
                self.emitter.emit("ALLOCN")

            slot = self.layout.global_slot(scope, name)
            self.emitter.emit(f"STOREG {slot}")

        self.current_scope = previous_scope

    def emit_all_array_allocations(self):
        for scope in self.semantic_info.scopes:
            self.emit_array_allocations_for_scope(scope)

    ###
    # Low-level emission helpers
    ###

    def new_label(self, prefix: str) -> str:
        label = f"L{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def emit_conversion(self, from_type: str, to_type: str) -> None:
        if from_type == to_type:
            return

        if from_type == "INTEGER" and to_type in {"REAL", "DOUBLE"}:
            self.emitter.emit("ITOF")
            return

        if from_type == "REAL" and to_type == "DOUBLE":
            # EWVM only haves one float representation.
            return

        if from_type == "DOUBLE" and to_type == "REAL":
            # EWVM only haves one float representation.
            return

        # NOTE Type checker should reject invalid conversions before codegen.

    def emit_read_value_for_type(self, type_name: str):
        self.emitter.emit("READ")

        if type_name == "INTEGER":
            self.emitter.emit("ATOI")
        elif type_name in {"REAL", "DOUBLE"}:
            self.emitter.emit("ATOF")
        elif type_name == "CHARACTER":
            pass
        else:
            raise CodeGenerationError(
                f"READ has unsupported target type {type_name!r}"
            )

    def comment_node(self, node, text: str) -> None:
        self.emitter.new_line()
        self.emitter.comment(text)

    ###
    # Procedure / control-flow helpers
    ###

    def unwrap_label_statement(self, node):
        """
        Labels wrap statements in the AST. For control-flow checks, the
        effective statement is the labelled statement itself.
        """

        while isinstance(node, ast.Label):
            node = node.statement

        return node

    def ends_with_return(self, statements) -> bool:
        """
        Return True when the procedure body definitely ends with RETURN.

        Conservative by design:
            - RETURN as the final statement: yes
            - labelled RETURN as the final statement: yes
            - anything else: no
        """

        if not statements:
            return False

        last_statement = self.unwrap_label_statement(statements[-1])

        return isinstance(last_statement, ast.Return)

    def emit_implicit_return_if_needed(self, statements) -> None:
        if not self.ends_with_return(statements):
            self.emitter.emit("RETURN")

    ###
    # Program unit generation
    ###

    def visit_file(self, node):
        if not isinstance(node, ast.File):
            raise CodeGenerationError(f"expected File node, got {node!r}")

        programs = [
            unit for unit in node.program_units
            if isinstance(unit, ast.Program)
        ]

        if not programs:
            raise CodeGenerationError(
                "code generation requires a PROGRAM unit"
            )

        self.procedures.register_from_file(node)
        self.allocate_all_scopes()

        program = programs[0]
        self.visit_program(program)

        for unit in node.program_units:
            if isinstance(unit, ast.Subroutine):
                self.visit_subroutine(unit)
            elif isinstance(unit, ast.Function):
                self.visit_function(unit)

    def visit_program(self, node):
        self.current_scope = self.find_scope(node.name, "program")

        self.emitter.comment(f"PROGRAM {node.name}")
        self.emitter.emit("START")

        if self.layout.global_slots:
            self.emitter.new_line()
            self.emitter.comment(
                f"allocate {len(self.layout.global_slots)} "
                "global variable slot(s)"
            )
            self.emitter.emit(f"PUSHN {len(self.layout.global_slots)}")

        self.emit_all_array_allocations()

        for statement in node.statements:
            self.visit_statement(statement)

        self.emitter.new_line()
        self.emitter.comment(f"END PROGRAM {node.name}")
        self.emitter.emit("STOP")

    def visit_procedure_body(
        self,
        *,
        name: str,
        kind: str,
        label: str,
        statements,
    ) -> None:
        self.current_scope = self.find_scope(name, kind)

        title = kind.upper()

        self.emitter.new_line()
        self.emitter.comment(f"{title} {name}")
        self.emitter.label(label)

        for statement in statements:
            self.visit_statement(statement)

        self.emitter.comment(f"END {title} {name}")
        self.emit_implicit_return_if_needed(statements)

    def visit_subroutine(self, node):
        self.visit_procedure_body(
            name=node.name,
            kind="subroutine",
            label=self.procedures.label(node.name),
            statements=node.statements,
        )

    def visit_function(self, node):
        self.visit_procedure_body(
            name=node.name,
            kind="function",
            label=self.procedures.label(node.name),
            statements=node.statements,
        )

    ###
    # Statement generation
    ###

    def visit_statement(self, node):
        if isinstance(node, ast.Declare):
            return

        self.comment_node(node, self.debug_formatter.statement(node))

        if isinstance(node, ast.Assign):
            self.visit_assign(node)
            return

        if isinstance(node, ast.Print):
            self.visit_print(node)
            return

        if isinstance(node, ast.Write):
            self.visit_write(node)
            return

        if isinstance(node, ast.Read):
            self.visit_read(node)
            return

        if isinstance(node, ast.If):
            self.visit_if(node)
            return

        if isinstance(node, ast.Label):
            self.visit_label(node)
            return

        if isinstance(node, ast.Do):
            self.visit_do(node)
            return

        if isinstance(node, ast.CallStatement):
            self.visit_call_statement(node)
            return

        if isinstance(node, ast.Goto):
            self.emitter.emit(f"JUMP L{node.label}")
            return

        if isinstance(node, ast.Stop):
            self.emitter.emit("STOP")
            return

        if isinstance(node, ast.Return):
            self.emitter.emit("RETURN")
            return

        if isinstance(node, ast.Continue):
            self.emitter.emit("NOP")
            return

        raise CodeGenerationError(
            f"unsupported statement for EWVM generation: {node!r}"
        )

    def visit_assign(self, node):
        if isinstance(node.target, ast.Var):
            self.visit_expression(node.value)

            value_type = self.expression_type(node.value)
            target_type = self.variable_type(node.target.name)

            self.emit_conversion(value_type, target_type)

            slot = self.variable_slot(node.target.name)
            self.emitter.comment(f"store into global slot {slot} "
                                 f"({node.target.name})")
            self.emitter.emit(f"STOREG {slot}")
            return

        if isinstance(node.target, ast.ArrayRef):
            self.visit_array_store(node.target, node.value)
            return

        raise CodeGenerationError(
            f"unsupported assignment target: {node.target!r}"
        )

    def write_items(self, items):
        for item in items:
            self.visit_expression(item)

            type_name = self.expression_type_hint(item)

            if type_name == "CHARACTER":
                self.emitter.emit("WRITES")
            elif type_name in {"REAL", "DOUBLE"}:
                self.emitter.emit("WRITEF")
            else:
                self.emitter.emit("WRITEI")

        self.emitter.emit("WRITELN")

    def visit_print(self, node):
        self.write_items(node.items)

    def visit_write(self, node):
        self.write_items(node.items)

    def visit_read(self, node):
        for variable in node.variables:
            if isinstance(variable, ast.Var):
                self.visit_read_var(variable)
                continue

            if isinstance(variable, ast.ArrayRef):
                self.visit_read_array_ref(variable)
                continue

            raise CodeGenerationError(f"unsupported READ target: {variable!r}")

    def visit_read_var(self, variable):
        type_name = self.variable_type(variable.name)

        self.emit_read_value_for_type(type_name)

        slot = self.variable_slot(variable.name)
        self.emitter.emit(f"STOREG {slot}")

    def visit_read_array_ref(self, variable):
        if len(variable.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array READ is supported yet"
            )

        self.emitter.comment(f"read into array element {variable.name}(...)")

        slot = self.variable_slot(variable.name)

        # STOREN expects: address, index, value
        self.emitter.emit(f"PUSHG {slot}")
        self.visit_array_index_zero_based(variable.indices[0])

        type_name = self.variable_type(variable.name)
        self.emit_read_value_for_type(type_name)

        self.emitter.emit("STOREN")

    ###
    # Expression generation
    ###

    def visit_expression(self, node):
        if isinstance(node, ast.Integer):
            self.emitter.emit(f"PUSHI {node.value}")
            return

        if isinstance(node, ast.Real):
            self.emitter.emit(f"PUSHF {node.value}")
            return

        if isinstance(node, ast.Double):
            # EWVM only has one real/float stack type
            self.emitter.emit(f"PUSHF {node.value}")
            return

        if isinstance(node, ast.String):
            self.emitter.emit(
                f"PUSHS {EWVMEmitter.string_literal(node.value)}"
            )
            return

        if isinstance(node, ast.Bool):
            self.emitter.emit(f"PUSHI {1 if node.value else 0}")
            return

        if isinstance(node, ast.Var):
            slot = self.variable_slot(node.name)
            self.emitter.emit(f"PUSHG {slot}")
            return

        if isinstance(node, ast.ArrayRef):
            self.visit_array_load(node)
            return

        if isinstance(node, ast.Arith):
            self.visit_arith(node)
            return

        if isinstance(node, ast.Rel):
            self.visit_rel(node)
            return

        if isinstance(node, ast.Logical):
            self.visit_logical(node)
            return

        if isinstance(node, ast.Unary):
            self.visit_unary(node)
            return

        if isinstance(node, ast.Call):
            self.visit_function_call(node)
            return

        if isinstance(node, ast.IndexedOrCall):
            raise CodeGenerationError(
                "internal error: unresolved IndexedOrCall reached code "
                f"generation: {node!r}"
            )

        raise CodeGenerationError(
            f"unsupported expression for EWVM generation: {node!r}"
        )

    def visit_arith(self, node):
        self.visit_expression(node.left)
        self.visit_expression(node.right)

        try:
            instruction = (
                FLOAT_ARITH_OPS[node.op]
                if self.expression_is_floatish(node)
                else INTEGER_ARITH_OPS[node.op]
            )
        except KeyError:
            raise CodeGenerationError(
                f"unsupported arithmetic operator {node.op!r}"
            )

        self.emitter.comment(f"apply arithmetic operator {node.op}")
        self.emitter.emit(instruction)

    def visit_rel(self, node):
        self.visit_expression(node.left)
        self.visit_expression(node.right)

        is_float = self.expression_is_floatish(node.left) or \
            self.expression_is_floatish(node.right)

        if node.op in {".EQ.", "==", "="}:
            self.emitter.emit("EQUAL")
        elif node.op in {".NE.", "/="}:
            self.emitter.emit("EQUAL")
            self.emitter.emit("NOT")
        elif node.op in {".LT.", "<"}:
            self.emitter.emit("FINF" if is_float else "INF")
        elif node.op in {".LE.", "<="}:
            self.emitter.emit("FINFEQ" if is_float else "INFEQ")
        elif node.op in {".GT.", ">"}:
            self.emitter.emit("FSUP" if is_float else "SUP")
        elif node.op in {".GE.", ">="}:
            self.emitter.emit("FSUPEQ" if is_float else "SUPEQ")
        else:
            raise CodeGenerationError(
                f"unsupported relational operator {node.op!r}"
            )

    def visit_logical(self, node):
        self.visit_expression(node.left)
        self.visit_expression(node.right)

        if node.op == ".AND.":
            self.emitter.emit("AND")
        elif node.op == ".OR.":
            self.emitter.emit("OR")
        else:
            raise CodeGenerationError(
                f"unsupported logical operator {node.op!r}"
            )

    def visit_unary(self, node):
        if node.op == "+":
            self.visit_expression(node.value)
            return

        if node.op == "-":
            value_type = self.expression_type(node.value)

            if value_type in {"REAL", "DOUBLE"}:
                self.emitter.emit("PUSHF 0.0")
                self.visit_expression(node.value)
                self.emitter.emit("FSUB")
            else:
                self.emitter.emit("PUSHI 0")
                self.visit_expression(node.value)
                self.emitter.emit("SUB")

            return

        if node.op == ".NOT.":
            self.visit_expression(node.value)
            self.emitter.emit("NOT")
            return

        raise CodeGenerationError(f"unsupported unary operator {node.op!r}")

    ###
    # Array generation
    ###

    def visit_array_index_zero_based(self, index_expr):
        self.visit_expression(index_expr)
        self.emitter.emit("PUSHI 1")
        self.emitter.emit("SUB")

    def visit_array_load(self, node):
        if len(node.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array references are supported yet"
            )

        self.emitter.comment(f"load array element {node.name}(...)")

        slot = self.variable_slot(node.name)

        self.emitter.emit(f"PUSHG {slot}")
        self.visit_array_index_zero_based(node.indices[0])
        self.emitter.emit("LOADN")

    def visit_array_store(self, target, value):
        if len(target.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array assignments are supported yet"
            )

        self.emitter.comment(f"store array element {target.name}(...)")

        slot = self.variable_slot(target.name)

        # STOREN expects: address, index, value
        self.emitter.emit(f"PUSHG {slot}")
        self.visit_array_index_zero_based(target.indices[0])

        self.visit_expression(value)

        value_type = self.expression_type(value)
        target_type = self.variable_type(target.name)

        self.emit_conversion(value_type, target_type)

        self.emitter.emit("STOREN")

    ###
    # Structured control-flow generation
    ###

    def visit_if(self, node):
        else_label = self.new_label("IFELSE")
        end_label = self.new_label("IFEND")

        self.emitter.comment("if condition")
        self.visit_expression(node.condition)

        if node.else_branch is None:
            self.emitter.emit(f"JZ {end_label}")

            self.emitter.comment("then branch")
            for statement in node.then_branch:
                self.visit_statement(statement)

            self.emitter.label(end_label)
            return

        self.emitter.emit(f"JZ {else_label}")

        self.emitter.comment("then branch")
        for statement in node.then_branch:
            self.visit_statement(statement)

        self.emitter.emit(f"JUMP {end_label}")

        self.emitter.label(else_label)

        self.emitter.comment("else branch")
        for statement in node.else_branch:
            self.visit_statement(statement)

        self.emitter.label(end_label)

    def visit_do(self, node):
        loop_id = self.loop_counter
        self.loop_counter += 1

        start_label = f"LDOSTART{loop_id}"
        body_label = f"LDOBODY{loop_id}"
        var_name = node.variable.name

        self.emitter.comment(f"initialize DO variable {var_name}")
        self.visit_expression(node.start)
        self.emitter.emit(f"STOREG {self.variable_slot(var_name)}")

        self.emitter.label(start_label)

        self.emitter.comment(f"check DO loop {var_name} <= end")
        self.emitter.emit(f"PUSHG {self.variable_slot(var_name)}")
        self.visit_expression(node.end)
        self.emitter.emit("SUP")
        self.emitter.emit(f"JZ {body_label}")
        self.emitter.emit(f"JUMP L{node.end_label}")

        self.emitter.label(body_label)

        self.pending_do_by_label[node.end_label] = {
            "variable": var_name,
            "start_label": start_label,
            "step": node.step,
        }

    def visit_label(self, node):
        loop_info = self.pending_do_by_label.get(node.number)

        if loop_info is not None and isinstance(node.statement, ast.Continue):
            var_name = loop_info["variable"]
            slot = self.variable_slot(var_name)
            step = loop_info["step"]

            self.emitter.comment(f"increment DO variable {var_name}")

            self.emitter.emit(f"PUSHG {slot}")

            if step is None:
                self.emitter.emit("PUSHI 1")
            else:
                self.visit_expression(step)

            self.emitter.emit("ADD")
            self.emitter.emit(f"STOREG {slot}")
            self.emitter.emit(f"JUMP {loop_info['start_label']}")

            self.emitter.label(f"L{node.number}")
            self.visit_statement(node.statement)

            del self.pending_do_by_label[node.number]
            return

        self.emitter.label(f"L{node.number}")
        self.visit_statement(node.statement)

    ###
    # Procedure call generation
    ###

    def visit_call_statement(self, node):
        info = self.procedure_info(node.name)

        if info.kind.startswith("intrinsic"):
            raise CodeGenerationError(
                f"intrinsic procedure {node.name!r} is not supported by code "
                "generation yet"
            )

        if info.kind != "subroutine":
            raise CodeGenerationError(
                f"{node.name!r} is not a subroutine"
            )

        target_scope = self.find_scope(info.name, "subroutine")

        self.emitter.comment(f"CALL {node.name}")

        self.copy_call_arguments(
            actual_arguments=node.arguments,
            formal_arguments=info.arguments,
            target_scope=target_scope,
        )

        self.emitter.emit(f"PUSHA {self.procedures.label(node.name)}")
        self.emitter.emit("CALL")

    def visit_function_call(self, node):
        info = self.procedure_info(node.name)

        if info.kind.startswith("intrinsic"):
            raise CodeGenerationError(
                f"intrinsic procedure {node.name!r} is not supported by code "
                "generation yet"
            )

        if info.kind != "function":
            raise CodeGenerationError(
                f"{node.name!r} is not a function"
            )

        target_scope = self.find_scope(info.name, "function")

        self.emitter.comment(f"call function {node.name}")

        self.copy_call_arguments(
            actual_arguments=node.arguments,
            formal_arguments=info.arguments,
            target_scope=target_scope,
        )

        self.emitter.emit(f"PUSHA {self.procedures.label(node.name)}")
        self.emitter.emit("CALL")

        return_slot = self.layout.global_slot(target_scope, info.name)
        self.emitter.emit(f"PUSHG {return_slot}")

    def copy_call_arguments(
        self,
        *,
        actual_arguments,
        formal_arguments,
        target_scope,
    ):
        if len(actual_arguments) != len(formal_arguments):
            raise CodeGenerationError(
                "internal error: procedure argument count mismatch"
            )

        caller_scope = self.current_scope

        for actual, formal_name in zip(actual_arguments, formal_arguments):
            self.current_scope = caller_scope
            self.visit_expression(actual)

            actual_type = self.expression_type(actual)

            formal_info = target_scope.variables.get(formal_name)
            if formal_info is None:
                raise CodeGenerationError(
                    f"internal error: formal argument {formal_name!r} "
                    f"has no slot"
                )

            self.emit_conversion(actual_type, formal_info.type_name)

            formal_slot = self.layout.global_slot(target_scope, formal_name)
            self.emitter.emit(f"STOREG {formal_slot}")

        self.current_scope = caller_scope


def generate(
    tree: AST,
    semantic_info: SemanticInfo,
    debug: bool = False
) -> str:
    generator = EWVMGenerator(semantic_info, debug=debug)
    return generator.generate(tree)


def main():
    """
    Main function to compile Fortran 77 source code into EWVM assembly.
    """

    import argparse
    import sys

    from common import (
        read_input,
        detect_source_format,
        visualize_ast,
        write_output
    )
    from preprocessor import preprocess
    from lexer import lexer, clear_lexer_state
    from parser import parser, clear_parser_state
    from semantics import semantic_checks, semantic_checks_post_optimizations
    from semantics.semantic_info import print_semantic_info
    from optimizations import optimizations
    from abstract_syntax_tree import (
        pretty_print,
        DEFAULT_VIS_OUTPUT_PATH
    )
    from error import flush_diagnostics

    # CLI argument parsing
    parser_args = argparse.ArgumentParser(
        description="Compile Fortran 77 source code into EWVM assembly."
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file to compile. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "--output", "-o",
        metavar="OUTPUT",
        help="Output file for the generated EWVM assembly code. "
             "If omitted, output to stdout."
    )

    parser_args.add_argument(
        "--optimize", "-O",
        action="store_true",
        default=False,
        help="Enable optimizations in the generated assembly code."
    )

    parser_args.add_argument(
        "--debug", "-g",
        action="store_true",
        default=False,
        help="Enable debug comments in the generated assembly code."
    )

    parser_args.add_argument(
        "--format",
        choices=["fixed", "free"],
        default=None,
        help="The source format. If omitted, inferred from file extension; "
             "stdin defaults to fixed."
    )

    parser_args.add_argument(
        "--no-preprocess",
        action="store_true",
        default=False,
        help="Skip preprocessing and parse the raw input directly",
    )

    parser_args.add_argument(
        "--visualize", "--viz",
        nargs="?",
        const=DEFAULT_VIS_OUTPUT_PATH,
        metavar="OUTPUT",
        help="Generate a Graphviz image of the AST "
             f"(default output: {DEFAULT_VIS_OUTPUT_PATH})"
    )

    parser_args.add_argument(
        "--show-intrinsics",
        action="store_true",
        default=False,
        help="Include intrinsic procedures in verbose semantic info output",
    )

    parser_args.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose output during compilation"
             "(e.g. print intermediate ASTs, semantic info, etc.)"
    )

    args = parser_args.parse_args()

    # Read input data
    try:
        source_filename, source_data = read_input(args.input_file)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Detect source format based on file extension
    source_format = detect_source_format(args.input_file, args.format)

    # Pre-process the input data
    if not args.no_preprocess:
        try:
            source_data = preprocess(source_data, format=source_format)
        except Exception as e:
            print(f"Preprocessing error: {e}", file=sys.stderr)
            sys.exit(1)

    # Set up lexer and parser state
    clear_lexer_state(lexer)
    clear_parser_state(parser)

    source_lines = source_data.splitlines()

    lexer.source_lines, parser.source_lines = (source_lines,) * 2
    lexer.source_filename, parser.source_filename = (source_filename,) * 2

    # Parse the input data
    result = parser.parse(source_data, lexer=lexer, debug=False)

    # Propagate lexer errors to parser, since the lexer doesn't exit on error
    parser.diagnostics.extend(lexer.diagnostics)
    if lexer.has_error:
        parser.has_error = True

    if result is None:
        flush_diagnostics(parser)
        print(
            f"\n{len(parser.diagnostics)} error(s)/warning(s) encountered.",
            file=sys.stderr
        )
        print("[panic] parser could't produce an AST", file=sys.stderr)
        sys.exit(1)

    # Semantic checks
    result, semantic_info = semantic_checks(parser, ast=result)

    # Stop immediately on semantic errors
    # Do not proceed to optimization if the program is invalid
    if parser.has_error:
        flush_diagnostics(parser)
        print(
            f"\n{len(parser.diagnostics)} error(s)/warning(s) encountered.",
            file=sys.stderr
        )
        sys.exit(1)

    # Verbose output of semantic information and initial AST
    if args.verbose:
        print("\nInitial AST:\n============\n")
        pretty_print(result)

        print()
        print_semantic_info(semantic_info,
                            show_intrinsics=args.show_intrinsics)

    # Visualize initial AST
    if args.visualize:
        visualize_ast(result, output_path=args.visualize, optimized=False)

    if not args.optimize:
        # Report diagnostics from the normal semantic pass
        flush_diagnostics(parser)
    else:
        # Discard pre-optimization warnings. They may no longer be true after
        # optimization, for example unused variables removed by DCE.
        parser.diagnostics.clear()

        result = optimizations(result)

        # Re-run semantic checks to ensure consistent semantic information.
        # INFO Alternatively we could have optimizations return both the
        # optimized AST as the updated semantic_info
        result, semantic_info = semantic_checks_post_optimizations(
            parser,
            ast=result
        )

        flush_diagnostics(parser)

        if parser.has_error:
            print(
                f"\n{len(parser.diagnostics)} error(s)/warning(s) encountered.",
                file=sys.stderr
            )
            sys.exit(1)

        # Verbose output of optimized AST
        if args.verbose:
            print("\nOptimized AST:\n==============\n")
            pretty_print(result)

        # Visualize optimized AST
        if args.visualize:
            visualize_ast(result, output_path=args.visualize, optimized=True)

    # Generate EWVM assembly code from the AST and semantic information
    try:
        assembly = generate(result, semantic_info, debug=args.debug)
    except CodeGenerationError as e:
        print(f"Code generation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Write output assembly code to file or stdout
    try:
        write_output(args.output, assembly, verbose=args.verbose)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
