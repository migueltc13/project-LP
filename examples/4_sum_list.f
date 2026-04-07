      PROGRAM SUM_LIST
      INTEGER NUMS(5)
      INTEGER I, SUM
      SUM = 0
      PRINT *, 'Insert 5 numbers:'
      DO 30 I = 1, 5
          READ *, NUMS(I)
          SUM = SUM + NUMS(I)
   30 CONTINUE
      PRINT *, 'The sum of the numbers is:', SUM
      END
