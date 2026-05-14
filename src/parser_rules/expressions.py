import abstract_syntax_tree as ast


# We start with the lowest precedence level (logical OR)
# and work our way down to the highest (primary expressions)
def p_expression(p):
    """
    expression : logical_or
    """
    p[0] = p[1]


def p_logical_or(p):
    """
    logical_or : logical_or OR logical_and
               | logical_and
    """
    if len(p) == 5:
        p[0] = ast.Logical(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_logical_and(p):
    """
    logical_and : logical_and AND relational
                | relational
    """
    if len(p) == 5:
        p[0] = ast.Logical(p[2], p[1], p[4])
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
    if len(p) == 5:
        p[0] = ast.Rel(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_additive(p):
    """
    additive : additive PLUS multiplicative
             | additive MINUS multiplicative
             | multiplicative
    """
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_multiplicative(p):
    """
    multiplicative : multiplicative ASTERISK unary
                   | multiplicative DIVIDE unary
                   | unary
    """
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]


def p_unary(p):
    """
    unary : PLUS unary
          | MINUS unary
          | NOT unary
          | power
    """
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
    power : primary POWER power
          | primary
    """
    if len(p) == 5:
        p[0] = ast.Arith(p[2], p[1], p[4])
    else:
        p[0] = p[1]


# Primary expressions include literals, variables, function calls, and
# parenthesized expressions
def p_primary_group(p):
    """
    primary : '(' expression ')'
    """
    p[0] = p[2]


def p_primary_double_number(p):
    """
    primary : DOUBLE_NUMBER
    """
    p[0] = ast.Double(p[1])


def p_primary_real_number(p):
    """
    primary : REAL_NUMBER
    """
    p[0] = ast.Real(p[1])


def p_primary_integer_number(p):
    """
    primary : INTEGER_NUMBER
    """
    p[0] = ast.Integer(p[1])


def p_primary_string(p):
    """
    primary : STRING
    """
    p[0] = ast.String(p[1])


def p_primary_boolean(p):
    """
    primary : TRUE
            | FALSE
    """
    p[0] = ast.Bool(p.slice[1].type == "TRUE")


# Primary identifiers can be variables or function calls
def p_primary_identifier(p):
    """
    primary : IDENTIFIER
            | IDENTIFIER '(' argument_list_opt ')'
    """
    location = ast.location_from_token(p.slice[1])

    if len(p) == 2:
        p[0] = ast.Var(p[1], location)
    else:
        p[0] = ast.IndexedOrCall(p[1], p[3], location)


# Optional argument list for function calls
def p_argument_list_opt(p):
    """
    argument_list_opt : argument_list
                      | empty
    """
    p[0] = [] if p[1] is None else p[1]


# Argument list is compose of one or more expressions separated by commas
def p_argument_list(p):
    """
    argument_list : expression
                  | argument_list ',' expression
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
