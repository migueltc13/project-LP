      PROGRAM TESTREF
      INTEGER X
      X = 1
      CALL INC(X)
      PRINT *, X  ! Expected output: 2 (instead of 1)
      END

      SUBROUTINE INC(A)
      INTEGER A
      A = A + 1
      RETURN
      END
