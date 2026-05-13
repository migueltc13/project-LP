import abstract_syntax_tree as ast
from error import get_token_column
from semantics.labels import (
    record_label_definition,
    record_label_reference
)


# Loop grammar used by the parser.

# The numeric label after DO is kept in the AST, and the loop terminator is
# matched directly as a labeled CONTINUE statement.

# The loop body uses its own non-terminal so the parser can stop cleanly at the
# terminating label without touching the lexer or preprocessor.

def p_do_loop(p):
    """
    do_loop : DO INTEGER_NUMBER IDENTIFIER '=' expression ',' expression loop_statements LABEL CONTINUE
    """
    # INFO The numeric label after DO identifies the matching CONTINUE line.
    # TODO Actually check if the label matches the one on the CONTINUE statement

    referenced_label = p[2]
    defined_label = p[9]

    record_label_reference(
        p.parser,
        referenced_label,
        lineno=p.lineno(2),
        col_start=get_token_column(p.slice[2]),
    )

    record_label_definition(
        p.parser,
        defined_label,
        lineno=p.lineno(9),
        col_start=get_token_column(p.slice[9]),
    )

    p[0] = ast.Do(
        end_label=referenced_label,
        variable=p[3],
        start=p[5],
        end=p[7],
        body=p[8],
        terminator_label=defined_label,
    )


def p_loop_statements(p):
    """
    loop_statements : loop_statement loop_statements
                    |
    """
    # AST node: if there are statements, create a list of them;
    # Otherwise, an empty list
    if len(p) == 3:
        p[0] = [p[1]] + p[2]
    else:
        p[0] = []


def p_loop_statement(p):
    """
    loop_statement : nonlabel_statement
    """
    # AST node: just pass the statement up the tree
    p[0] = p[1]
