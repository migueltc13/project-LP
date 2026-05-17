      PROGRAM TEST_RECURSIVE_ABS_FUNCTION
      INTEGER N, R
      N = 5
      R = SUMABS(N)
      PRINT *, R
      END

      INTEGER FUNCTION SUMABS(N)
      INTEGER N, M
      IF (N .LE. 0) THEN
        SUMABS = 0
      ELSE
        M = N - 1
        SUMABS = ABS(-N) + SUMABS(M)
      ENDIF
      RETURN
      END
