      PROGRAM TESTARRREF
      INTEGER A(3)
      A(1) = 10
      CALL INC(A(1))
      PRINT *, A(1)  ! Expected output: 15 (instead of 10)
      END

      SUBROUTINE INC(X)
      INTEGER X
      X = X + 5
      RETURN
      END
