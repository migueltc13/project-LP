program prime
integer num, i
logical isprim
print *, 'Insert a positive integer:'
read *, num
isprim = .TRUE.
i = 2
20 if (i .LE. (num/2) .AND. isprim) then
     if (mod(num, i) .EQ. 0) then
        isprim = .FALSE.
     endif
     i = i + 1
     goto 20
endif
if (isprim) then
   print *, num, ' is a prime number'
else
   print *, num, ' is not a prime number'
endif
end
