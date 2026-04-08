       PROGRAM FACTORIAL
       INTEGER N, I, FACT
       PRINT *, 'Insert a positive integer:'
       READ *, N
       FACT = 1
       DO 10 I = 1, N
           FACT = FACT * I
   10  CONTINUE
       PRINT *, 'The factorial of ', N, ' is ', FACT
       END
