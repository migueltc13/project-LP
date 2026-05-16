      PROGRAM LOGICAL_CONSTANT_FOLDING
      LOGICAL L
      L = .TRUE. .AND. .FALSE.  ! L = .FALSE. in compile time
      PRINT *, L
      END
