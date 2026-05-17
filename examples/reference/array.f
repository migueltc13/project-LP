      PROGRAM TESTARRAY
      INTEGER A(3)
      A(1) = 1
      CALL SETFIRST(A)
      PRINT *, A(1)  ! Expected output: 99 (instead of 1)
      END

      SUBROUTINE SETFIRST(X)
      INTEGER X(3)
      X(1) = 99
      RETURN
      END
