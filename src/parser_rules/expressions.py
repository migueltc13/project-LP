# Expressions

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
    if len(p) == 4:
        p[0] = ('logical', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_logical_and(p):
    """
    logical_and : logical_and AND relational
                | relational
    """
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
    if len(p) == 3:
        if p[1] == '+':
            p[0] = ('uplus', p[2])
        elif p[1] == '-':
            p[0] = ('uminus', p[2])
        else:
            p[0] = ('not', p[2])
    else:
        p[0] = p[1]


def p_power(p):
    """
    power : primary POWER power
          | primary
    """
    if len(p) == 4:
        p[0] = ('arith', p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_primary_group(p):
    """
    primary : '(' expression ')'
    """
    p[0] = p[2]


def p_primary_number(p):
    """
    primary : NUMBER
    """
    p[0] = ('number', p[1])


def p_primary_string(p):
    """
    primary : STRING
    """
    p[0] = ('string', p[1])


def p_primary_boolean(p):
    """
    primary : TRUE
            | FALSE
    """
    p[0] = ('bool', p.slice[1].type == 'TRUE')


def p_primary_identifier(p):
    """
    primary : IDENTIFIER
            | IDENTIFIER '(' argument_list_opt ')'
    """
    if len(p) == 2:
        p[0] = ('var', p[1])
    else:
        p[0] = ('call', p[1], p[3])


def p_argument_list_opt(p):
    """
    argument_list_opt : argument_list
                      | empty
    """
    p[0] = [] if p[1] is None else p[1]


def p_argument_list(p):
    """
    argument_list : expression
                  | argument_list ',' expression
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_empty(p):
    """
    empty :
    """
    p[0] = None