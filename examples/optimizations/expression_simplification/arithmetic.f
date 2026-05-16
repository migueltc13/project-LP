      PROGRAM ARITHMETIC_SIMPLIFICATION
      INTEGER X, Y
      Y = 10
      X = (2 + 3) * Y + 0  ! X = 5 * Y + 0 (Constant folding)
                           ! X = 5 * Y     (Expression simplification)
      PRINT *, X
      END
