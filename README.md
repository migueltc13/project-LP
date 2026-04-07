# Language Processing <br/> *Processamento de Linguagens*

## Resources

- [EWVM](https://ewvm.epl.di.uminho.pt/)
- [FORTRAN 77 Reference Language | Oracle](https://docs.oracle.com/cd/E19957-01/805-4939/)
- [FORTRAN 77 Reference Language Manual | Innsbruck](http://physik.uibk.ac.at/hephy/praktikum/fortran_manual.pdf)
- [FORTRAN 77 | Wikipedia](https://en.wikipedia.org/wiki/Fortran_77)
- [FORTRAN 77 Standard Fixed Format | Oracle](https://docs.oracle.com/cd/E19957-01/805-4939/z40007331fe6/index.html)

## Lexical Analysis

For now, we will use column fixed format, which is the default for FORTRAN 77.

- First 6 columns:   reserved for labels
- 7th column:        for continuation characters (if the line is too long)
- Remaining columns: for code statements

We will also ignore comments, which start with a 'C' in the first column.

## Syntax Analysis

## Semantic Analysis

## Code Translation

## Code Optimization

- Unused variable elimination
- Constant `IF` elimination
- Loop unrolling
