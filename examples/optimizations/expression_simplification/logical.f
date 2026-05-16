      PROGRAM TEST
      LOGICAL L, X
      X = .TRUE.
      L = (.TRUE. .AND. X) .OR. .FALSE.  ! L = X in compile time
      PRINT *, L
      END
