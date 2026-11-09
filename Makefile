CC ?= cc
AR ?= ar
PYTHON ?= python3
CPPFLAGS += -D_GNU_SOURCE -Iinclude
CFLAGS ?= -O2 -g
WARNINGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -Wshadow \
           -Wstrict-prototypes -Wmissing-prototypes
NO_ALLOC = -fno-builtin-malloc -fno-builtin-free -fno-builtin-calloc -fno-builtin-realloc
LDLIBS += -pthread
BUILD_DIR ?= build
OFFICIAL_DIR ?= ../official/LLH-26/Systems Programming/SYSPROG10
LIB = $(BUILD_DIR)/libmemctl.a
OBJ = $(BUILD_DIR)/allocator.o
TEST = $(BUILD_DIR)/test_allocator

.PHONY: all check check-symbols public-test sanitize benchmark reference clean
all: $(LIB) $(TEST)

$(BUILD_DIR):
	mkdir -p "$@"

$(OBJ): src/allocator.c include/libmemctl.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) $(NO_ALLOC) -c $< -o $@

$(LIB): $(OBJ)
	$(AR) rcs $@ $^

$(TEST): tests/test_allocator.c $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) $< $(LIB) $(LDLIBS) \
	  -Wl,--wrap=mmap -Wl,--wrap=munmap -o $@

check-symbols: $(OBJ)
	$(PYTHON) scripts/check_symbols.py $(OBJ)

check: check-symbols $(TEST)
	timeout 90s $(TEST)

public-test: $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) "$(OFFICIAL_DIR)/tests/test_runner.c" $(LIB) $(LDLIBS) -o $(BUILD_DIR)/public_tests
	timeout 90s $(BUILD_DIR)/public_tests

sanitize:
	ASAN_OPTIONS=detect_leaks=0 $(MAKE) BUILD_DIR=build-sanitize \
	  CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all' check

benchmark: $(BUILD_DIR)/benchmark_candidate

$(BUILD_DIR)/benchmark_candidate: bench/benchmark.c $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) $< $(LIB) $(LDLIBS) -o $@

reference: | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) $(NO_ALLOC) -c "$(OFFICIAL_DIR)/src/allocator.c" -o $(BUILD_DIR)/reference.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) -DMEMCTL_REFERENCE bench/benchmark.c $(BUILD_DIR)/reference.o $(LDLIBS) -o $(BUILD_DIR)/benchmark_reference

clean:
	rm -f -- $(OBJ) $(LIB) $(TEST) $(BUILD_DIR)/public_tests \
	  $(BUILD_DIR)/reference.o $(BUILD_DIR)/benchmark_reference $(BUILD_DIR)/benchmark_candidate
