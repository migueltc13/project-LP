      PROGRAM TEST_ARRAY_REFERENCE_RECURSION
      INTEGER A(3), N
      A(1) = 0
      N = 3
      CALL INCN(A(1), N)
      PRINT *, A(1)  ! 3
      END

      SUBROUTINE INCN(X, N)
      INTEGER X, N, M
      IF (N .LE. 0) THEN
        RETURN
      ELSE
        X = X + 1
        M = N - 1
        CALL INCN(X, M)
      ENDIF
      RETURN
      END
