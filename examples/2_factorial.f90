program factorial
integer n, i, fact
print *, 'Insert a positive integer:'
read *, n
fact = 1
do 10 i = 1, n
  fact = fact * i
10 continue
print *, 'The factorial of ', n, ' is ', fact
end
