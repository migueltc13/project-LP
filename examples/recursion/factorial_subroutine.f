      PROGRAM TEST_SUBROUTINE_RECURSION
      INTEGER N, R
      N = 5
      R = 1
      CALL FACTACC(N, R)
      PRINT *, R  ! 120
      END

      SUBROUTINE FACTACC(N, R)
      INTEGER N, R, M
      IF (N .LE. 1) THEN
        RETURN
      ELSE
        R = R * N
        M = N - 1
        CALL FACTACC(M, R)
      ENDIF
      RETURN
      END
