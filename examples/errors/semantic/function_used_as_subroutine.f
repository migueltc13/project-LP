       PROGRAM FUNCTION_USED_AS_SUBROUTINE
       INTEGER X
       X = 0
       CALL F(X)
       END

       INTEGER FUNCTION F(N)
       INTEGER N
       F = N + 1
       RETURN
       END
