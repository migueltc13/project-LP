FC=gfortran
FFLAGS=-ffixed-form

SOURCES=$(wildcard *.f)
BIN_DIR=bin
EXECUTABLES=$(SOURCES:%.f=$(BIN_DIR)/%)

.PHONY: all clean

all: $(BIN_DIR) $(EXECUTABLES)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/%: %.f
	$(FC) $(FFLAGS) $< -o $@

clean:
	rm -rf $(BIN_DIR)/*  # Keeps .gitignore
