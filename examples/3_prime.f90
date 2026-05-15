program prime
integer num, i
logical isprim
print *, 'Insert a positive integer:'
read *, num
isprim = .true.
i = 2
20 if (i .le. (num/2) .and. isprim) then
     if (mod(num, i) .eq. 0) then
        isprim = .false.
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
