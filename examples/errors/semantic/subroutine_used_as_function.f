       PROGRAM SUBROUTINE_USED_AS_FUNCTION
       INTEGER X
       X = S(X)
       END

       SUBROUTINE S(N)
       INTEGER N
       N = N + 1
       RETURN
       END
