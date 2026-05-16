      PROGRAM IF_NO_ELSE_DCE
      INTEGER X
      X = 1
      IF (.FALSE.) THEN ! Dead code (remove the if-else)
      X = 999
      ENDIF
      PRINT *, X
      END
