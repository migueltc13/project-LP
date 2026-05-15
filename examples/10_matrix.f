      PROGRAM MATRIX_MULT
      INTEGER A(2), B(2), RESULT

      PRINT *, 'Enter 2 integers for A (row vector):'
      READ *, A(1), A(2)

      PRINT *, 'Enter 2 integers for B (column vector):'
      READ *, B(1), B(2)

      RESULT = A(1)*B(1) + A(2)*B(2)

      PRINT *, 'Result:'
      PRINT *, RESULT

      END