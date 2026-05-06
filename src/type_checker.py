from dataclasses import dataclass

###
# Type Checker
# Used after parsing to ensure semantic correctness of the program
# Checks include:
# - Type compatibility in assignments and expressions
# - Proper use of variables (e.g., not using arrays without indices)
# - Validity of function and subroutine calls
# - Proper use of control structures (e.g., DO loops, IF statements)
###


class SemanticError(Exception):
    pass


##
# Basic type system and utilities for type checking
##

NUMERIC_TYPES = {"INTEGER", "REAL", "DOUBLE"}
SCALAR_TYPES = NUMERIC_TYPES | {"LOGICAL", "CHARACTER", "UNKNOWN"}


def is_numeric(type_name):
    return type_name in NUMERIC_TYPES


def is_compatible_type(expected_type, actual_type):
    if expected_type == "UNKNOWN" or actual_type == "UNKNOWN":
        return True
    if expected_type == actual_type:
        return True
    if expected_type in {"REAL", "DOUBLE"} and actual_type == "INTEGER":
        return True
    return False


def widest_numeric_type(left_type, right_type):
    if "DOUBLE" in {left_type, right_type}:
        return "DOUBLE"
    if "REAL" in {left_type, right_type}:
        return "REAL"
    if left_type == "INTEGER" and right_type == "INTEGER":
        return "INTEGER"
    return "UNKNOWN"

###
# Type Checker Implementation
# Traverses the AST and checks for semantic correctness based
# on the rules of Fortran 77.
###

@dataclass
class Symbol:
    type_name: str
    kind: str = "scalar"
    dimensions: int = 0


class TypeChecker:
    def __init__(self):
        self.scope = {}

    def check(self, node):
        if node is None:
            return

        if isinstance(node, list):
            for item in node:
                self.check(item)
            return

        if isinstance(node, str):
            return

        if not isinstance(node, tuple) or not node:
            raise SemanticError(f"Unsupported AST node: {node!r}")

        node_type = node[0]

        if node_type == "program":
            self.check_program(node)

        elif node_type == "subroutine":
            self.check_subroutine(node)

        elif node_type == "function":
            self.check_function(node)

        elif node_type == "block":
            self.check(node[1])

        elif node_type == "label":
            self.check(node[2])

        elif node_type == "declare":
            self.check_declaration(node[1], node[2])

        elif node_type == "assign":
            self.check_assignment(node[1], node[2])

        elif node_type in {"print", "write"}:
            for expression in node[1]:
                self.infer_expression(expression)

        elif node_type == "read":
            for variable in node[1]:
                self.check_target(variable)

        elif node_type == "if":
            condition_type = self.infer_expression(node[1])
            if condition_type not in {"LOGICAL", "UNKNOWN"}:
                raise SemanticError("IF condition must be logical")
            self.check(node[2])
            if node[3] is not None:
                self.check(node[3])

        elif node_type == "do":
            self.check_do_loop(node)

        elif node_type == "call":
            self.check_call(node[1], node[2])

        elif node_type in {"goto", "stop", "return", "CONTINUE"}:
            return
        else:
            raise SemanticError(f"Unsupported AST node type: {node_type}")

    # Check Program: Set up a new scope for the program and check its body
    def check_program(self, node):
        previous_scope = self.scope
        self.scope = {}
        self.check(node[2])
        self.scope = previous_scope

    # Check Subroutine: Set up a new scope for the subroutine, declare its
    # arguments, and check its body
    def check_subroutine(self, node):
        previous_scope = self.scope
        self.scope = {}
        for argument in node[2]:
            self.declare(argument, "UNKNOWN")
        self.check(node[3])
        self.scope = previous_scope

    # Check Function: Set up a new scope for the function, declare its
    # return type
    def check_function(self, node):
        previous_scope = self.scope
        self.scope = {}
        self.declare(node[2], node[1])
        for argument in node[3]:
            self.declare(argument, "UNKNOWN")
        self.check(node[4])
        self.scope = previous_scope

    # Check Declaration: Declare variables and arrays in the current scope, checking
    # array dimensions for correctness
    def check_declaration(self, type_name, declarators):
        for declarator in declarators:
            if isinstance(declarator, tuple) and declarator[0] == "array":
                array_name = declarator[1]
                dimensions = declarator[2]
                for dimension in dimensions:
                    dimension_type = self.infer_expression(dimension)
                    if dimension_type not in {"INTEGER", "UNKNOWN"}:
                        raise SemanticError(
                            f"Array dimension for '{array_name}' must be integer"
                        )
                self.declare(array_name, type_name, kind="array", dimensions=len(dimensions))
            else:
                self.declare(declarator, type_name)

    # Check Assignment: Ensure the target of the assignment is valid and that the
    # expression being assigned is compatible with the target's type
    def check_assignment(self, target, expression):
        target_type = self.check_target(target)
        expression_type = self.infer_expression(expression)
        if not is_compatible_type(target_type, expression_type):
            raise SemanticError(
                f"Cannot assign {expression_type} to {target_type}"
            )

    # Check DO Loop: Ensure the loop variable is numeric, the bounds are scalar
    # and numeric, and check the body of the loop for semantic correctness
    def check_do_loop(self, node):
        _, _, loop_variable, start_expression, end_expression, body, _ = node

        loop_type = self.check_target(("var", loop_variable))
        if loop_type not in {"INTEGER", "REAL", "DOUBLE", "UNKNOWN"}:
            raise SemanticError("DO loop variable must be numeric")

        start_type = self.infer_expression(start_expression)
        end_type = self.infer_expression(end_expression)
        if start_type not in SCALAR_TYPES or end_type not in SCALAR_TYPES:
            raise SemanticError("DO loop bounds must be scalar expressions")
        if not is_numeric(start_type) and start_type != "UNKNOWN":
            raise SemanticError("DO loop lower bound must be numeric")
        if not is_numeric(end_type) and end_type != "UNKNOWN":
            raise SemanticError("DO loop upper bound must be numeric")

        self.check(body)

    # Check Call: Ensure the called procedure is declared and that the arguments
    # are compatible with the procedure's parameters
    def check_call(self, name, arguments):
        for argument in arguments:
            self.infer_expression(argument)

        symbol = self.scope.get(name)
        if symbol is not None and symbol.kind == "array":
            if len(arguments) != symbol.dimensions:
                raise SemanticError(
                    f"'{name}' expects {symbol.dimensions} indices"
                )
            return self.check_target(("array_ref", name, arguments))

        return symbol.type_name if symbol is not None else "UNKNOWN"

    # Check Target: Ensure the target of an assignment is valid (either a
    # variable or an array reference)
    def check_target(self, node):
        if not isinstance(node, tuple):
            raise SemanticError(f"Invalid assignment target: {node!r}")

        node_type = node[0]
        if node_type == "var":
            symbol = self.resolve(node[1])
            if symbol.kind == "array":
                raise SemanticError(f"'{node[1]}' is an array and needs indices")
            return symbol.type_name

        if node_type == "array_ref":
            symbol = self.resolve(node[1])
            if symbol.kind != "array":
                raise SemanticError(f"'{node[1]}' is not an array")
            if len(node[2]) != symbol.dimensions:
                raise SemanticError(f"'{node[1]}' expects {symbol.dimensions} indices")
            for index_expression in node[2]:
                index_type = self.infer_expression(index_expression)
                if index_type not in {"INTEGER", "UNKNOWN"}:
                    raise SemanticError("Array indices must be integers")
            return symbol.type_name

        raise SemanticError(f"Invalid assignment target: {node!r}")

    # Infer Expression: Determine the type of an expression based on its
    # structure and the types of its components, checking for type compatibility
    # in the process
    def infer_expression(self, node):
        if isinstance(node, tuple):
            node_type = node[0]

            if node_type == "number":
                return "REAL" if isinstance(node[1], float) else "INTEGER"

            if node_type == "string":
                return "CHARACTER"

            if node_type == "bool":
                return "LOGICAL"

            if node_type == "var" or node_type == "array_ref":
                return self.check_target(node)

            if node_type == "call":
                return self.check_call(node[1], node[2])

            if node_type == "uplus" or node_type == "uminus":
                operand_type = self.infer_expression(node[1])
                if operand_type not in {"UNKNOWN"} and not is_numeric(operand_type):
                    raise SemanticError("Unary arithmetic operators require numeric operands")
                return operand_type

            if node_type == "not":
                operand_type = self.infer_expression(node[1])
                if operand_type not in {"UNKNOWN", "LOGICAL"}:
                    raise SemanticError("NOT requires a logical operand")
                return "LOGICAL"

            if node_type == "arith":
                left_type = self.infer_expression(node[2])
                right_type = self.infer_expression(node[3])
                if left_type not in {"UNKNOWN"} and not is_numeric(left_type):
                    raise SemanticError("Arithmetic operands must be numeric")
                if right_type not in {"UNKNOWN"} and not is_numeric(right_type):
                    raise SemanticError("Arithmetic operands must be numeric")
                return widest_numeric_type(left_type, right_type)

            if node_type == "logical":
                left_type = self.infer_expression(node[2])
                right_type = self.infer_expression(node[3])
                if left_type not in {"UNKNOWN", "LOGICAL"}:
                    raise SemanticError("Logical operands must be logical")
                if right_type not in {"UNKNOWN", "LOGICAL"}:
                    raise SemanticError("Logical operands must be logical")
                return "LOGICAL"

            if node_type == "rel":
                left_type = self.infer_expression(node[2])
                right_type = self.infer_expression(node[3])
                if left_type == "UNKNOWN" or right_type == "UNKNOWN":
                    return "LOGICAL"
                if is_numeric(left_type) and is_numeric(right_type):
                    return "LOGICAL"
                if left_type == right_type:
                    return "LOGICAL"
                raise SemanticError("Relational operands must have compatible types")

            raise SemanticError(f"Unsupported expression node: {node!r}")

        if isinstance(node, str):
            return "UNKNOWN"

        raise SemanticError(f"Unsupported expression node: {node!r}")

    # Add a symbol to the current scope, checking for conflicting declarations
    def declare(self, name, type_name, kind="scalar", dimensions=0):
        existing = self.scope.get(name)
        new_symbol = Symbol(type_name=type_name, kind=kind, dimensions=dimensions)

        if existing is None:
            self.scope[name] = new_symbol
            return

        if existing.type_name == "UNKNOWN":
            self.scope[name] = new_symbol
            return

        if (
            existing.type_name != type_name
            or existing.kind != kind
            or existing.dimensions != dimensions
        ):
            raise SemanticError(f"Conflicting declaration for '{name}'")

    # Resolve a symbol from the current scope, raising an error if it is not
    # declared
    def resolve(self, name):
        symbol = self.scope.get(name)
        if symbol is None:
            raise SemanticError(f"Use of undeclared identifier '{name}'")
        return symbol


def type_check(ast):
    checker = TypeChecker()
    checker.check(ast)
    return ast