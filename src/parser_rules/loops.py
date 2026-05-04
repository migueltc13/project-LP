# Loop grammar used by the parser.

# The numeric label after DO is kept in the AST, and the loop terminator is
# matched directly as a labeled CONTINUE statement.

# The loop body uses its own nonterminal so the parser can stop cleanly at the
# terminating label without touching the lexer or preprocessor.


def p_do_loop(p):
	"""
	do_loop : DO NUMBER IDENTIFIER '=' expression ',' expression loop_statements LABEL CONTINUE
	"""
	# The numeric label after DO identifies the matching CONTINUE line.
	# We keep the loop variable, bounds, body, and terminator label in a
    # compact AST node.
	p[0] = ('do', p[2], p[3], p[5], p[7], p[8], p[9])


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
