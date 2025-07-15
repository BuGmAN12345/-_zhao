# --------------------------------------------------------------------
# Toolchain
CC         := gcc
CFLAGS     := -Wall -Wextra -O3
LDFLAGS    :=

# 默认源文件（可被下面的条件覆盖）
SM4_SRC    := sm4.c
TEST_SRC   := sm4test.c
SM4_CFLAGS :=

# 如果开启 SIMD，则使用 simd 实现，并添加 AVX2 参数，测试程序也切到 simd 版
ifeq ($(SIMD),1)
SM4_SRC     := sm4_simd.c
SM4_CFLAGS += -mavx2 -march=native
TEST_SRC    := sm4test_simd.c
endif

# 如果开启 GCM，则不管 SIMD 与否，测试程序都改为 GCM 扩展版
ifeq ($(GCM),1)
TEST_SRC := test_sm4_gcm.c
endif

# 最终的可执行文件名
TARGET := sm4_test

# 默认目标
.PHONY: all
all: $(TARGET)

# 链接规则：直接以 .c 为输入，编译并链接，随后清理所有 .o
$(TARGET): $(SM4_SRC) $(TEST_SRC)
	$(CC) $(CFLAGS) $(SM4_CFLAGS) $^ -o $@ $(LDFLAGS)
	@rm -f *.o

# 清理
.PHONY: clean
clean:
	@rm -f $(TARGET) *.o
