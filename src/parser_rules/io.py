# Input/output grammar used by the parser.

# This module owns the PRINT, READ, and WRITE productions plus the
# comma/continuation-separated list helpers they rely on.


def p_print_stmt(p):
	"""
	print_stmt : PRINT ASTERISK ',' expression_list
			   | PRINT expression_list
	"""
	# AST node: keep the same normalized shape used by the rest of the parser.
	if len(p) == 5:
		p[0] = ('print', p[4])
	else:
		p[0] = ('print', p[2])


def p_read_stmt(p):
	"""
	read_stmt : READ ASTERISK ',' variable_list
			  | READ variable_list
	"""
	# AST node: keep the same normalized shape used by the rest of the parser.
	if len(p) == 5:
		p[0] = ('read', p[4])
	else:
		p[0] = ('read', p[2])


def p_write_stmt(p):
	"""
	write_stmt : WRITE ASTERISK ',' expression_list
			   | WRITE expression_list
	"""
	# AST node: keep the same normalized shape used by the rest of the parser.
	if len(p) == 5:
		p[0] = ('write', p[4])
	else:
		p[0] = ('write', p[2])


def p_variable_list(p):
	"""
	variable_list : variable variable_list_tail
	"""
	# AST node: build the variable list with any continuation pieces.
	p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated variables.
def p_variable_list_tail(p):
	"""
	variable_list_tail : ',' variable variable_list_tail
					   | '&' variable variable_list_tail
					   | empty
	"""
	# AST node: if there are more variables, create a list of them;
	# otherwise, an empty list.
	if len(p) == 4:
		p[0] = [p[2]] + p[3]
	else:
		p[0] = []


def p_expression_list(p):
	"""
	expression_list : expression expression_list_tail
	"""
	# AST node: build the expression list with any continuation pieces.
	p[0] = [p[1]] + p[2]


# The preprocessor leaves line continuations as '&', so accept them in
# the same list structure as normal comma-separated expressions.
def p_expression_list_tail(p):
	"""
	expression_list_tail : ',' expression expression_list_tail
						 | '&' expression expression_list_tail
						 | empty
	"""
	# AST node: if there are more expressions, create a list of them;
	# otherwise, an empty list.
	if len(p) == 4:
		p[0] = [p[2]] + p[3]
	else:
		p[0] = []
