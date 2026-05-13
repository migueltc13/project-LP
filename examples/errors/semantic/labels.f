      PROGRAM LABEL_ERRORS
        INTEGER I
      GOTO 10
   10 PRINT 'Referenced label'
      GOTO 999
   20 PRINT 'First definition of redefined label'
      GOTO 20
   30 PRINT 'Unused label'
   40 PRINT 'DO target is not CONTINUE'
        DO 40 I = 1, 10
        PRINT *, I
   50 CONTINUE
   20 PRINT 'Second definition of redefined label'
      END
