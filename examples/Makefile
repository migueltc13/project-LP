FC=gfortran
FFLAGS=-ffixed-form

FIXED_SOURCES=$(wildcard *.f)
FREE_SOURCES=$(wildcard *.f90)

FIXED_TARGETS=$(FIXED_SOURCES:%.f=$(BIN_DIR)/%_f)
FREE_TARGETS=$(FREE_SOURCES:%.f90=$(BIN_DIR)/%_f90)

TARGETS=$(FIXED_TARGETS) $(FREE_TARGETS)

BIN_DIR=bin

.PHONY: all install clean

all: $(BIN_DIR) $(TARGETS)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/%_f: %.f
	$(FC) -ffixed-form $< -o $@

$(BIN_DIR)/%_f90: %.f90
	$(FC) -ffree-form $< -o $@

install:
	sudo apt install -y gfortran

clean:
	rm -rf $(BIN_DIR)/*  # Keeps .gitignore
