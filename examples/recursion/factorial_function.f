      PROGRAM TEST_FUNCTION_REL_LHS
      INTEGER X
      X = 5
      IF (ID(X) .EQ. X) THEN
        PRINT *, 1
      ELSE
        PRINT *, 0
      ENDIF
      END

      INTEGER FUNCTION ID(A)
      INTEGER A
      ID = A
      RETURN
      END
