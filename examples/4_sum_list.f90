program sum_list
integer nums(5)
integer i, sum
sum = 0
print *, 'Insert 5 numbers:'
do 30 i = 1, 5
	read *, nums(i)
	sum = sum + nums(i)
30 continue
print *, 'The sum of the numbers is:', sum
end
