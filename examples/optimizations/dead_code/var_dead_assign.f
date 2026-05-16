      PROGRAM DEAD_ASSIGN_DCE
      INTEGER X, Y  ! remove Y declaration
      X = 10
      Y = 999       ! remove Y assignment
      PRINT *, X
      END
