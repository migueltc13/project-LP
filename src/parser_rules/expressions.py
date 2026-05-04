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
    logical_or : logical_or OR logical_and
               | logical_and
    """
    # AST node: if it's a logical OR, create a node with the operator and operands
    # Otherwise, just pass the logical AND expression up the tree
    if len(p) == 4:
        p[0] = ('logical', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_logical_and(p):
    """
    logical_and : logical_and AND relational
                | relational
    """
    # AST node: if it's a logical AND, create a node with the operator and operands
    # Otherwise, just pass the relational expression up the tree
    if len(p) == 4:
        p[0] = ('logical', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_relational(p):
    """
    relational : additive EQ additive
               | additive NE additive
               | additive LT additive
               | additive LE additive
               | additive GT additive
               | additive GE additive
               | additive
    """
    # AST node: if it's a relational operator, create a node with the operator and operands
    # Otherwise, just pass the additive expression up the tree
    if len(p) == 4:
        p[0] = ('rel', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_additive(p):
    """
    additive : additive PLUS multiplicative
             | additive MINUS multiplicative
             | multiplicative
    """
    # AST node: if it's an additive operator, create a node with the operator and operands
    # Otherwise, just pass the multiplicative expression up the tree
    if len(p) == 4:
        p[0] = ('arith', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_multiplicative(p):
    """
    multiplicative : multiplicative ASTERISK unary
                   | multiplicative DIVIDE unary
                   | unary
    """
    # AST node: if it's a multiplicative operator, create a node with the operator and operands
    # Otherwise, just pass the unary expression up the tree
    if len(p) == 4:
        p[0] = ('arith', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_unary(p):
    """
    unary : PLUS unary
          | MINUS unary
          | NOT unary
          | power
    """
    # AST node: if it's a unary operator, create a node with the operator and operand
    # Otherwise, just pass the power expression up the tree
    if len(p) == 3:
        if p[1] == '+':
            p[0] = ('uplus', p[2])
        elif p[1] == '-':
            p[0] = ('uminus', p[2])
        else:
            p[0] = ('not', p[2])
    else:
        p[0] = p[1]

# Power operator is right-associative, so it's handled separately
def p_power(p):
    """
    power : primary POWER power
          | primary
    """
    # AST node: if it's a power operator, create a node with the operator and operands
    # Otherwise, just pass the primary expression up the tree
    if len(p) == 4:
        p[0] = ('arith', p[2], p[1], p[3])
    else:
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
    p[0] = ('number', p[1])


def p_primary_string(p):
    """
    primary : STRING
    """
    # AST node: create a node for the string literal
    p[0] = ('string', p[1])


def p_primary_boolean(p):
    """
    primary : TRUE
            | FALSE
    """
    # AST node: create a node for the boolean literal
    p[0] = ('bool', p.slice[1].type == 'TRUE')


# Primary identifiers can be variables or function calls
def p_primary_identifier(p):
    """
    primary : IDENTIFIER
            | IDENTIFIER '(' argument_list_opt ')'
    """
    # AST node: if it's a function call, create a node with the function name and arguments
    # Otherwise, just create a node for the variable
    if len(p) == 2:
        p[0] = ('var', p[1])
    else:
        p[0] = ('call', p[1], p[3])

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


def p_empty(p):
    """
    empty :
    """
    p[0] = None