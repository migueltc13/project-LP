[![Tests](https://github.com/migueltc13/project-LP/actions/workflows/tests.yml/badge.svg)](https://github.com/migueltc13/project-LP/actions/workflows/tests.yml)

# Language Processing <br/> *Processamento de Linguagens*

**TODO** Small project description mentioning the assignment file, and developed work.

## Table of Contents

**TODO**

## TODO list

- [ ] Move examples/*.f and *.f90 to examples/general/ adapt Makefile
    and tests accordingly

- [ ] Provide test description for the new `examples/errors/semantic/numbers.f`
- [ ] remove test `examples/errors/code_gen/intrinsic_function.f` we support them now
- [ ] Added pass-by-reference tests at `examples/references/`
- [ ] Added recursion tests at `examples/recursion/`

- report INTRINSIC FUNCTIONS supported:
```
ABS, IABS, DABS
POW,
SQRT, DSQRT
EXP, DEXP
INT, REAL, DBLE, FLOAT
MAX, MIN
MOD
```

- [ ] Explain sqrt algorithm in codegen
    and EXP that uses Taylor series expansion (12 iterations) to calculate the
    value of e^x.

- [ ] Add support for the functions defined in INTRINSIC_FUNCTIONS at
      [procedures.py](src/semantics/procedures.py),
      Maybe reserved this functions as lexer `keywords`.
      Also see `# TODO remove intrinsics that we don't support` at the same file.
      Update `**` to use `POW` intrinsic function instead of generating a loop
      for exponentiation.
- [ ] mention in the report how the parser checks for the special statement
    RETURN, and it only recognizes it in the right contexts (inside procedures)
- [ ] mention that the parser prioritizes left recursion since its more
    efficient for the LALR(1) (try to find a good reference for this,
    I think it was in the PLY documentation)
- [ ] mention in report that strict version was implemented instead of implicit
    typing rules
- [ ] mention as future work: constant folding for intrinsic calls
- [ ] mention as future work: combine semantic checks for efficiency
    (e.g. type checks and reference resolution in a single pass)
- [ ] mention as future work: how could we support multi dimensional arrays
- [ ] mention as future work: Improve compiler temporary allocation for deeply
nested expressions (and TEMP_SLOTS_PER_SCOPE)

## Usage

```
usage: generator.py [-o OUTPUT] [-O] [-g] [--format {fixed,free}] [--no-preprocess]
                    [--viz [OUTPUT]] [--no-open] [--show-intrinsics] [-v] [-h]
                    [input_file]

Compile Fortran 77 source code into EWVM assembly.

positional arguments:
  input_file            Fortran source file. If omitted, read from stdin.

options:
  -o OUTPUT, --output OUTPUT
                        Output file. If omitted, output to stdout.
  -O, --optimize        Enable optimizations.
  -g, --debug           Enable debug comments.
  --format {fixed,free}
                        The source format. If omitted, inferred from file extension;
                        stdin defaults to fixed.
  --no-preprocess       Skip preprocessing stage.
  --viz [OUTPUT], --visualize [OUTPUT]
                        Generate a Graphviz image of the AST.
  --no-open             Do not open the generated AST visualization file. Only valid
                        with --viz/--visualize.
  --show-intrinsics     Include intrinsic procedures in verbose semantic info output.
                        Requires -v/--verbose.
  -v, --verbose         Enable verbose output during compilation (e.g. print
                        intermediate AST, semantic info, etc.)
  -h, --help            Show this help message and exit.
```

## Compiler Pipeline

### Overview

```mermaid
graph LR
    %% Modules
    subgraph PRE[Preprocessor]
        direction TB
        P_FIXED[Fixed-Format Logic]
        P_FREE[Free-Format Logic]
        P_FIXED ~~~ P_FREE
    end
    LEX[Lexer]
    PARSER["Parser
            +
            Semantic Analysis"]
    DECIDE{"Optimization
            enabled?"}
    OPT[Optimizations]
    GEN[Code Generation]

    %% Connections
    PRE      --> LEX
    LEX      --> PARSER
    PARSER   --> DECIDE
    DECIDE   -->|"Yes"| OPT
    OPT      --> GEN
    DECIDE   -->|"No"| GEN
```

### Preprocessor

The compiler pipeline begins with a dedicated **Preprocessor** module. Its
original purpose was to simplify the handling of Fortran 77 fixed-format source
code before lexical analysis. This was necessary because fixed-format Fortran is
highly column-sensitive: columns 1 to 5 may contain a statement label, column 6
is reserved for continuation markers, and the actual statement body begins at
column 7 and may only extend up to column 72.

Handling these rules directly in the lexer would make the lexical analysis
significantly more complex, since the lexer would need to be aware not only of
tokens, but also of their exact column positions. To avoid this, the
preprocessor converts fixed-format input into a normalized pseudo-Fortran
representation that is easier for the lexer to process.

For fixed-format source code, the preprocessor is responsible for:

- enforcing the maximum column width of 72 characters;
- normalizing full-line comments beginning with `C`, `c`, or `*` in column
    into a common `!` comment form;
- extracting labels from columns 1 to 5 and converting them into an explicit
    pseudo-token, such as `@LABEL(100)`;
- validating that labels contain only numeric values with at most five digits;
- detecting continuation lines through column 6, and converting continuation
    markers into a normalized `&` representation by appending `&` to the
    previous statement line;
- detecting invalid continuations, such as a continuation line without a
    preceding statement.

If invalid fixed-format input is detected, the preprocessor raises an explicit
preprocessing error and the compiler pipeline is halted before lexical analysis.
Examples of such errors include lines exceeding 72 columns, invalid labels in
the label field, or orphaned continuation lines.

After the initial implementation, the group realized that the same normalization
strategy could also be applied to free-format source code. Although free-format
does not depend on fixed columns, labels can still appear before statements.
Therefore, the free-format preprocessor also converts labels into the same
`@LABEL(...)` pseudo-token representation. This allows both fixed-format and
free-format programs to be transformed into a common intermediate textual
representation before reaching the lexer.

The result is a single preprocessing stage that supports both source formats and
produces a normalized pseudo-Fortran 77 stream. This reduces the complexity of
the lexer and also the parser, since they no longer need to distinguish between
several surface-level formatting conventions. Instead, they can operate over a
more uniform representation.

However, this approach also introduces an important disadvantage. The
preprocessor inserts pseudo-tokens, such as `@LABEL(...)`, which are not part of
the original Fortran source code. Although this simplifies the lexer and parser,
it creates a challenge for one of the main objectives of the compiler as a
whole: accurate error reporting. Since transformed lines may no longer preserve
the original column positions, errors detected in later stages may refer to
locations in the preprocessed code rather than in the user’s original source
file.

This trade-off was accepted because the problem can be addressed with
source-location mapping. Since the preprocessor preserves a 1:1 mapping
between original and preprocessed lines, the compiler can extend this mapping
with column information. Later stages, such as the lexer, parser, and semantic
analyser, can then translate reported positions back to the original source.
For example, when a line contains an inserted `@LABEL(...)` token, the compiler
can compensate for the introduced offset and report the correct original column.
This allows the compiler to keep the advantages of normalization while still
preserving accurate diagnostics.

Furthermore, although the preprocessor could try to infer the source format
automatically, this was not chosen because fixed-format and free-format code can
be ambiguous. Instead, the compiler uses an explicit CLI flag when provided,
otherwise it infers the format from the file extension: `.f` for fixed-format
and `.f90` for free-format. When reading from standard input without a specified
format, it defaults to fixed-format.

For example:

```fortran
      PROGRAM EXAMPLE
C = 1
      END
```

In fixed-format Fortran, `C = 1` is a comment because `C` appears in column 1.
In free-format Fortran, it may be interpreted as an assignment to variable `C`.
This ambiguity makes explicit or extension-based format selection more
predictable.

The preprocessing stage is additionally validated through the automated test
[tests/formats.py](tests/formats.py), it compares the outputted lexed tokens for
equivalent fixed-format (`.f`) and free-format (`.f90`) source files. When
running the lexer, the `--test` flag is used to remove the column field from
the lexed tokens, since positions naturally differ between the two formats.

### Lexical Analysis

The lexical analysis phase is responsible for transforming the preprocessed
Fortran 77 source code into a stream of tokens that can be consumed by the
parser, using the [PLY (Python Lex-Yacc)](https://www.dabeaz.com/ply/ply.html)
library.

Unlike preprocessing, which handles format normalization and structural cleanup
of fixed and free-format source code, the lexer operates directly on the
normalized pseudo-Fortran representation produced by the preprocessing stage.
At this point, fixed-format constraints have already been resolved, labels have
been converted into `@LABEL(...)` pseudo-tokens, continuation lines symbols have
been normalized, and both source formats share a unified input stream.

***This significantly reduces formatting ambiguities and simplifies the complexity
of token recognition.***

**TODO** it does simplify the lexer, but i don't know what ambiguities it resolves

#### Token Categories

The lexer defines a set of tokens grouped into the following categories:

1. **Reserved Keywords**

- **Program Structure:** `PROGRAM`, `END`;
- **I/O Statements:** `READ`, `WRITE`, `PRINT`;
- **Data Types:** `INTEGER`, `REAL`, `DOUBLE`, `LOGICAL`, `CHARACTER`;
- **Control Flow:** `IF`, `THEN`, `ELSE`, `ENDIF`;
- **Iteration and Jumps:** `DO`, `CONTINUE`, `GOTO`, `STOP`;
- **Procedures:** `SUBROUTINE`, `FUNCTION`, `RETURN`.

2. **Identifiers, Literals and Punctuation**

- **Identifiers:** Variable and procedure names;
- **Numeric Literals:** Integer, double precision, and real literals;
- **Strings:** Single or double-quoted strings, with proper handling of escaped
characters;
- **Labels:** Recognized through the preprocessor as `@LABEL(...)` pseudo-tokens.
The lexer converts them into a `LABEL` token containing the numeric identifier.

The lexer also supports a small set of punctuation symbols, such as `( ) , : =`.
These are handled as single-character tokens for simplicity.

3. **Operators**

Instead of defining operators as literals, we used tokens, because they simplify
the attachment of semantic information and precedence rules during later stages
of compilation.
For the `POWER` operator, we had to define it before the `ASTERISK` operator,
otherwise it would be lexed as two separate `ASTERISK` tokens.

- **Math Operators:** `PLUS`, `MINUS`, `DIVIDE`, `POWER`, `ASTERISK`;
- **Dot Relational Operators:** `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`;
- **Logical Dot Operators and Constants:** `AND`, `OR`, `NOT`, `TRUE`, `FALSE`.

Since Fortran 77 is case-insensitive, the lexer converts identifiers,
dot operators, and logical constants to uppercase during tokenization.
This allows the parser and later stages to operate over a uniform
representation independently of the original source casing.

4. **Whitespaces and Comments**

Whitespace characters (space, tab, and the continuation marker `&`) are ignored
by the lexer.

Comments are fully discarded at lexical level:
- Fixed-format comments starting with `C`, `c`, or `*` in column 1;
- Inline comments starting with `!`.

#### Error Handling

The lexer includes error detection for invalid characters and unsupported
sequences. Any character not matching the defined token rules triggers a
lexical error, and consecutive invalid characters are grouped into a single
diagnostic to improve error message readability.
Errors are reported using the compiler's diagnostic system, including source
line extraction; column position calculation, error length highlighting, and
optional filename tracking.
After reporting, the lexer skips the invalid input and continues analysis,
allowing multiple errors to be detected in a single compilation run.

The lexical analysis stage is additionally validated through an automated test
[tests/lexer.py](tests/lexer.py). This test executes the lexer over all example
source files in test mode, verifying that valid programs are tokenized
successfully and that lexical errors are correctly reported when invalid input
is encountered.

### Syntax Analysis

### Semantic Analysis

#### Program unit checks

#### Label checks

#### Loop checks

#### Variable checks

#### Reference resolution

#### Numeric checks

#### Procedures checks

#### Type checks

### Optimizations

#### Constant Folding

#### Expression Simplification

#### Dead Code Elimination

#### Vectorization

### Code Generation

## Error Handling

### Supported Diagnostics

Severity                            | Type         | Category     | Description                                                         | Hint
---                                 | ---          | ---          | ---                                                                 | ---
$\color{Red}\textsf{Error}$         | Preprocessor | Format       | Line exceeds 72 columns                                             | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Preprocessor | Continuation | Orphaned continuation line                                          | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Preprocessor | Labels       | Label field contains non-numeric characters or exceeds 5 digits     | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Lexical      | Characters   | Character not valid in Fortran 77                                   | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Lexical      | Characters   | Character sequence not valid in Fortran 77                          | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Syntax       | Characters   | Syntax error in token                                               | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Syntax       | EOF          | Unexpected end of file                                              | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Program      | Multiple main PROGRAM units defined                                 | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Labels       | Label redefined                                                     | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Labels       | Label referenced but not defined                                    | $\color{White}\textsf{✗}$
$\color{Goldenrod}\textsf{Warning}$ | Semantic     | Labels       | Label defined but not referenced                                    | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Loops        | DO loop target label does not label a CONTINUE statement            | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Variables    | Variable already declared                                           | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Variables    | Use of undeclared variable                                          | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Variables    | Assignment to undeclared variable                                   | $\color{White}\textsf{✗}$
$\color{Goldenrod}\textsf{Warning}$ | Semantic     | Variables    | Variable may be used before being initialized                       | $\color{White}\textsf{✗}$
$\color{Goldenrod}\textsf{Warning}$ | Semantic     | Variables    | Variable declared but not used                                      | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | Undefined procedure reference                                       | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | Duplicate procedure definition                                      | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | Procedure definition conflicts with intrinsic procedure             | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | FUNCTION called as a SUBROUTINE                                     | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | SUBROUTINE called as a FUNCTION                                     | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | Procedure mismatched expected number of arguments                   | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Procedures   | RETURN statement outside procedure                                  | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Numeric      | Division by zero                                                    | $\color{White}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Numeric      | INTEGER/REAL/DOUBLE value out of range                              | $\color{Green}\textsf{✓}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | IF condition must be of type LOGICAL                                | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Array dimension must be of type INTEGER                             | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Array index must be of type INTEGER                                 | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Cannot assign value of type X to type Y variable                    | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | DO loop variable must be of type INTEGER                            | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | DO loop upper/lower bound must be of type INTEGER                   | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | DO loop step must be of type INTEGER                                | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | DO loop step must be a positive INTEGER                             | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Unary operators ('+' and '-') require numeric operand               | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | NOT requires a LOGICAL operand                                      | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Left/right arithmetic operand must be numeric                       | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Relational operands must have compatible types                      | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Semantic     | Types        | Left/right logical operand must be LOGICAL                          | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Arrays       | Only one-dimensional arrays are supported yet                       | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Arrays       | Only one-dimensional array references/assignments are supported yet | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Arrays       | Dynamic array dimensions inside procedures are not supported yet    | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Program      | Code generation requires a PROGRAM unit                             | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Statements   | Unsupported statement for EWVM generation                           | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Expressions  | Unsupported expression for EWVM generation                          | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Assignments  | Unsupported assignment target                                       | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Instructions | Unsupported READ target                                             | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Instructions | Only one-dimensional array READ is supported yet                    | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Operators    | Unsupported arithmetic/relational/logical/unary operator            | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Procedures   | Intrinsic procedure is not supported by code generation yet         | $\color{White}\textsf{✗}$
$\color{Red}\textsf{Error}$         | Code Gen     | Procedures   | Not a FUNCTION/SUBROUTINE                                           | $\color{White}\textsf{✗}$

<!--
HTML:
<span style="background:#ffecec;color:#b00020;padding:2px 6px;border-radius:4px;font-weight:bold;">Error</span>
<span style="background:#fff8db;color:#8a6d00;padding:2px 6px;border-radius:4px;font-weight:bold;">Warning</span>
<span style="color:green">✓</span>
<span style="color:red">✗</span>

LaTeX:
$\color{Goldenrod}\textsf{Warning}$
$\color{Red}\textsf{Error}$
$\color{Green}\textsf{✓}$
$\color{Red}\textsf{✗}$
-->

## Testing

## Conclusions and Future Work

## Resources

### Tools

- [PLY (Python Lex-Yacc)](https://www.dabeaz.com/ply/ply.html)
- [EWVM](https://ewvm.epl.di.uminho.pt/)
- [GraphViz](https://graphviz.org/)
- [GFortran](https://gcc.gnu.org/wiki/GFortran)
- [GitHub Actions](https://github.com/features/actions)

### Fortran 77 References

- [Fortran 77 Reference Language Manual, Innsbruck](http://physik.uibk.ac.at/hephy/praktikum/fortran_manual.pdf)
- [Fortran 77 Reference Language, Oracle](https://docs.oracle.com/cd/E19957-01/805-4939/)
- [Fortran 77 Standard Fixed Format, Oracle](https://docs.oracle.com/cd/E19957-01/805-4939/z40007331fe6/index.html)
- [Fortran 77, Wikipedia](https://en.wikipedia.org/wiki/Fortran_77)

<a href="https://www.youtube.com/watch?v=4XF_Agllu7Q" target="_blank">🥚</a>
