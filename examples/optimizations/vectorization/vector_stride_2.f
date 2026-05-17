      PROGRAM VECTOR_STRIDE_2
      INTEGER I, SUM
      SUM = 0

* This for loop:
      DO 100 I = 1, 10, 2
          SUM = SUM + I
  100 CONTINUE

* With vector size set to 4, becomes:
*     DO 100 I = 1, 1, 8
*         SUM = SUM + I
*         SUM = SUM + I + 2
*         SUM = SUM + I + 4
*         SUM = SUM + I + 6
*     100 CONTINUE
*
* SUM = SUM + I

      PRINT *, SUM  ! Expected output: 25 (1 + 3 + 5 + 7 + 9)
      END
