FC=gfortran
FFLAGS=-ffixed-form

# Sources live under the `general/` subdirectory now
ALL_FIXED=$(wildcard general/*.f)
FIXED_SOURCES=$(filter-out general/empty.f, $(ALL_FIXED))
FIXED_NAMES=$(notdir $(FIXED_SOURCES))

FREE_SOURCES=$(wildcard general/*.f90)
FREE_NAMES=$(notdir $(FREE_SOURCES))

BIN_DIR=bin

FIXED_TARGETS=$(FIXED_NAMES:%.f=$(BIN_DIR)/%_f)
FREE_TARGETS=$(FREE_NAMES:%.f90=$(BIN_DIR)/%_f90)

TARGETS=$(FIXED_TARGETS) $(FREE_TARGETS)

.PHONY: all install clean

all: $(BIN_DIR) $(TARGETS)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/%_f: general/%.f
	$(FC) -ffixed-form $< -o $@

$(BIN_DIR)/%_f90: general/%.f90
	$(FC) -ffree-form $< -o $@

install:
	sudo apt install -y gfortran

clean:
	rm -rf $(BIN_DIR)/*  # Keeps .gitignore
