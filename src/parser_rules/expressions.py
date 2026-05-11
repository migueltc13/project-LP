import abstract_syntax_tree as ast

# Expressions

# We start with the lowest precedence level (logical OR)
# and work our way down to the highest (primary expressions)
def p_expression(p):
    """
    expression : logical_or
    """
    # AST node: pass the logical OR expression up the tree
    p[0] = p[1]


def p_logical_or(p):
    """
    logical_or : logical_or OR continuation_opt logical_and
               | logical_and
    """
    # AST node: if it's a logical OR, create a node with the operator and operands
    # Otherwise, just pass the logical AND expression up the tree
    if len(p) == 5:
        p[0] = ast.Logical(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_logical_and(p):
    """
    logical_and : logical_and AND continuation_opt relational
                | relational
    """
    # AST node: if it's a logical AND, create a node with the operator and operands
    # Otherwise, just pass the relational expression up the tree
    if len(p) == 5:
        p[0] = ast.Logical(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_relational(p):
    """
    relational : additive EQ continuation_opt additive
               | additive NE continuation_opt additive
               | additive LT continuation_opt additive
               | additive LE continuation_opt additive
               | additive GT continuation_opt additive
               | additive GE continuation_opt additive
               | additive
    """
    # AST node: if it's a relational operator, create a node with the operator and operands
    # Otherwise, just pass the additive expression up the tree
    if len(p) == 5:
        p[0] = ast.Rel(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_additive(p):
    """
    additive : additive PLUS continuation_opt multiplicative
             | additive MINUS continuation_opt multiplicative
             | multiplicative
    """
    # AST node: if it's an additive operator, create a node with the operator and operands
    # Otherwise, just pass the multiplicative expression up the tree
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_multiplicative(p):
    """
    multiplicative : multiplicative ASTERISK continuation_opt unary
                   | multiplicative DIVIDE continuation_opt unary
                   | unary
    """
    # AST node: if it's a multiplicative operator, create a node with the operator and operands
    # Otherwise, just pass the unary expression up the tree
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_unary(p):
    """
    unary : PLUS continuation_opt unary
          | MINUS continuation_opt unary
          | NOT continuation_opt unary
          | power
    """
    # AST node: if it's a unary operator, create a node with the operator and operand
    # Otherwise, just pass the power expression up the tree
    if len(p) == 4:
        if p[1] == '+':
            p[0] = ast.Unary('+', p[3])
        elif p[1] == '-':
            p[0] = ast.Unary('-', p[3])
        else:
            p[0] = ast.Unary('not', p[3])
    else:
        p[0] = p[1]

# Power operator is right-associative, so it's handled separately
def p_power(p):
    """
    power : primary POWER continuation_opt power
          | primary
    """
    # AST node: if it's a power operator, create a node with the operator and operands
    # Otherwise, just pass the primary expression up the tree
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]

# Optional continuation operator for line continuations in expressions
def p_continuation_opt(p):
    """
    continuation_opt : '&'
                     | empty
    """
    p[0] = p[1]

# Primary expressions include literals, variables, function calls, and
# parenthesized expressions
def p_primary_group(p):
    """
    primary : '(' expression ')'
    """
    # AST node: just pass the expression up the tree, ignoring the parentheses
    p[0] = p[2]


def p_primary_number(p):
    """
    primary : NUMBER
    """
    # AST node: create a node for the number literal
    p[0] = ast.Number(p[1])


def p_primary_string(p):
    """
    primary : STRING
    """
    # AST node: create a node for the string literal
    p[0] = ast.String(p[1])


def p_primary_boolean(p):
    """
    primary : TRUE
            | FALSE
    """
    # AST node: create a node for the boolean literal
    p[0] = ast.Bool(p.slice[1].type == "TRUE")


# Primary identifiers can be variables or function calls
def p_primary_identifier(p):
    """
    primary : IDENTIFIER
            | IDENTIFIER '(' argument_list_opt ')'
    """
    # AST node: if it's a function call, create a node with the function name and arguments
    # Otherwise, just create a node for the variable
    if len(p) == 2:
        p[0] = ast.Var(p[1])
    else:
        p[0] = ast.Call(p[1], p[3])

# Optional argument list for function calls
def p_argument_list_opt(p):
    """
    argument_list_opt : argument_list
                      | empty
    """
    # AST node: if there's an argument list, pass it up the tree;
    # Otherwise, use an empty list
    p[0] = [] if p[1] is None else p[1]

# Argument list is compose of one or more expressions separated by commas
def p_argument_list(p):
    """
    argument_list : expression
                  | argument_list ',' expression
    """
    # AST node: if it's a list of arguments, create a list of expressions
    # Otherwise, just pass the single expression up the tree
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
