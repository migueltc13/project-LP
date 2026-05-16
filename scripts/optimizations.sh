#!/bin/bash

# Script to generate visualizations for all optimizations examples.
# Usage: ./optimizations.sh [output_dir]

set -eu

if [ ! -f src/generator.py ]; then
    echo "Error: src/generator.py not found."
    echo "Please run this script from the root of the project."
    exit 1
fi

EXT=".f"
OUTPUT_DIR=${1:-".assets/optimizations"}

for DIR in examples/optimizations/*; do
    DIRNAME=$(basename "$DIR")
    for FILE in "$DIR"/*"$EXT"; do
        FNAME=$(basename "$FILE" "$EXT")
        src/generator.py -O --no-open --viz "$OUTPUT_DIR/$DIRNAME/$FNAME.png"     "$FILE" 1>/dev/null
        src/generator.py -O --no-open --viz "$OUTPUT_DIR/$DIRNAME/svg/$FNAME.svg" "$FILE" 1>/dev/null
    done
done

echo -e "\nOptimizations visualizations generated in $OUTPUT_DIR."
