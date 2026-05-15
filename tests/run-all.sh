#!/bin/bash

CYN='\033[0;36m'
PRP='\033[0;35m'
RST='\033[0m'

VERBOSE=0

banner() {
    echo -e "${CYN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  $1"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${RST}"
}

section() {
    echo -ne "${PRP}"
    echo "═════════ $1 ═════════"
    echo -ne "${RST}"
}

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --no-color     Disable colored output"
    echo "  -v, --verbose  Show AST and lexer tokens"
    echo "  -h, --help     Show this help message and exit"
}

# Process command-line arguments
for arg in "$@"; do
    case $arg in
        -h|--help)
            usage
            exit 0
            ;;

        --no-color)
            CYN=''
            PRP=''
            RST=''
            ;;

        -v|--verbose)
            VERBOSE=1
            ;;

        *)
            echo "Unknown option: $arg"
            usage
            exit 1
            ;;
    esac
done

# Check if needed directories exist
dirs=("examples" "tests")
for dir in "${dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Error: $dir/ directory not found!"
        exit 1
    fi
done

banner "FORTRAN COMPILATION"

# Compile fortran files to validate that they compile correctly
echo "Compiling Fortran examples..."

pushd examples/ >/dev/null || {
    echo "Error: examples/ directory not found!"
    exit 1
}

make clean
make

popd >/dev/null || {
    echo "Error: Failed to return to the original directory!"
    exit 1
}

banner "TEST EXECUTION"

# Explicit test order
TESTS=(
    "tests/formats.py"
    "tests/lexer.py"
    "tests/parser.py"
    "tests/errors.py"
)

# Run all tests
exit_code=0

for TEST in "${TESTS[@]}"; do
    section "$TEST"

    if [ "$VERBOSE" -eq 1 ]; then
        python3 "$TEST" --verbose
    else
        python3 "$TEST"
    fi

    test_exit_code=$?

    echo ""

    if [ $test_exit_code -ne 0 ]; then
        echo "Error: $TEST failed!"
        exit_code=1
    fi
done