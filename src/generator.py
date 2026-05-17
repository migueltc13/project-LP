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
    TEMP_SLOTS_PER_SCOPE = 16

    def __init__(self):
        self.global_slots: dict[tuple[str, str, str], int] = {}
        self.local_slots: dict[tuple[str, str, str], int] = {}
        self.arrays: set[tuple[str, str, str]] = set()
        self.scope_local_sizes: dict[tuple[str, str], int] = {}
        self.scope_temp_slots: dict[tuple[str, str], list[int]] = {}

    def key(self, scope, name: str) -> tuple[str, str, str]:
        return (scope.kind, scope.name.upper(), name.upper())

    def scope_key(self, scope) -> tuple[str, str]:
        return (scope.kind, scope.name.upper())

    def is_global_scope(self, scope) -> bool:
        return scope.kind == "program"

    def allocate_global(self, scope, name: str) -> int:
        key = self.key(scope, name)

        if key not in self.global_slots:
            self.global_slots[key] = len(self.global_slots)

        return self.global_slots[key]

    def allocate_local(self, scope, name: str) -> int:
        key = self.key(scope, name)

        if key not in self.local_slots:
            scope_key = self.scope_key(scope)
            slot = self.scope_local_sizes.get(scope_key, 0)
            self.local_slots[key] = slot
            self.scope_local_sizes[scope_key] = slot + 1

        return self.local_slots[key]

    def global_slot(self, scope, name: str) -> int:
        key = self.key(scope, name)

        try:
            return self.global_slots[key]
        except KeyError:
            raise CodeGenerationError(
                f"internal error: variable {name!r} has no global slot "
                f"in {scope.kind} {scope.name!r}"
            )

    def local_slot(self, scope, name: str) -> int:
        key = self.key(scope, name)

        try:
            return self.local_slots[key]
        except KeyError:
            raise CodeGenerationError(
                f"internal error: variable {name!r} has no local slot "
                f"in {scope.kind} {scope.name!r}"
            )

    def mark_array(self, scope, name: str) -> None:
        self.arrays.add(self.key(scope, name))

    def is_array(self, scope, name: str) -> bool:
        return self.key(scope, name) in self.arrays

    def local_size(self, scope) -> int:
        return self.scope_local_sizes.get(self.scope_key(scope), 0)

    def allocate_temp_slots(self, scope) -> None:
        scope_key = self.scope_key(scope)

        if scope_key in self.scope_temp_slots:
            return

        slots = []

        for i in range(self.TEMP_SLOTS_PER_SCOPE):
            name = f"__TMP_{i}"

            if self.is_global_scope(scope):
                slot = self.allocate_global(scope, name)
            else:
                slot = self.allocate_local(scope, name)

            slots.append(slot)

        self.scope_temp_slots[scope_key] = slots

    def temp_slot(self, scope, index: int) -> int:
        slots = self.scope_temp_slots.get(self.scope_key(scope))

        if slots is None:
            raise CodeGenerationError(
                f"internal error: temporary slots not allocated for "
                f"{scope.kind} {scope.name!r}"
            )

        try:
            return slots[index]
        except IndexError:
            raise CodeGenerationError(
                "internal error: out of compiler temporary slots"
            )


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
# TODO(codegen): Improve compiler temporary allocation for deeply nested expressions.
# TODO(codegen): Add constant-domain checks for intrinsic calls.
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
        self.temp_slot_index = 0

    def generate(self, tree) -> str:
        self.visit_file(tree)
        return self.emitter.render()

    def reset_temp_slots(self) -> None:
        self.temp_slot_index = 0

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
            info = scope.variables[name]

            # Formal arguments are passed on the call frame with negative PUSHL
            # offsets. They do not need positive local/global slots.
            if info.is_argument:
                if info.is_array:
                    self.layout.mark_array(scope, name)
                continue

            if scope.kind == "program":
                self.layout.allocate_global(scope, name)
            else:
                self.layout.allocate_local(scope, name)

            if info.is_array:
                self.layout.mark_array(scope, name)

        self.layout.allocate_temp_slots(scope)

    def allocate_all_scopes(self) -> None:
        for scope in self.semantic_info.scopes:
            self.allocate_scope(scope)

    def variable_slot(self, name: str) -> int:
        if self.current_scope is None:
            raise CodeGenerationError(
                f"internal error: no current scope for variable {name!r}"
            )

        if self.is_argument(name):
            raise CodeGenerationError(
                f"internal error: formal argument {name!r} has no normal slot"
            )

        if self.current_scope.kind == "program":
            return self.layout.global_slot(self.current_scope, name)

        return self.layout.local_slot(self.current_scope, name)

    def emit_load_slot(self, name: str) -> None:
        slot = self.variable_slot(name)

        if self.current_scope.kind == "program":
            self.emitter.emit(f"PUSHG {slot}")
        else:
            self.emitter.emit(f"PUSHL {slot}")

    def emit_store_slot(self, name: str) -> None:
        slot = self.variable_slot(name)

        if self.current_scope.kind == "program":
            self.emitter.emit(f"STOREG {slot}")
        else:
            self.emitter.emit(f"STOREL {slot}")

    def compiler_temp_slot(self) -> int:
        if self.current_scope is None:
            raise CodeGenerationError(
                "internal error: no current scope for compiler temporary"
            )

        slot = self.layout.temp_slot(self.current_scope, self.temp_slot_index)
        self.temp_slot_index += 1
        return slot

    def emit_load_temp(self, slot: int) -> None:
        if self.current_scope.kind == "program":
            self.emitter.emit(f"PUSHG {slot}")
        else:
            self.emitter.emit(f"PUSHL {slot}")

    def emit_store_temp(self, slot: int) -> None:
        if self.current_scope.kind == "program":
            self.emitter.emit(f"STOREG {slot}")
        else:
            self.emitter.emit(f"STOREL {slot}")

    def emit_array_allocations_for_scope(self, scope):
        previous_scope = self.current_scope
        self.current_scope = scope

        for name in scope.variable_order:
            info = scope.variables[name]

            if not info.is_array:
                continue

            # Array arguments are passed by reference. Do not allocate them.
            if info.is_argument:
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

            if scope.kind == "program":
                slot = self.layout.global_slot(scope, name)
                self.emitter.emit(f"STOREG {slot}")
            else:
                slot = self.layout.local_slot(scope, name)
                self.emitter.emit(f"STOREL {slot}")

        self.current_scope = previous_scope

    def emit_all_array_allocations(self):
        for scope in self.semantic_info.scopes:
            self.emit_array_allocations_for_scope(scope)

    def variable_info(self, name: str):
        if self.current_scope is None:
            return None

        return self.current_scope.variables.get(name)

    def is_argument(self, name: str) -> bool:
        info = self.variable_info(name)
        return info is not None and info.is_argument

    def is_array_variable(self, name: str) -> bool:
        info = self.variable_info(name)
        return info is not None and info.is_array

    def current_procedure_arguments(self) -> list[str]:
        if self.current_scope is None:
            return []

        if self.current_scope.kind == "program":
            return []

        procedure = self.semantic_info.procedures.get(self.current_scope.name.upper())

        if procedure is None:
            return []

        return procedure.arguments

    def formal_argument_offset(self, name: str) -> int:
        arguments = self.current_procedure_arguments()

        try:
            index = [arg.upper() for arg in arguments].index(name.upper())
        except ValueError:
            raise CodeGenerationError(
                f"internal error: formal argument {name!r} not found"
            )

        if self.current_scope is not None and self.current_scope.kind == "function":
            # Function call layout:
            #   arg0, arg1, ..., argN, hidden_result
            #
            # For n args:
            #   hidden_result -> -1
            #   last arg      -> -2
            #   first arg     -> -(n + 1)
            return index - len(arguments) - 1

        # Subroutine call layout:
        #   arg0, arg1, ..., argN
        #
        # For n args:
        #   last arg  -> -1
        #   first arg -> -n
        return index - len(arguments)

    def function_hidden_return_offset(self) -> int:
        # The hidden result address is pushed after all user arguments,
        # so it is always the last negative slot.
        return -1

    def emit_variable_address(self, variable: ast.Var) -> None:
        """
        Push the address of a scalar variable.

        Normal program variable:
            PUSHGP + slot

        Normal procedure local:
            PUSHFP + slot

        Formal argument:
            PUSHL negative_offset
            because the argument value is already an address.
        """

        if self.is_argument(variable.name):
            self.emitter.emit(f"PUSHL {self.formal_argument_offset(variable.name)}")
            return

        slot = self.variable_slot(variable.name)

        if self.current_scope.kind == "program":
            self.emitter.emit("PUSHGP")
            self.emitter.emit(f"PUSHI {slot}")
            self.emitter.emit("PADD")
        else:
            self.emitter.emit("PUSHFP")
            self.emitter.emit(f"PUSHI {slot}")
            self.emitter.emit("PADD")

    def emit_lvalue_address(self, node) -> None:
        if isinstance(node, ast.Var):
            # Passing an array variable to an array formal parameter should pass
            # the array base address, not the variable slot address.
            if self.is_array_variable(node.name):
                self.emit_array_base_address(node.name)
            else:
                self.emit_variable_address(node)
            return

        if isinstance(node, ast.ArrayRef):
            self.emit_array_element_address(node)
            return

        raise CodeGenerationError(
            f"procedure arguments are passed by reference; "
            f"actual argument {node!r} is not addressable"
        )

    def emit_array_base_address(self, name: str) -> None:
        """
        Push array base address.

        Normal array:
            slot stores heap base address.

        Formal array:
            negative PUSHL offset stores caller's array base address.
        """

        if self.is_argument(name):
            self.emitter.emit(f"PUSHL {self.formal_argument_offset(name)}")
            return

        self.emit_load_slot(name)

    def emit_array_element_address(self, node: ast.ArrayRef) -> None:
        if len(node.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array references are supported yet"
            )

        self.emit_array_base_address(node.name)
        self.visit_array_index_zero_based(node.indices[0])
        self.emitter.emit("PADD")

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

    def emit_function_result_store(self) -> None:
        if self.current_scope is None or self.current_scope.kind != "function":
            return

        return_offset = self.function_hidden_return_offset()

        # Store function-name variable into caller-provided result address.
        self.emitter.emit(f"PUSHL {return_offset}")
        self.visit_expression(ast.Var(self.current_scope.name))
        self.emitter.emit("STORE 0")

    def emit_temp_address(self, slot: int) -> None:
        if self.current_scope.kind == "program":
            self.emitter.emit("PUSHGP")
            self.emitter.emit(f"PUSHI {slot}")
            self.emitter.emit("PADD")
        else:
            self.emitter.emit("PUSHFP")
            self.emitter.emit(f"PUSHI {slot}")
            self.emitter.emit("PADD")

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
            if (
                self.current_scope is not None and
                self.current_scope.kind == "function"
            ):
                self.emit_function_result_store()

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
        self.reset_temp_slots()

        self.emitter.comment(f"PROGRAM {node.name}")
        self.emitter.emit("START")

        if self.layout.global_slots:
            self.emitter.new_line()
            self.emitter.comment(
                f"allocate {len(self.layout.global_slots)} "
                "global variable slot(s)"
            )
            self.emitter.emit(f"PUSHN {len(self.layout.global_slots)}")

        self.emit_array_allocations_for_scope(self.current_scope)

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
        self.reset_temp_slots()

        title = kind.upper()

        self.emitter.new_line()
        self.emitter.comment(f"{title} {name}")
        self.emitter.label(label)

        local_count = self.layout.local_size(self.current_scope)

        if local_count > 0:
            self.emitter.comment(
                f"allocate {local_count} local slot(s)"
            )
            self.emitter.emit(f"PUSHN {local_count}")

        self.emit_array_allocations_for_scope(self.current_scope)

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
        self.reset_temp_slots()

        if isinstance(node, ast.Declare):
            return

        # Comment the statement before generating it
        self.emitter.new_line()
        self.emitter.comment(self.debug_formatter.statement(node))

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
            if (
                self.current_scope is not None and
                self.current_scope.kind == "function"
            ):
                self.emit_function_result_store()

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
            if isinstance(node.value, ast.Call):
                info = self.procedure_info(node.value.name)

                if info.kind == "function":
                    self.visit_function_call_into_address(
                        node.value,
                        lambda: self.emit_variable_address(node.target),
                    )
                    return

            self.visit_expression(node.value)

            value_type = self.expression_type(node.value)
            target_type = self.variable_type(node.target.name)

            self.emit_conversion(value_type, target_type)

            if self.is_argument(node.target.name):
                temp_slot = self.compiler_temp_slot()
                self.emit_store_temp(temp_slot)

                self.emit_variable_address(node.target)
                self.emit_load_temp(temp_slot)
                self.emitter.emit("STORE 0")
            else:
                self.emit_store_slot(node.target.name)

            return

        if isinstance(node.target, ast.ArrayRef):
            if isinstance(node.value, ast.Call):
                info = self.procedure_info(node.value.name)

                if info.kind == "function":
                    self.visit_function_call_into_address(
                        node.value,
                        lambda: self.emit_array_element_address(node.target),
                    )
                    return

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

        if self.is_argument(variable.name):
            temp_slot = self.compiler_temp_slot()
            self.emit_store_temp(temp_slot)

            self.emit_variable_address(variable)
            self.emit_load_temp(temp_slot)
            self.emitter.emit("STORE 0")
            return

        self.emit_store_slot(variable.name)

    def visit_read_array_ref(self, variable):
        if len(variable.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array READ is supported yet"
            )

        self.emitter.comment(f"read into array element {variable.name}(...)")

        self.emit_array_base_address(variable.name)
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
            if self.is_argument(node.name):
                self.emitter.emit(f"PUSHL {self.formal_argument_offset(node.name)}")
                self.emitter.emit("LOAD 0")
            else:
                self.emit_load_slot(node.name)
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
        if node.op == "**":
            self.visit_pow_expression(node.left, node.right, node)
            return

        if self.expression_contains_user_function_call(node.right):
            right_temp = self.compiler_temp_slot()

            self.visit_expression(node.right)
            self.emit_store_temp(right_temp)

            self.visit_expression(node.left)
            self.emit_load_temp(right_temp)
        else:
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

    def expression_contains_user_function_call(self, node) -> bool:
        if isinstance(node, ast.Call):
            info = self.procedure_info(node.name)
            return info.kind == "function"

        if isinstance(node, ast.ArrayRef):
            return any(
                self.expression_contains_user_function_call(index)
                for index in node.indices
            )

        if isinstance(node, ast.Unary):
            return self.expression_contains_user_function_call(node.value)

        if isinstance(node, ast.Arith):
            return (
                self.expression_contains_user_function_call(node.left)
                or self.expression_contains_user_function_call(node.right)
            )

        if isinstance(node, ast.Rel):
            return (
                self.expression_contains_user_function_call(node.left)
                or self.expression_contains_user_function_call(node.right)
            )

        if isinstance(node, ast.Logical):
            return (
                self.expression_contains_user_function_call(node.left)
                or self.expression_contains_user_function_call(node.right)
            )

        return False

    def visit_rel(self, node):
        if self.expression_contains_user_function_call(node.right):
            right_temp = self.compiler_temp_slot()

            # Evaluate RHS first and save it.
            self.visit_expression(node.right)
            self.emit_store_temp(right_temp)

            # Then emit normal operand order: left, right.
            self.visit_expression(node.left)
            self.emit_load_temp(right_temp)
        else:
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
        if self.expression_contains_user_function_call(node.right):
            right_temp = self.compiler_temp_slot()

            self.visit_expression(node.right)
            self.emit_store_temp(right_temp)

            self.visit_expression(node.left)
            self.emit_load_temp(right_temp)
        else:
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

        self.emit_array_base_address(node.name)
        self.visit_array_index_zero_based(node.indices[0])
        self.emitter.emit("LOADN")

    def visit_array_store(self, target, value):
        if len(target.indices) != 1:
            raise CodeGenerationError(
                "only one-dimensional array assignments are supported yet"
            )

        self.emitter.comment(f"store array element {target.name}(...)")

        self.emit_array_base_address(target.name)
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
        self.emit_store_slot(var_name)

        self.emitter.label(start_label)

        self.emitter.comment(f"check DO loop {var_name} <= end")
        self.emit_load_slot(var_name)
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
            step = loop_info["step"]

            self.emitter.comment(f"increment DO variable {var_name}")

            self.emit_load_slot(var_name)

            if step is None:
                self.emitter.emit("PUSHI 1")
            else:
                self.visit_expression(step)

            self.emitter.emit("ADD")
            self.emit_store_slot(var_name)
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
                "generation as a subroutine"
            )

        if info.kind != "subroutine":
            raise CodeGenerationError(
                f"{node.name!r} is not a subroutine"
            )

        self.emitter.comment(f"CALL {node.name}")

        self.push_call_arguments_by_reference(node.arguments)

        self.emitter.emit(f"PUSHA {self.procedures.label(node.name)}")
        self.emitter.emit("CALL")

        self.cleanup_call_arguments(len(node.arguments))

    def visit_function_call(self, node):
        info = self.procedure_info(node.name)

        if info.kind == "intrinsic_function":
            self.visit_intrinsic_function_call(node)
            return

        if info.kind != "function":
            raise CodeGenerationError(
                f"{node.name!r} is not a function"
            )

        result_slot = self.compiler_temp_slot()

        self.visit_function_call_into_address(
            node,
            lambda: self.emit_temp_address(result_slot),
        )

        self.emit_load_temp(result_slot)

    def visit_function_call_into_address(
        self,
        node: ast.Call,
        emit_result_address
    ) -> None:
        info = self.procedure_info(node.name)

        if info.kind == "intrinsic_function":
            # Intrinsics are expression-valued; generate normally and store outside.
            self.visit_intrinsic_function_call(node)
            return

        if info.kind != "function":
            raise CodeGenerationError(
                f"{node.name!r} is not a function"
            )

        self.emitter.comment(f"call function {node.name}")

        # User arguments.
        self.push_call_arguments_by_reference(node.arguments)

        # Hidden result address.
        emit_result_address()

        self.emitter.emit(f"PUSHA {self.procedures.label(node.name)}")
        self.emitter.emit("CALL")

        # Remove hidden result address + user argument addresses.
        self.cleanup_call_arguments(len(node.arguments) + 1)

    def push_call_arguments_by_reference(self, actual_arguments) -> None:
        for actual in actual_arguments:
            if not isinstance(actual, (ast.Var, ast.ArrayRef)):
                raise CodeGenerationError(
                    "procedure arguments are passed by reference, "
                    f"so actual argument {actual!r} must be a variable "
                    "or array element"
                )

            self.emit_lvalue_address(actual)

    def cleanup_call_arguments(self, count: int) -> None:
        if count > 0:
            self.emitter.emit(f"POP {count}")

    ###
    # Instrinsic function generation
    ###

    def require_intrinsic_arity(self, node, expected: int) -> None:
        actual = len(node.arguments)

        if actual != expected:
            raise CodeGenerationError(
                f"internal error: intrinsic function {node.name!r} expects "
                f"{expected} argument(s), got {actual}"
            )

    def require_intrinsic_min_arity(self, node, expected_min: int) -> None:
        actual = len(node.arguments)

        if actual < expected_min:
            raise CodeGenerationError(
                f"internal error: intrinsic function {node.name!r} expects "
                f"at least {expected_min} argument(s), got {actual}"
            )

    def visit_intrinsic_function_call(self, node):
        name = node.name.upper()

        if name in {"ABS", "IABS", "DABS"}:
            self.visit_intrinsic_abs(node)
            return

        if name == "POW":
            self.require_intrinsic_arity(node, 2)
            self.visit_pow_expression(
                node.arguments[0],
                node.arguments[1],
                node
            )
            return

        if name in {"INT", "REAL", "DBLE", "FLOAT"}:
            self.visit_intrinsic_conversion(node)
            return

        if name == "MOD":
            self.visit_intrinsic_mod(node)
            return

        if name in {"MAX", "MIN"}:
            self.visit_intrinsic_minmax(node, want_max=(name == "MAX"))
            return

        if name in {"SQRT", "DSQRT"}:
            self.visit_intrinsic_sqrt(node)
            return

        if name in {"EXP", "DEXP"}:
            self.visit_intrinsic_exp(node)
            return

        raise CodeGenerationError(
            f"intrinsic function {node.name!r} is not supported by code "
            "generation"
        )

    def visit_intrinsic_conversion(self, node):
        self.require_intrinsic_arity(node, 1)

        name = node.name.upper()
        argument = node.arguments[0]
        argument_type = self.expression_type(argument)

        self.visit_expression(argument)

        if name == "INT":
            if argument_type in {"REAL", "DOUBLE"}:
                self.emitter.emit("FTOI")
            return

        if name in {"REAL", "DBLE", "FLOAT"}:
            if argument_type == "INTEGER":
                self.emitter.emit("ITOF")
            return

        raise CodeGenerationError(
            f"unsupported conversion intrinsic {node.name!r}"
        )

    def visit_intrinsic_mod(self, node):
        self.require_intrinsic_arity(node, 2)

        self.visit_expression(node.arguments[0])
        self.visit_expression(node.arguments[1])
        self.emitter.emit("MOD")

    def visit_intrinsic_abs(self, node):
        self.require_intrinsic_arity(node, 1)

        argument = node.arguments[0]
        result_is_float = (
            node.name.upper() == "DABS"
            or self.expression_type(argument) in {"REAL", "DOUBLE"}
        )

        temp_slot = self.compiler_temp_slot()
        positive_label = self.new_label("ABSPOS")
        end_label = self.new_label("ABSEND")

        self.visit_expression(argument)
        self.emit_store_temp(temp_slot)

        self.emit_load_temp(temp_slot)
        if result_is_float:
            self.emitter.emit("PUSHF 0.0")
            self.emitter.emit("FINF")
        else:
            self.emitter.emit("PUSHI 0")
            self.emitter.emit("INF")

        self.emitter.emit(f"JZ {positive_label}")

        if result_is_float:
            self.emitter.emit("PUSHF 0.0")
            self.emit_load_temp(temp_slot)
            self.emitter.emit("FSUB")
        else:
            self.emitter.emit("PUSHI 0")
            self.emit_load_temp(temp_slot)
            self.emitter.emit("SUB")

        self.emitter.emit(f"JUMP {end_label}")

        self.emitter.label(positive_label)
        self.emit_load_temp(temp_slot)

        self.emitter.label(end_label)

    def visit_intrinsic_minmax(self, node, *, want_max: bool):
        self.require_intrinsic_min_arity(node, 2)

        result_is_float = self.expression_type(node) in {"REAL", "DOUBLE"}
        temp_slot = self.compiler_temp_slot()

        # Store first argument as current best.
        self.visit_expression(node.arguments[0])
        self.emit_store_temp(temp_slot)

        for argument in node.arguments[1:]:
            replace_label = self.new_label("MINMAXREPLACE")
            end_label = self.new_label("MINMAXEND")

            # Compare current best with candidate.
            self.emit_load_temp(temp_slot)
            self.visit_expression(argument)

            if want_max:
                # current >= candidate
                self.emitter.emit("FSUPEQ" if result_is_float else "SUPEQ")
            else:
                # current <= candidate
                self.emitter.emit("FINFEQ" if result_is_float else "INFEQ")

            # If comparison is false, candidate becomes best.
            self.emitter.emit(f"JZ {replace_label}")

            # Keep current.
            self.emitter.emit(f"JUMP {end_label}")

            self.emitter.label(replace_label)
            self.visit_expression(argument)
            self.emit_store_temp(temp_slot)

            self.emitter.label(end_label)

        self.emit_load_temp(temp_slot)

    def visit_pow_expression(self, base, exponent, node):
        base_type = self.expression_type(base)
        exponent_type = self.expression_type(exponent)
        result_type = self.expression_type(node)

        if exponent_type != "INTEGER":
            raise CodeGenerationError(
                "POW/** currently requires INTEGER exponent in code generation"
            )

        if (
            result_type in {"REAL", "DOUBLE"} or
            base_type in {"REAL", "DOUBLE"}
        ):
            self.visit_pow_float_base_integer_exponent(base, exponent)
            return

        self.visit_pow_integer_base_integer_exponent(base, exponent)

    def visit_pow_float_base_integer_exponent(self, base, exponent):
        base_slot = self.compiler_temp_slot()
        exp_slot = self.compiler_temp_slot()
        result_slot = self.compiler_temp_slot()

        loop_label = self.new_label("FPOWLOOP")
        body_label = self.new_label("FPOWBODY")
        end_label = self.new_label("FPOWEND")

        self.visit_expression(base)

        if self.expression_type(base) == "INTEGER":
            self.emitter.emit("ITOF")

        self.emit_store_temp(base_slot)

        self.visit_expression(exponent)
        self.emit_store_temp(exp_slot)

        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 0")
        self.emitter.emit("INF")
        self.emitter.emit(f"JZ {body_label}")
        self.emitter.emit('ERR "negative exponent is not supported"')

        self.emitter.label(body_label)

        self.emitter.emit("PUSHF 1.0")
        self.emit_store_temp(result_slot)

        self.emitter.label(loop_label)

        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 0")
        self.emitter.emit("SUP")
        self.emitter.emit(f"JZ {end_label}")

        self.emit_load_temp(result_slot)
        self.emit_load_temp(base_slot)
        self.emitter.emit("FMUL")
        self.emit_store_temp(result_slot)

        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 1")
        self.emitter.emit("SUB")
        self.emit_store_temp(exp_slot)

        self.emitter.emit(f"JUMP {loop_label}")

        self.emitter.label(end_label)
        self.emit_load_temp(result_slot)

    def visit_pow_integer_base_integer_exponent(self, base, exponent):
        base_slot = self.compiler_temp_slot()
        exp_slot = self.compiler_temp_slot()
        result_slot = self.compiler_temp_slot()

        loop_label = self.new_label("POWLOOP")
        body_label = self.new_label("POWBODY")
        end_label = self.new_label("POWEND")

        self.visit_expression(base)
        self.emit_store_temp(base_slot)

        self.visit_expression(exponent)
        self.emit_store_temp(exp_slot)

        # Reject negative exponent at runtime for integer POW.
        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 0")
        self.emitter.emit("INF")
        self.emitter.emit(f"JZ {body_label}")
        self.emitter.emit('ERR "negative INTEGER exponent is not supported"')

        self.emitter.label(body_label)

        self.emitter.emit("PUSHI 1")
        self.emit_store_temp(result_slot)

        self.emitter.label(loop_label)

        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 0")
        self.emitter.emit("SUP")
        self.emitter.emit(f"JZ {end_label}")

        self.emit_load_temp(result_slot)
        self.emit_load_temp(base_slot)
        self.emitter.emit("MUL")
        self.emit_store_temp(result_slot)

        self.emit_load_temp(exp_slot)
        self.emitter.emit("PUSHI 1")
        self.emitter.emit("SUB")
        self.emit_store_temp(exp_slot)

        self.emitter.emit(f"JUMP {loop_label}")

        self.emitter.label(end_label)
        self.emit_load_temp(result_slot)

    def visit_intrinsic_sqrt(self, node):
        self.require_intrinsic_arity(node, 1)

        value = node.arguments[0]

        n_slot = self.compiler_temp_slot()
        x_slot = self.compiler_temp_slot()
        i_slot = self.compiler_temp_slot()

        positive_label = self.new_label("SQRTPOS")
        init_loop_label = self.new_label("SQRTINIT")
        loop_label = self.new_label("SQRTLOOP")
        push_result_label = self.new_label("SQRTPUSH")
        final_label = self.new_label("SQRTFINAL")

        self.visit_expression(value)

        if self.expression_type(value) == "INTEGER":
            self.emitter.emit("ITOF")

        self.emit_store_temp(n_slot)

        # if n < 0: runtime error
        self.emit_load_temp(n_slot)
        self.emitter.emit("PUSHF 0.0")
        self.emitter.emit("FINF")
        self.emitter.emit(f"JZ {positive_label}")
        self.emitter.emit('ERR "SQRT domain error: negative argument"')

        self.emitter.label(positive_label)

        # if n == 0: result is 0.0
        self.emit_load_temp(n_slot)
        self.emitter.emit("PUSHF 0.0")
        self.emitter.emit("EQUAL")
        self.emitter.emit(f"JZ {init_loop_label}")
        self.emitter.emit("PUSHF 0.0")
        self.emitter.emit(f"JUMP {final_label}")

        self.emitter.label(init_loop_label)

        # x = n / 2.0
        self.emit_load_temp(n_slot)
        self.emitter.emit("PUSHF 2.0")
        self.emitter.emit("FDIV")
        self.emit_store_temp(x_slot)

        # i = 0
        self.emitter.emit("PUSHI 0")
        self.emit_store_temp(i_slot)

        self.emitter.label(loop_label)

        # while i < 10
        self.emit_load_temp(i_slot)
        self.emitter.emit("PUSHI 10")
        self.emitter.emit("INF")
        self.emitter.emit(f"JZ {push_result_label}")

        # x = 0.5 * (x + n / x)
        self.emit_load_temp(x_slot)

        self.emit_load_temp(n_slot)
        self.emit_load_temp(x_slot)
        self.emitter.emit("FDIV")

        self.emitter.emit("FADD")
        self.emitter.emit("PUSHF 0.5")
        self.emitter.emit("FMUL")
        self.emit_store_temp(x_slot)

        # i = i + 1
        self.emit_load_temp(i_slot)
        self.emitter.emit("PUSHI 1")
        self.emitter.emit("ADD")
        self.emit_store_temp(i_slot)

        self.emitter.emit(f"JUMP {loop_label}")

        self.emitter.label(push_result_label)
        self.emit_load_temp(x_slot)

        self.emitter.label(final_label)

    def visit_intrinsic_exp(self, node):
        self.require_intrinsic_arity(node, 1)

        value = node.arguments[0]

        x_slot = self.compiler_temp_slot()
        term_slot = self.compiler_temp_slot()
        sum_slot = self.compiler_temp_slot()
        i_slot = self.compiler_temp_slot()

        loop_label = self.new_label("EXPLOOP")
        end_label = self.new_label("EXPEND")

        self.visit_expression(value)

        if self.expression_type(value) == "INTEGER":
            self.emitter.emit("ITOF")

        self.emit_store_temp(x_slot)

        # sum = 1.0
        self.emitter.emit("PUSHF 1.0")
        self.emit_store_temp(sum_slot)

        # term = 1.0
        self.emitter.emit("PUSHF 1.0")
        self.emit_store_temp(term_slot)

        # i = 1
        self.emitter.emit("PUSHI 1")
        self.emit_store_temp(i_slot)

        self.emitter.label(loop_label)

        # while i <= 12
        self.emit_load_temp(i_slot)
        self.emitter.emit("PUSHI 12")
        self.emitter.emit("INFEQ")
        self.emitter.emit(f"JZ {end_label}")

        # term = term * x / i
        self.emit_load_temp(term_slot)
        self.emit_load_temp(x_slot)
        self.emitter.emit("FMUL")

        self.emit_load_temp(i_slot)
        self.emitter.emit("ITOF")
        self.emitter.emit("FDIV")

        self.emit_store_temp(term_slot)

        # sum = sum + term
        self.emit_load_temp(sum_slot)
        self.emit_load_temp(term_slot)
        self.emitter.emit("FADD")
        self.emit_store_temp(sum_slot)

        # i = i + 1
        self.emit_load_temp(i_slot)
        self.emitter.emit("PUSHI 1")
        self.emitter.emit("ADD")
        self.emit_store_temp(i_slot)

        self.emitter.emit(f"JUMP {loop_label}")

        self.emitter.label(end_label)
        self.emit_load_temp(sum_slot)


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
        description="Compile Fortran 77 source code into EWVM assembly.",
        add_help=False,
    )

    parser_args.add_argument(
        "input_file",
        nargs="?",
        help="Fortran source file. If omitted, read from stdin.",
    )

    parser_args.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        help="Output file. If omitted, output to stdout."
    )

    parser_args.add_argument(
        "-O", "--optimize",
        action="store_true",
        default=False,
        help="Enable optimizations."
    )

    parser_args.add_argument(
        "-g", "--debug",
        action="store_true",
        default=False,
        help="Enable debug comments."
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
        help="Skip preprocessing stage."
    )

    parser_args.add_argument(
        "--viz", "--visualize",
        dest="visualize",
        nargs="?",
        const=DEFAULT_VIS_OUTPUT_PATH,
        metavar="OUTPUT",
        help="Generate a Graphviz image of the AST."
    )

    parser_args.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not open the generated AST visualization file. "
             "Only valid with --viz/--visualize."
    )

    parser_args.add_argument(
        "--show-intrinsics",
        action="store_true",
        default=False,
        help="Include intrinsic procedures in verbose semantic info output. "
             "Requires -v/--verbose."
    )

    parser_args.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output during compilation "
             "(e.g. print intermediate AST, semantic info, etc.)"
    )

    parser_args.add_argument(
        "-h", "--help",
        help="Show this help message and exit.",
        action="help"
    )

    args = parser_args.parse_args()

    if args.no_open and not args.visualize:
        parser_args.error("--no-open can only be used with --viz/--visualize")

    if args.show_intrinsics and not args.verbose:
        parser_args.error("--show-intrinsics requires -v/--verbose")

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
        visualize_ast(
            result,
            output_path=args.visualize,
            optimized=False,
            open_result=not args.no_open
        )

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
            visualize_ast(
                result,
                output_path=args.visualize,
                optimized=True,
                open_result=not args.no_open
            )

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
