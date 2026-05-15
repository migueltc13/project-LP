C     Example with fixed-form comments
      PROGRAM STRINGS
      PRINT *, 'He said "HI"'
      PRINT *, "A!B"
      PRINT *, ""
C     This line is ignored by the compiler front end
      PRINT *, "abc" ! comment after string
      END