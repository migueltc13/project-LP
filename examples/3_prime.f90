program prime
integer num
logical isprim
print *, 'Insert a positive integer:'
read *, num
isprim = .TRUE.
if (isprim) then
  print *, num, ' is a prime number'
else
  print *, num, ' is not a prime number'
endif
end
