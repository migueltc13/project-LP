      PROGRAM VECTOR_BASIC_SUM
      INTEGER I, SUM
      SUM = 0

* This for loop:
      DO 100 I = 1, 8
          SUM = SUM + I
  100 CONTINUE

* With vector size set to 4, becomes:
*     DO 100 I = 1, 5, 4
*         SUM = SUM + I
*         SUM = SUM + I + 1
*         SUM = SUM + I + 2
*         SUM = SUM + I + 3
* 100 CONTINUE

      PRINT *, SUM  ! Expected output: 36
      END
