program full_program
integer n, i, factor, total, result
integer values(5)
logical ready

print *, 'Full program demo'
n = 5
factor = 3
ready = .TRUE.
total = 0

do 10 i = 1, n
  values(i) = i * factor
10 continue

if (ready) then
  call bump_all(values, n, factor)
endif

total = isum_values(values, n)
result = total + factor

print *, 'N =', n
print *, 'TOTAL =', total
print *, 'RESULT =', result
print *, values(1), values(2), values(3)
print *, values(4), values(5)
end

integer function isum_values(values, count)
integer values(5), count, i, total
total = 0
do 20 i = 1, count
  total = total + values(i)
20 continue
print *, i
isum_values = total
return
end

subroutine bump_all(values, count, delta)
integer values(5), count, delta, i
do 30 i = 1, count
  values(i) = values(i) + delta
30 continue
return
end
