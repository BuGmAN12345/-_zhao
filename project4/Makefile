# Makefile for SM3 with optional SSE2-optimized version, no .o intermediate files
# Usage:
#   make              # builds sm3
#   make SIMD=1       # builds sm3_simd
#   make MERKLE=1     # builds sm3_merkle
#   make SIMD=1 MERKLE=1  # builds sm3_simd_merkle
# Default executable names
TARGET       := sm3
SIMD_TARGET  := sm3_simd
MERKLE_TARGET := sm3_merkle
SIMD_MERKLE_TARGET := sm3_simd_merkle

# Compiler and base flags
CC           := gcc
CFLAGS       := -Wall -Wextra

# SIMD-specific flags (SSE2)
SIMD_FLAGS   := -msse2 -O3

# Choose sources, target, and flags based on SIMD and MERKLE variables
ifeq ($(SIMD),1)
    ifeq ($(MERKLE),1)
        SRCS    := sm3_simd.c test_merkle.c
        TARGET  := $(SIMD_MERKLE_TARGET)
        CFLAGS += $(SIMD_FLAGS)
    else
        SRCS    := sm3_simd.c sm3test.c
        TARGET  := $(SIMD_TARGET)
        CFLAGS += $(SIMD_FLAGS)
    endif
else
    ifeq ($(MERKLE),1)
        SRCS    := sm3.c test_merkle.c
        TARGET  := $(MERKLE_TARGET)
    else
        SRCS    := sm3.c sm3test.c
    endif
endif

.PHONY: all clean

all:
	@echo "Building $(TARGET) from $(SRCS)…"
	@rm -f *.o                        # 确保没有残留的 .o
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET)
	@echo "Built $(TARGET)"

clean:
	@rm -f $(TARGET) $(SIMD_TARGET) $(MERKLE_TARGET) $(SIMD_MERKLE_TARGET)