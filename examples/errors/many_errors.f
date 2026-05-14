      PROGRAM MANY_ERRORS
      INTEGER X, Z, Z, I
      REAL R
      LOGICAL FLAG
      INTEGER ARR(FLAG)

      PRINT *, X
      PRINT *, Y
      Z = 5
      A = 2

      IF (X) THEN
        PRINT *, 'bad IF'
      ENDIF

      PRINT *, X .AND. .TRUE.
      PRINT *, X .EQ. 'A'
      PRINT *, 'oops' + 1
      X = 'text'

      CALL F(1, 2)
      X = S(1, 2)
      X = F(1)
      CALL S(1)
      X = MYSTERY(1)
      CALL UNKNOWN_SUB

      RETURN
      GOTO 10

   20 CONTINUE
   20 PRINT *, 'redefined label'
   30 CONTINUE

      DO 40 I = 1, 10
        PRINT *, I
   40 PRINT *, I

      END

      PROGRAM SECOND_MAIN
      PRINT *, 'second program unit'
      END

      INTEGER FUNCTION F(A, B)
      INTEGER A, B
      F = A + B
      RETURN
      END

      SUBROUTINE S(A, B)
      INTEGER A, B
      RETURN
      END

      SUBROUTINE S(Z)
      INTEGER Z
      RETURN
      END
