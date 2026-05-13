       PROGRAM LABEL_ERRORS
       GOTO 10
   10  PRINT 'Referenced label'
       GOTO 999
   20  PRINT 'First definition of redefined label'
       GOTO 20
   30  PRINT 'Unused label'
   20  PRINT 'Second definition of redefined label'
       END
