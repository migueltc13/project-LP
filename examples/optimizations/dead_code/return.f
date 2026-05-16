      PROGRAM RETURN_DCE
      CALL TEST()
      END

      SUBROUTINE TEST()
      PRINT *, 'before'
      RETURN
      PRINT *, 'after'  ! Dead code
      END
