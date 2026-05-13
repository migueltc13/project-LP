#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CYN='\033[0;36m'
PRP='\033[0;35m'
RST='\033[0m'

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

# Process command-line arguments
for arg in "$@"; do
    case $arg in
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-color    Disable colored output"
            echo "  -h, --help    Show this help message and exit"
            exit 0
            ;;
        --no-color)
            CYN=''
            PRP=''
            RST=''
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

# Check if needed directories exist
dirs=("$ROOT_DIR/examples" "$ROOT_DIR/tests")
for dir in "${dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Error: $dir/ directory not found!"
        exit 1
    fi
done

banner "FORTRAN COMPILATION"

# Compile fortran files to validate that they compile correctly
echo "Compiling Fortran examples..."
pushd "$ROOT_DIR/examples" >/dev/null || \
    (echo "Error: examples/ directory not found!" && exit 1)
make clean
make
popd >/dev/null || \
    (echo "Error: Failed to return to the original directory!" && exit 1)

banner "TEST EXECUTION"

# Get all executable files in the tests/ directory (excluding this script)
TESTS=$(find "$ROOT_DIR/tests" -type f -executable ! -name "$(basename "$0")")

# Run all tests
exit_code=0
for TEST in $TESTS; do
    section "$TEST"
    if ! "$TEST"; then
        echo "Error: $TEST failed!"
        exit_code=1
    fi
done

echo
echo "All tests completed."
exit $exit_code
