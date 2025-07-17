// sm4_gcm_openssl.c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdbool.h>

#include "sm4_avx.h"        

static const uint8_t test_plain_tv1[SM4_BLOCK_SIZE] = {
    0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
    0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
};
static const uint8_t test_key_tv1[SM4_KEY_SIZE] = {
    0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef,
    0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10
};
static const uint8_t test_cipher_expected_tv1[SM4_BLOCK_SIZE] = {
    0x68, 0x1e, 0xdf, 0x34, 0xd2, 0x06, 0x96, 0x5e,
    0x86, 0xb3, 0xe9, 0x4f, 0x53, 0x6e, 0x42, 0x46
};

static const uint8_t hash_key[SM4_BLOCK_SIZE] = {
    0x66, 0xe9, 0x4b, 0xd4, 0xef, 0x8a, 0x2c, 0x3b,
    0x88, 0x4c, 0xfa, 0x59, 0xca, 0x34, 0x2b, 0x2e
};

static const uint8_t append_infomation[SM4_BLOCK_SIZE] = { //附加消息部分
    0x66, 0x9a, 0x4b, 0xd4, 0xef, 0x8a, 0x2c, 0x3b,
    0x58, 0x4c, 0xfa, 0x59, 0x01, 0x34, 0x24, 0x2e
};

void print_hex_data_test(const char* label, const uint8_t* data, int len) { //打印16进制数据
    printf("%s: ", label);
    for (int i = 0; i < len; ++i) {
        printf("%02x", data[i]);
    }
    printf("\n");
}

void generate_test_block(uint8_t block[SM4_BLOCK_SIZE], uint64_t i, bool regenerate_random) { //生成CTR模式数据块
    static uint8_t fixed_random[8];  // 前 8 字节保持不变，除非显式要求
    static bool initialized = false;
    if (!initialized || regenerate_random) { // 如果需要重新生成随机数IV
        for (int j = 0; j < 8; j++) {
            fixed_random[j] = rand() & 0xFF;
        }
        initialized = true;
    }
    // 前 8 字节复制过去
    for (int j = 0; j < 8; j++) {
        block[j] = fixed_random[j];
    }
    // 后 8 字节写入 i（大端序）
    for (int j = 0; j < 8; j++) {
        block[8 + j] = (i >> (56 - 8 * j)) & 0xFF;
    }
}

//下面实现Gmac核心函数Mh块mac操作
// GF(2^128)的既约多项式: x^128 + x^7 + x^2 + x + 1
#define GF_POLYNOMIAL 0x87

// 将128位数据右移1位
static void right_shift_128(uint8_t *data) {
    int i;
    uint8_t carry = 0;
    
    for (i = 0; i < 16; i++) {
        uint8_t new_carry = data[i] & 1;
        data[i] = (data[i] >> 1) | (carry << 7);
        carry = new_carry;
    }
}

// 将128位数据左移1位
static void left_shift_128(uint8_t *data) {
    int i;
    uint8_t carry = 0;
    
    for (i = 15; i >= 0; i--) {
        uint8_t new_carry = (data[i] & 0x80) ? 1 : 0;
        data[i] = (data[i] << 1) | carry;
        carry = new_carry;
    }
}

// 在GF(2^128)上进行乘法运算（最简单的实现）
void gmac_multiply_block(uint8_t *result, const uint8_t *x, const uint8_t *y) {
    uint8_t temp_x[16];
    uint8_t temp_result[16];
    int i, j;
    
    // 清零结果
    memset(temp_result, 0, 16);
    memcpy(temp_x, x, 16);
    
    // 对y的每一位进行处理
    for (i = 0; i < 16; i++) {
        for (j = 0; j < 8; j++) {
            // 如果y的当前位是1，则将temp_x加到结果中
            if (y[i] & (1 << (7 - j))) {
                for (int k = 0; k < 16; k++) {
                    temp_result[k] ^= temp_x[k];
                }
            }
            
            // 左移temp_x
            uint8_t msb = temp_x[0] & 0x80;
            left_shift_128(temp_x);
            
            // 如果最高位是1，则异或既约多项式
            if (msb) {
                temp_x[15] ^= GF_POLYNOMIAL;
            }
        }
    }
    
    memcpy(result, temp_result, 16);
}

// GMAC的Mh块操作函数
void gmac_mh_block(uint8_t *input, const uint8_t *output) {
    // 在GMAC中，Mh块就是输入数据与哈希密钥的GF(2^128)乘法
    gmac_multiply_block(output, input, hash_key);
}

void sm4_xor_blocks(uint8_t *a, uint8_t *b, size_t block_num) //将两个长度为SM4_BLOCK_SIZE的基本输入分块进行亦或
{
    for (size_t i = 0; i < block_num * SM4_BLOCK_SIZE; ++i) 
    {
        a[i] ^= b[i];
    }
}

void sm4_gcm(uint8_t *correctness_input,size_t num_correctness_blocks,uint8_t *mac_res) //gcm模式进行可认证加密
{
    sm4_avx_ctx ctx_enc;
    uint8_t *correctness_output = (uint8_t*)malloc((num_correctness_blocks+1) * SM4_BLOCK_SIZE);
    uint8_t *CTR_input = (uint8_t*)malloc((num_correctness_blocks+1) * SM4_BLOCK_SIZE);
    uint8_t tmp[SM4_BLOCK_SIZE]; //生成CTR块
    for (size_t i = 0; i <= num_correctness_blocks; ++i) {
        generate_test_block(tmp,i,false);
        memcpy(CTR_input + i * SM4_BLOCK_SIZE, tmp , SM4_BLOCK_SIZE);
    }
    sm4_avx_init(&ctx_enc, test_key_tv1, 1);
    sm4_avx_encrypt_blocks(&ctx_enc, CTR_input, correctness_output, num_correctness_blocks+1);
    sm4_xor_blocks(correctness_output+SM4_BLOCK_SIZE, correctness_input, num_correctness_blocks); //将CTR输出与输入进行异或
    gmac_mh_block(append_infomation,tmp); //计算附加消息的Mh块
    for(size_t i = SM4_BLOCK_SIZE; i <= num_correctness_blocks * SM4_BLOCK_SIZE; i+=SM4_BLOCK_SIZE)
    {
        sm4_xor_blocks(tmp,correctness_output+i,1); //将Mh块与每个分组进行异或
        gmac_mh_block(tmp,tmp); //计算Mh块
    }
    sm4_xor_blocks(tmp,correctness_output,1); //将Mh块与初始消息亦或
    memcpy(mac_res, tmp, SM4_BLOCK_SIZE); //将最终的Mh块作为MAC结果

    free(correctness_output);
    free(CTR_input);
}

int main(int argc, char *argv[]) {
    sm4_avx_ctx ctx_dec;

    printf("SM4 AVX 8-Block Target Implementation Test Suite\n");
    printf("================================================\n\n");

    size_t num_correctness_blocks = 256; //设明文共256个块 
    uint8_t *correctness_input = (uint8_t*)malloc(num_correctness_blocks * SM4_BLOCK_SIZE);
    uint8_t *correctness_decrypted = (uint8_t*)malloc(num_correctness_blocks * SM4_BLOCK_SIZE);

    if (!correctness_input || !correctness_decrypted) {
        fprintf(stderr, "Failed to allocate memory for correctness test.\n");
        return 1;
    }

    for (size_t i = 0; i < num_correctness_blocks; ++i) { //生成明文块
        memcpy(correctness_input + i * SM4_BLOCK_SIZE, test_plain_tv1, SM4_BLOCK_SIZE);
    }
    
    //print_hex_data_test("Plaintext (TV1, 1st block) ", correctness_input, SM4_BLOCK_SIZE);
    uint8_t *mac_res = (uint8_t*)malloc(SM4_BLOCK_SIZE);
    sm4_gcm(correctness_input,num_correctness_blocks,mac_res);
    print_hex_data_test("MAC Result (GCM)           ", mac_res, SM4_BLOCK_SIZE);

    free(correctness_input);
    free(mac_res);
    free(correctness_decrypted);

    return 0;
}