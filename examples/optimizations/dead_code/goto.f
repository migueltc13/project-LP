      PROGRAM GOTO_DCE
      INTEGER X
      X = 1
      GOTO 100
      X = 999     ! Dead code
      PRINT *, X  ! Dead code
  100 PRINT *, 'done'
      END
