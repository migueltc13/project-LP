      PROGRAM PRIME
      INTEGER NUM
      LOGICAL ISPRIM
      PRINT *, 'Insert a positive integer:'
      READ *, NUM
      ISPRIM = .TRUE.
      IF (ISPRIM) THEN
        PRINT *, NUM, ' is a prime number'
      ELSE
        PRINT *, NUM, ' is not a prime number'
      ENDIF
      END
