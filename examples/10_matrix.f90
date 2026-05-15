program matrix_mult
integer a(2), b(2), result

print *, 'Enter 2 integers for A (row vector):'
read *, a(1), a(2)

print *, 'Enter 2 integers for B (column vector):'
read *, b(1), b(2)

result = a(1)*b(1) + a(2)*b(2)

print *, 'Result:'
print *, result

end