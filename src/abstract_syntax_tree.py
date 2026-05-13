from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.modules["abstract_syntax_tree"] = sys.modules["__main__"]

from dataclasses import dataclass
from typing import Union

from graphviz import Digraph


DEFAULT_VISUALIZE_OUTPUT_PATH = "/tmp/ast.png"


###
# AST node definitions
###

@dataclass(frozen=True)
class File:
    filename: str
    program_units: list[ProgramUnit]


###
# Program units
###

@dataclass(frozen=True)
class Program:
    name: str
    statements: list[Statement]


@dataclass(frozen=True)
class Subroutine:
    name: str
    arguments: list[str]
    statements: list[Statement]


@dataclass(frozen=True)
class Function:
    return_type: str
    name: str
    arguments: list[str]
    statements: list[Statement]


@dataclass(frozen=True)
class Block:
    statements: list[Statement]


###
# Statements
###

@dataclass(frozen=True)
class Declare:
    type_name: str
    declarators: list[Declarator]


@dataclass(frozen=True)
class Assign:
    target: Variable
    value: Expression


@dataclass(frozen=True)
class Print:
    items: list[Expression]


@dataclass(frozen=True)
class Read:
    variables: list[Variable]


@dataclass(frozen=True)
class Write:
    items: list[Expression]


@dataclass(frozen=True)
class Label:
    number: int
    statement: Statement


@dataclass(frozen=True)
class If:
    condition: Expression
    then_branch: list[Statement]
    else_branch: list[Statement] | None


@dataclass(frozen=True)
class Do:
    end_label: int
    variable: str
    start: Expression
    end: Expression
    body: list[Statement]
    terminator_label: int


@dataclass(frozen=True)
class Goto:
    label: int


@dataclass(frozen=True)
class Stop:
    pass


@dataclass(frozen=True)
class Return:
    pass


@dataclass(frozen=True)
class Continue:
    pass


@dataclass(frozen=True)
class CallStatement:
    name: str
    arguments: list[Expression]


###
# Declarations
###

@dataclass(frozen=True)
class VarDeclarator:
    name: str


@dataclass(frozen=True)
class ArrayDeclarator:
    name: str
    dimensions: list[Expression]


###
# Expressions
###

@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class ArrayRef:
    name: str
    indices: list[Expression]


@dataclass(frozen=True)
class Double:
    value: float


@dataclass(frozen=True)
class Real:
    value: float


@dataclass(frozen=True)
class Integer:
    value: int


@dataclass(frozen=True)
class String:
    value: str


@dataclass(frozen=True)
class Bool:
    value: bool


@dataclass(frozen=True)
class Arith:
    op: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Rel:
    op: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Logical:
    op: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Unary:
    op: str
    value: Expression


@dataclass(frozen=True)
class Call:
    name: str
    arguments: list[Expression]


Declarator = Union[
    VarDeclarator,
    ArrayDeclarator,
]

Variable = Union[
    Var,
    ArrayRef,
]

Expression = Union[
    Variable,
    Double,
    Real,
    Integer,
    String,
    Bool,
    Arith,
    Rel,
    Logical,
    Unary,
    Call,
]

Statement = Union[
    Declare,
    Assign,
    Print,
    Read,
    Write,
    Label,
    If,
    Do,
    Goto,
    Stop,
    Return,
    Continue,
    CallStatement,
]

ProgramUnit = Union[
    Program,
    Subroutine,
    Function,
    Block,
]

AST = File


###
# AST tree helpers
###

def _node_label(node) -> str:
    if isinstance(node, File):
        return f"file: {node.filename}"

    if isinstance(node, Program):
        return f"program: {node.name}"

    if isinstance(node, Subroutine):
        return f"subroutine: {node.name}"

    if isinstance(node, Function):
        return f"function: {node.return_type} {node.name}"

    if isinstance(node, Block):
        return "block"

    if isinstance(node, Declare):
        return f"declare: {node.type_name}"

    if isinstance(node, VarDeclarator):
        return f"var-decl: {node.name}"

    if isinstance(node, ArrayDeclarator):
        return f"array-decl: {node.name}"

    if isinstance(node, Assign):
        return "assign"

    if isinstance(node, Var):
        return f"var: {node.name}"

    if isinstance(node, ArrayRef):
        return f"array-ref: {node.name}"

    if isinstance(node, Double):
        return f"double number: {node.value}"

    if isinstance(node, Real):
        return f"real number: {node.value}"

    if isinstance(node, Integer):
        return f"integer number: {node.value}"

    if isinstance(node, String):
        return f"string: {node.value!r}"

    if isinstance(node, Bool):
        return f"bool: {node.value}"

    if isinstance(node, Print):
        return "print"

    if isinstance(node, Read):
        return "read"

    if isinstance(node, Write):
        return "write"

    if isinstance(node, Label):
        return f"label: {node.number}"

    if isinstance(node, If):
        return "if"

    if isinstance(node, Do):
        return f"do: {node.variable}, end label {node.end_label}"

    if isinstance(node, Goto):
        return f"goto: {node.label}"

    if isinstance(node, Stop):
        return "stop"

    if isinstance(node, Return):
        return "return"

    if isinstance(node, Continue):
        return "continue"

    if isinstance(node, CallStatement):
        return f"call-stmt: {node.name}"

    if isinstance(node, Call):
        return f"call: {node.name}"

    if isinstance(node, Arith):
        return f"arith: {node.op}"

    if isinstance(node, Rel):
        return f"rel: {node.op}"

    if isinstance(node, Logical):
        return f"logical: {node.op}"

    if isinstance(node, Unary):
        return f"unary: {node.op}"

    raise TypeError(f"Unsupported AST node: {node!r}")


def _node_children(node):
    if isinstance(node, File):
        return node.program_units

    if isinstance(node, Program):
        return node.statements

    if isinstance(node, Subroutine):
        return [Var(name) for name in node.arguments] + node.statements

    if isinstance(node, Function):
        return [Var(name) for name in node.arguments] + node.statements

    if isinstance(node, Block):
        return node.statements

    if isinstance(node, Declare):
        return node.declarators

    if isinstance(node, VarDeclarator):
        return []

    if isinstance(node, ArrayDeclarator):
        return node.dimensions

    if isinstance(node, Assign):
        return [node.target, node.value]

    if isinstance(node, Var):
        return []

    if isinstance(node, ArrayRef):
        return node.indices

    if isinstance(node, Double):
        return []

    if isinstance(node, Real):
        return []

    if isinstance(node, Integer):
        return []

    if isinstance(node, String):
        return []

    if isinstance(node, Bool):
        return []

    if isinstance(node, Print):
        return node.items

    if isinstance(node, Read):
        return node.variables

    if isinstance(node, Write):
        return node.items

    if isinstance(node, Label):
        return [node.statement]

    if isinstance(node, If):
        children = [node.condition, Block(node.then_branch)]
        if node.else_branch is not None:
            children.append(Block(node.else_branch))
        return children

    if isinstance(node, Do):
        return [
            Var(node.variable),
            node.start,
            node.end,
            Block(node.body),
            Label(node.terminator_label, Continue()),
        ]

    if isinstance(node, Goto):
        return []

    if isinstance(node, Stop):
        return []

    if isinstance(node, Return):
        return []

    if isinstance(node, Continue):
        return []

    if isinstance(node, CallStatement):
        return node.arguments

    if isinstance(node, Call):
        return node.arguments

    if isinstance(node, Arith):
        return [node.left, node.right]

    if isinstance(node, Rel):
        return [node.left, node.right]

    if isinstance(node, Logical):
        return [node.left, node.right]

    if isinstance(node, Unary):
        return [node.value]

    raise TypeError(f"Unsupported AST node: {node!r}")


###
# Pretty printing
###

def pretty_print(ast: AST) -> None:
    """
    Print the AST as a terminal tree.

    Arguments:
        ast(AST): The AST to print.
    """

    def walk(node, prefix="", is_last=True, is_root=False):
        label = _node_label(node)

        if is_root:
            print(label)
        else:
            connector = "└── " if is_last else "├── "
            print(prefix + connector + label)

        children = _node_children(node)

        if is_root:
            child_prefix = ""
        else:
            child_prefix = prefix + ("    " if is_last else "│   ")

        for index, child in enumerate(children):
            walk(
                child,
                prefix=child_prefix,
                is_last=index == len(children) - 1,
                is_root=False,
            )

    walk(ast, is_root=True)


###
# Graphviz visualization
###

def visualize(ast: AST, output_path: str = DEFAULT_VISUALIZE_OUTPUT_PATH) -> str:
    """
    Generate an AST image using Graphviz.

    Arguments:
        ast(AST): The AST to visualize.
        output_path(str): The file path to save the image.
                          Default: /tmp/ast.png

    Returns:
        str: The generated output file path.
    """

    dot = Digraph("AST")

    dot.attr("node", shape="box")
    dot.attr(rankdir="TB")

    counter = 0

    def new_id():
        nonlocal counter
        node_id = f"node_{counter}"
        counter += 1
        return node_id

    def escape_label(label: str) -> str:
        return (
            label.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )

    def build(node, parent_id=None):
        node_id = new_id()
        label = escape_label(_node_label(node))

        dot.node(node_id, label)

        if parent_id is not None:
            dot.edge(parent_id, node_id)

        for child in _node_children(node):
            build(child, node_id)

        return node_id

    build(ast)

    if "." in output_path:
        filename, file_format = output_path.rsplit(".", 1)
    else:
        filename = output_path
        file_format = "png"

    output_file = dot.render(filename, format=file_format, cleanup=True)

    # print(f"Generated AST image: {output_file}")
    return output_file
