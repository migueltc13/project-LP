      PROGRAM BASE_CONVERTER
      INTEGER NUM, BASE, RESULT

      PRINT *, 'Insert an integer:'
      READ *, NUM

      DO 10 BASE = 2, 9
        RESULT = CONVRT(NUM, BASE)
        PRINT *, 'BASE ', BASE, ': ', RESULT
   10 CONTINUE

      END

      INTEGER FUNCTION CONVRT(N, B)
      INTEGER N, B, QUOT, POT, VAL
      VAL = 0
      POT = 1
      QUOT = N
      VAL = VAL + (MOD(QUOT, B) * POT)
      QUOT = QUOT / B
      POT = POT * 10
      VAL = VAL + (MOD(QUOT, B) * POT)
      QUOT = QUOT / B
      POT = POT * 10
      VAL = VAL + (MOD(QUOT, B) * POT)
      QUOT = QUOT / B
      POT = POT * 10
      VAL = VAL + (MOD(QUOT, B) * POT)
      CONVRT = VAL
      RETURN
      END
