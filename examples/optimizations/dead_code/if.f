      PROGRAM IF_TRUE_DCE
      INTEGER X
      IF ((2 + 3) .EQ. 5) THEN  ! Always true condition (with constant folding)
      X = 10
      ELSE                      ! Dead code else-branch
      X = 999
      ENDIF
      PRINT *, X
      END
