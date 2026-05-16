      PROGRAM STOP_DCE
      INTEGER X
      X = 1
      STOP
      X = 999     ! Dead code
      PRINT *, X  ! Dead code
      END
