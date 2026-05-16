from __future__ import annotations

from dataclasses import dataclass
from typing import Union, Optional

from graphviz import Digraph


DEFAULT_VIS_OUTPUT_PATH = "/tmp/ast.png"


###
# Source location definition
###

@dataclass(frozen=True)
class SourceLocation:
    lineno: int
    col_start: int
    length: int


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
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Subroutine:
    name: str
    arguments: list[str]
    statements: list[Statement]
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Function:
    return_type: str
    name: str
    arguments: list[str]
    statements: list[Statement]
    location: Optional[SourceLocation] = None


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
    else_branch: Optional[list[Statement]]


@dataclass(frozen=True)
class Do:
    end_label: int
    variable: Var
    start: Expression
    end: Expression
    step: Optional[Expression] = None


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
    location: Optional[SourceLocation] = None


###
# Declarations
###

@dataclass(frozen=True)
class VarDeclarator:
    name: str
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class ArrayDeclarator:
    name: str
    dimensions: list[Expression]
    location: Optional[SourceLocation] = None


###
# Expressions
###

@dataclass(frozen=True)
class Var:
    name: str
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class ArrayRef:
    name: str
    indices: list[Expression]
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Double:
    value: float
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Real:
    value: float
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Integer:
    value: int
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class String:
    value: str
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Bool:
    value: bool
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Arith:
    op: str
    left: Expression
    right: Expression
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Rel:
    op: str
    left: Expression
    right: Expression
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Logical:
    op: str
    left: Expression
    right: Expression
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Unary:
    op: str
    value: Expression
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class Call:
    name: str
    arguments: list[Expression]
    location: Optional[SourceLocation] = None


@dataclass(frozen=True)
class IndexedOrCall:
    name: str
    arguments: list[Expression]
    location: Optional[SourceLocation] = None


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
    IndexedOrCall,
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
        return f"do: {node.variable.name}, end label {node.end_label}"

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

    if isinstance(node, IndexedOrCall):
        return f"indexed-or-call: {node.name}"

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
        children = [
            node.variable,
            node.start,
            node.end
        ]

        if node.step is not None:
            children.append(node.step)

        return children

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

    if isinstance(node, IndexedOrCall):
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
# Source Location extraction helpers
###

def location_from_token(
    token,
    lexdata: Optional[str] = None
) -> SourceLocation:
    from error import get_token_column

    return SourceLocation(
        lineno=token.lineno,
        col_start=get_token_column(token, lexdata),
        length=max(1, getattr(token, "lexeme_length", len(str(token.value)))),
    )


def location_from_parser_token(p, index: int) -> SourceLocation:
    return location_from_token(
        p.slice[index],
        getattr(p.lexer, "lexdata", None),
    )


def _location_from_span(
    start_token,
    end_node,
    lexdata: Optional[str] = None,
) -> SourceLocation:
    from error import get_token_column

    lineno = start_token.lineno
    col_start = get_token_column(start_token, lexdata)

    end_location = getattr(end_node, "location", None)

    if end_location is not None and end_location.lineno == lineno:
        end_col = end_location.col_start + end_location.length
        length = max(1, end_col - col_start)
    else:
        length = max(1, len(str(start_token.value)))

    return SourceLocation(
        lineno=lineno,
        col_start=col_start,
        length=length,
    )


def location_from_parser_span(
    p,
    start_index: int,
    end_node
) -> SourceLocation:
    return _location_from_span(
        p.slice[start_index],
        end_node,
        getattr(p.lexer, "lexdata", None),
    )


def _location_from_children(
    left,
    fallback_token,
    right,
    lexdata: Optional[str] = None,
) -> SourceLocation:
    left_location = getattr(left, "location", None)
    right_location = getattr(right, "location", None)

    if left_location is None:
        return location_from_token(fallback_token, lexdata)

    if (
        right_location is not None
        and right_location.lineno == left_location.lineno
    ):
        end_col = right_location.col_start + right_location.length
        return SourceLocation(
            lineno=left_location.lineno,
            col_start=left_location.col_start,
            length=max(1, end_col - left_location.col_start),
        )

    return left_location


def location_from_parser_children(
    left,
    p,
    fallback_index: int,
    right,
) -> SourceLocation:
    return _location_from_children(
        left,
        p.slice[fallback_index],
        right,
        getattr(p.lexer, "lexdata", None),
    )


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

def visualize(ast: AST, output_path: str = DEFAULT_VIS_OUTPUT_PATH) -> str:
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
    dot.attr(bgcolor="transparent")
    dot.attr("node", shape="box",
             style="filled", fillcolor="lightgray",
             fontname="Courier")
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
