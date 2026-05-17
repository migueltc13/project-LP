! Calculate the area of a circle
PROGRAM CIRCLE
  REAL RADIUS, AREA, PI
  PI = 3.14159265
  PRINT *, 'Enter radius:'
  READ *, radius
100 AREA = PI * &
  RADIUS**2
11 PRINT *, 'Area = ', AREA
END
