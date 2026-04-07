      PROGRAM PRIME
      INTEGER NUM, I
      LOGICAL ISPRIM
      PRINT *, 'Insert a positive integer:'
      READ *, NUM
      ISPRIM = .TRUE.
      I = 2
  20  IF (I .LE. (NUM/2) .AND. ISPRIM) THEN
          IF (MOD(NUM, I) .EQ. 0) THEN
              ISPRIM = .FALSE.
          ENDIF
          I = I + 1
          GOTO 20
      ENDIF
      IF (ISPRIM) THEN
          PRINT *, NUM, ' is a prime number'
      ELSE
          PRINT *, NUM, ' is not a prime number'
      ENDIF
      END
