program matrix_mult
integer A(2), B(2), RESULT

print *, 'Enter values for A(1) and A(2):'
read *, A(1), A(2)

print *, 'Enter values for B(1) and B(2):'
read *, B(1), B(2)

RESULT = A(1)*B(1) + A(2)*B(2)

print *, 'Result:'
print *, RESULT

end
