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

    def comment(self, text: str) -> None:
        if self.debug:
            self.emit(f"// {text}")

    def label(self, name: str) -> None:
        self.emit(f"{name}:")

    def render(self) -> str:
        return "\n".join(self.instructions) + "\n"


class MemoryLayout:
    def __init__(self):
        self.global_slots: dict[str, int] = {}

    def allocate_global(self, name: str) -> int:
        if name not in self.global_slots:
            self.global_slots[name] = len(self.global_slots)
        return self.global_slots[name]

    def global_slot(self, name: str) -> int:
        try:
            return self.global_slots[name]
        except KeyError:
            raise CodeGenerationError(f"internal error: variable {name!r} has "
                                      "no slot")

# TODO(codegen): Add type-directed expression generation using semantic/type info.
# TODO(codegen): Insert numeric conversions such as ITOF/FTOI.
# TODO(codegen): Support arrays with ALLOC/LOAD/STORE.
# TODO(codegen): Support IF/ELSE via JZ/JUMP labels.
# TODO(codegen): Support WRITE statement.
# TODO(codegen): Support function/subroutine generation and CALL convention.
# TODO(codegen): Support intrinsic functions.
# TODO(codegen): Support power operator (**).
# TODO(codegen): Support DO step expressions and negative-step loops.
# TODO(codegen): Define CHARACTER storage model.
# TODO(codegen): Add local frame layout for procedures.

class EWVMGenerator:
    def __init__(self, semantic_info, *, debug: bool = False):
        self.semantic_info = semantic_info
        self.emitter = EWVMEmitter(debug=debug)
        self.layout = MemoryLayout()
        self.current_scope = None
        self.loop_counter = 0
        self.pending_do_by_label = {}

    def generate(self, tree) -> str:
        self.visit_file(tree)
        return self.emitter.render()

    def allocate_scope(self, scope) -> None:
        for name in scope.variable_order:
            self.layout.allocate_global(name)

    def find_scope(self, name: str, kind: str):
        for scope in self.semantic_info.scopes:
            if scope.name == name and scope.kind == kind:
                return scope
        raise CodeGenerationError("internal error: missing semantic scope "
                                  f"{kind} {name}")

    def visit_file(self, node):
        if not isinstance(node, ast.File):
            raise CodeGenerationError(f"expected File node, got {node!r}")

        programs = [unit for unit in node.program_units
                    if isinstance(unit, ast.Program)]

        if not programs:
            raise CodeGenerationError("code generation requires a PROGRAM unit")

        program = programs[0]
        self.visit_program(program)

    def visit_program(self, node):
        self.current_scope = self.find_scope(node.name, "program")
        self.allocate_scope(self.current_scope)

        self.emitter.comment(f"program {node.name}")
        self.emitter.emit("START")

        if self.layout.global_slots:
            self.emitter.comment("global variable storage")
            self.emitter.emit(f"PUSHN {len(self.layout.global_slots)}")

        for statement in node.statements:
            self.visit_statement(statement)

        self.emitter.emit("STOP")

    def visit_statement(self, node):
        if isinstance(node, ast.Declare):
            return

        if isinstance(node, ast.Assign):
            self.visit_assign(node)
            return

        if isinstance(node, ast.Print):
            self.visit_print(node)
            return

        if isinstance(node, ast.Read):
            self.visit_read(node)
            return

        if isinstance(node, ast.Label):
            self.visit_label(node)
            return

        if isinstance(node, ast.Goto):
            self.emitter.emit(f"JUMP L{node.label}")
            return

        if isinstance(node, ast.Stop):
            self.emitter.emit("STOP")
            return

        if isinstance(node, ast.Continue):
            self.emitter.emit("NOP")
            return

        if isinstance(node, ast.Do):
            self.visit_do(node)
            return

        raise CodeGenerationError("unsupported statement for EWVM generation: "
                                  f"{node!r}")

    def visit_assign(self, node):
        if not isinstance(node.target, ast.Var):
            raise CodeGenerationError("array assignment is not supported yet")

        self.visit_expression(node.value)

        slot = self.layout.global_slot(node.target.name)
        self.emitter.comment(f"{node.target.name} = ...")
        self.emitter.emit(f"STOREG {slot}")

    def visit_expression(self, node):
        if isinstance(node, ast.Integer):
            self.emitter.emit(f"PUSHI {node.value}")
            return

        if isinstance(node, ast.Real):
            self.emitter.emit(f"PUSHF {node.value}")
            return

        if isinstance(node, ast.Double):
            # EWVM appears to have one real/float stack type.
            self.emitter.emit(f"PUSHF {node.value}")
            return

        if isinstance(node, ast.String):
            self.emitter.emit(f"PUSHS {node.value!r}")
            return

        if isinstance(node, ast.Bool):
            self.emitter.emit(f"PUSHI {1 if node.value else 0}")
            return

        if isinstance(node, ast.Var):
            slot = self.layout.global_slot(node.name)
            self.emitter.emit(f"PUSHG {slot}")
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

        raise CodeGenerationError("unsupported expression for EWVM generation: "
                                  f"{node!r}")

    def expression_is_floatish(self, node) -> bool:
        if isinstance(node, (ast.Real, ast.Double)):
            return True

        if isinstance(node, ast.Arith):
            return self.expression_is_floatish(node.left) or \
                self.expression_is_floatish(node.right)

        return False

    def visit_arith(self, node):
        self.visit_expression(node.left)
        self.visit_expression(node.right)

        is_float = self.expression_is_floatish(node)

        if node.op == "+":
            self.emitter.emit("FADD" if is_float else "ADD")
        elif node.op == "-":
            self.emitter.emit("FSUB" if is_float else "SUB")
        elif node.op == "*":
            self.emitter.emit("FMUL" if is_float else "MUL")
        elif node.op == "/":
            self.emitter.emit("FDIV" if is_float else "DIV")
        elif node.op == "**":
            raise CodeGenerationError("power operator is not supported yet")
        else:
            raise CodeGenerationError("unsupported arithmetic operator "
                                      f"{node.op!r}")

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
            raise CodeGenerationError("unsupported relational operator "
                                      f"{node.op!r}")

    def visit_logical(self, node):
        self.visit_expression(node.left)
        self.visit_expression(node.right)

        if node.op == ".AND.":
            self.emitter.emit("AND")
        elif node.op == ".OR.":
            self.emitter.emit("OR")
        else:
            raise CodeGenerationError("unsupported logical operator "
                                      f"{node.op!r}")

    def visit_unary(self, node):
        if node.op == "+":
            self.visit_expression(node.value)
            return

        if node.op == "-":
            self.emitter.emit("PUSHI 0")
            self.visit_expression(node.value)
            self.emitter.emit("SUB")
            return

        if node.op == ".NOT.":
            self.visit_expression(node.value)
            self.emitter.emit("NOT")
            return

        raise CodeGenerationError(f"unsupported unary operator {node.op!r}")

    def variable_type(self, name: str) -> str:
        if self.current_scope is None:
            return "UNKNOWN"

        info = self.current_scope.variables.get(name)
        if info is None:
            return "UNKNOWN"

        return info.type_name

    def expression_type_hint(self, node) -> str:
        if isinstance(node, ast.Integer):
            return "INTEGER"
        if isinstance(node, (ast.Real, ast.Double)):
            return "REAL"
        if isinstance(node, ast.String):
            return "CHARACTER"
        if isinstance(node, ast.Bool):
            return "LOGICAL"
        if isinstance(node, ast.Var):
            return self.variable_type(node.name)
        if isinstance(node, ast.Arith):
            if self.expression_is_floatish(node):
                return "REAL"
            return "INTEGER"

        return "UNKNOWN"

    def visit_print(self, node):
        for item in node.items:
            self.visit_expression(item)

            type_name = self.expression_type_hint(item)

            if type_name == "CHARACTER":
                self.emitter.emit("WRITES")
            elif type_name in {"REAL", "DOUBLE"}:
                self.emitter.emit("WRITEF")
            else:
                self.emitter.emit("WRITEI")

        self.emitter.emit("WRITELN")

    def visit_read(self, node):
        for variable in node.variables:
            if not isinstance(variable, ast.Var):
                raise CodeGenerationError("array READ is not supported yet")

            type_name = self.variable_type(variable.name)

            self.emitter.emit("READ")

            if type_name == "INTEGER":
                self.emitter.emit("ATOI")
            elif type_name in {"REAL", "DOUBLE"}:
                self.emitter.emit("ATOF")
            elif type_name == "CHARACTER":
                pass
            else:
                raise CodeGenerationError(
                    f"READ for variable {variable.name!r} "
                    f"has unsupported type {type_name!r}"
                )

            slot = self.layout.global_slot(variable.name)
            self.emitter.emit(f"STOREG {slot}")

    def visit_label(self, node):
        loop_info = self.pending_do_by_label.get(node.number)

        if loop_info is not None and isinstance(node.statement, ast.Continue):
            var_name = loop_info["variable"]
            slot = self.layout.global_slot(var_name)

            self.emitter.emit(f"PUSHG {slot}")
            self.emitter.emit("PUSHI 1")
            self.emitter.emit("ADD")
            self.emitter.emit(f"STOREG {slot}")
            self.emitter.emit(f"JUMP {loop_info['start_label']}")

            self.emitter.label(f"L{node.number}")
            self.visit_statement(node.statement)

            del self.pending_do_by_label[node.number]
            return

        self.emitter.label(f"L{node.number}")
        self.visit_statement(node.statement)

    def visit_do(self, node):
        loop_id = self.loop_counter
        self.loop_counter += 1

        start_label = f"L_DO_START_{loop_id}"

        self.visit_expression(node.start)
        self.emitter.emit(f"STOREG {self.layout.global_slot(node.variable)}")

        self.emitter.label(start_label)

        self.emitter.emit(f"PUSHG {self.layout.global_slot(node.variable)}")
        self.visit_expression(node.end)
        self.emitter.emit("SUP")
        self.emitter.emit(f"JZ L_DO_BODY_{loop_id}")
        self.emitter.emit(f"JUMP L{node.end_label}")

        self.emitter.label(f"L_DO_BODY_{loop_id}")

        self.pending_do_by_label[node.end_label] = {
            "variable": node.variable,
            "start_label": start_label,
        }


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
    from pathlib import Path

    from common import read_input, detect_source_format, open_file, write_output
    from preprocessor import preprocess
    from lexer import lexer, clear_lexer_state
    from parser import parser, clear_parser_state
    from semantics import semantic_checks
    from semantics.semantic_info import print_semantic_info
    from optimizations import optimizations
    from abstract_syntax_tree import (
        pretty_print,
        visualize,
        DEFAULT_VIS_OUTPUT_PATH
    )

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
        "--visualize", "--vis",
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

    lexer.source_lines = source_lines
    lexer.source_filename = source_filename

    parser.source_lines = source_lines
    parser.source_filename = source_filename

    # Parse the input data
    result = parser.parse(source_data, lexer=lexer, debug=False)

    # Propagate lexer errors to parser error state,
    # since the lexer doesn't exit on error
    if lexer.has_error:
        parser.has_error = True

    if result is None:
        sys.exit(1)

    # Semantic checks
    semantic_info = semantic_checks(parser, ast=result)

    # Check for semantic errors before proceeding
    if parser.has_error:
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
        try:
            visualize_file = visualize(result, output_path=args.visualize)
            print(f"\nAST visualization generated at: {visualize_file}")
            open_file(visualize_file)
        except Exception as e:
            print(f"AST Visualization error: {e}", file=sys.stderr)

    # TODO optimizations here (e.g. constant folding, dead code elimination, etc.)
    if args.optimize:
        # TODO Check if optimizations can use (and enjoy) semantic_info
        result = optimizations(result)
        # TODO perhaps code optimization will also need to propagate changes
        # to semantic_info in this case we could re-run:
        # semantic_info = semantic_checks(parser, ast=result)
        # NOTE this can be a bit expensive so we have to check of it's worth it
        # But ensure new code generation receives the updated semantic_info for
        # memory allocation, etc.
        # Alternatively we could have optimizations return both the optimized
        # AST and updated semantic_info.

        # Verbose output of optimized AST
        if args.verbose:
            print("\nOptimized AST:\n==============\n")
            pretty_print(result)

        # Visualize optimized AST
        if args.visualize:
            try:
                vis_path = Path(args.visualize)
                output_path = str(vis_path.with_name(
                    f"{vis_path.stem}_optimized{vis_path.suffix}"
                ))
                optimized_vis_file = visualize(result, output_path=output_path)
                print("\nOptimized AST visualization generated at: "
                      f"{optimized_vis_file}")
                open_file(optimized_vis_file)
            except Exception as e:
                print(f"Optimized AST Visualization error: {e}",
                      file=sys.stderr)

    # Generate EWVM assembly code from the AST and semantic information
    try:
        assembly = generate(result, semantic_info, debug=args.debug)
    except CodeGenerationError as e:
        print(f"Code generation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Write output assembly code to file or stdout
    try:
        write_output(args.output, assembly)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
