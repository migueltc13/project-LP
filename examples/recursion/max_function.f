      PROGRAM TEST_RECURSIVE_MAX_FUNCTION
      INTEGER N, R
      N = 5
      R = SUMMAX(N)
      PRINT *, R
      END

      INTEGER FUNCTION SUMMAX(N)
      INTEGER N, M
      IF (N .LE. 0) THEN
        SUMMAX = 0
      ELSE
        M = N - 1
        SUMMAX = MAX(N, 3) + SUMMAX(M)
      ENDIF
      RETURN
      END
