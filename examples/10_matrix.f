      PROGRAM MATRIX_MULT
      INTEGER A(2), B(2), RESULT

      PRINT *, 'Enter values for A(1) and A(2):'
      READ *, A(1), A(2)

      PRINT *, 'Enter values for B(1) and B(2):'
      READ *, B(1), B(2)

      RESULT = A(1)*B(1) + A(2)*B(2)

      PRINT *, 'Result:'
      PRINT *, RESULT

      END
