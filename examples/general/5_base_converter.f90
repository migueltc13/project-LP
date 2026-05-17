program base_converter
integer num, base, result, convrt

print *, 'Insert an integer:'
read *, num

do 10 base = 2, 9
  result = convrt(num, base)
  print *, 'BASE ', base, ': ', result
10 continue

end

integer function convrt(n, b)
integer n, b, quot, pot, val
val = 0
pot = 1
quot = n
val = val + (mod(quot, b) * pot)
quot = quot / b
pot = pot * 10
val = val + (mod(quot, b) * pot)
quot = quot / b
pot = pot * 10
val = val + (mod(quot, b) * pot)
quot = quot / b
pot = pot * 10
val = val + (mod(quot, b) * pot)
convrt = val
return
end
