# SM3算法实验报告

## 算法原理

SM3是中国国家密码管理局发布的密码杂凑算法标准，属于SHA-2系列的替代方案。SM3算法采用Merkle-Damgård结构，输出256位（32字节）的哈希值。

### 核心组件

1. **初始化向量（IV）**
   - 算法使用8个32位初始化向量
   - 代码中的初始值：`0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600, 0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E`

2. **消息扩展**
   - 将512位消息块扩展为68个32位字（W[0]到W[67]）
   - 生成64个32位字（W'[0]到W'[63]），其中W'[j] = W[j] ⊕ W[j+4]

3. **压缩函数**
   - 使用两种不同的布尔函数FF和GG
   - 前16轮使用FF0和GG0，后48轮使用FF1和GG1
   - 采用不同的常数T[j]：前16轮使用0x79CC4519，后48轮使用0x7A879D8A

4. **填充机制**
   - 消息后添加'1'位，然后添加'0'位使长度≡448 (mod 512)
   - 最后64位存储原始消息长度

## 代码优化方案

### 1. 宏定义优化
- **字节序转换宏**：`GET_ULONG_BE`和`PUT_ULONG_BE`宏实现高效的大端字节序转换
- **位运算宏**：`SHL`、`ROTL`、`P0`、`P1`等宏避免函数调用开销
- **布尔函数宏**：`FF0`、`FF1`、`GG0`、`GG1`直接展开为位运算

### 2. 内存管理优化
- **流式处理**：支持分块处理大文件，避免将整个文件加载到内存
- **缓冲区重用**：使用64字节缓冲区处理不完整的数据块
- **上下文结构**：维护算法状态，支持增量更新

### 3. 算法实现优化
- **消息扩展优化**：针对VC6编译器优化问题，使用临时变量避免编译器bug
- **循环展开**：在消息扩展和压缩函数中适度使用循环展开
- **避免重复计算**：预计算常数T[j]数组

### 4. 调试支持
- **条件编译**：使用`#ifdef _DEBUG`提供详细的中间状态输出
- **状态跟踪**：可以观察每轮迭代后的寄存器状态

## 性能特点

1. **内存效率**：固定大小的上下文结构，内存占用可预测
2. **处理能力**：支持流式处理，适合大文件哈希计算
3. **兼容性**：考虑了不同编译器的优化差异
4. **可扩展性**：支持HMAC-SM3扩展

## 测试用例

代码提供了两个标准测试向量：
- 输入"abc"，输出：`66c7f0f4 62eeedd9 d1f2d46b dc10e4e2 4167c487 5cf2f7a2 297da02b 8f4ba8e0`
- 输入64字节重复"abcd"，输出：`debe9ff9 2275b8a1 38604889 c18e5a4d 6fdb70e5 387e5765 293dcba3 9c0c5732`

---

# README

## 概述

这是一个完整的SM3密码哈希算法C语言实现，包含标准SM3算法和HMAC-SM3扩展。SM3是中国国家标准的密码杂凑算法，输出256位哈希值。

## 主要特性

- ✅ 完整的SM3算法实现
- ✅ 支持流式数据处理
- ✅ 文件哈希计算
- ✅ HMAC-SM3认证码生成
- ✅ 调试模式支持
- ✅ 跨平台兼容

## 编译要求

- C99兼容的编译器
- 需要包含`sm3.h`头文件
- 链接时需要标准C库

```bash
gcc -o sm3_test sm3.c main.c -std=c99
```

## 核心接口

### 1. 基本哈希函数

```c
void sm3(uint8_t *input, int ilen, uint8_t output[32]);
```
- **功能**：计算输入数据的SM3哈希值
- **参数**：
  - `input`：输入数据指针
  - `ilen`：输入数据长度
  - `output`：输出哈希值（32字节）

### 2. 流式处理接口

```c
void sm3_starts(sm3_context *ctx);
void sm3_update(sm3_context *ctx, uint8_t *input, int ilen);
void sm3_finish(sm3_context *ctx, uint8_t output[32]);
```
- **功能**：支持分块处理大量数据
- **用途**：适合处理大文件或流式数据

### 3. 文件哈希接口

```c
int sm3_file(char *path, uint8_t output[32]);
```
- **功能**：直接计算文件的SM3哈希值
- **返回值**：0=成功，1=文件打开失败，2=读取错误

### 4. HMAC-SM3接口

```c
void sm3_hmac(uint8_t *key, int keylen, uint8_t *input, int ilen, uint8_t output[32]);
```
- **功能**：计算HMAC-SM3认证码
- **参数**：
  - `key`：密钥数据
  - `keylen`：密钥长度
  - `input`：待认证数据
  - `ilen`：数据长度
  - `output`：输出认证码（32字节）

## 使用示例

### 基本哈希计算

```c
#include "sm3.h"
#include <stdio.h>
#include <string.h>

int main() {
    uint8_t input[] = "abc";
    uint8_t output[32];
    int i;
    
    // 计算哈希值
    sm3(input, strlen((char*)input), output);
    
    // 打印结果
    printf("SM3(\"abc\") = ");
    for (i = 0; i < 32; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    return 0;
}
```

### 流式处理示例

```c
#include "sm3.h"
#include <stdio.h>

int main() {
    sm3_context ctx;
    uint8_t output[32];
    uint8_t data1[] = "Hello, ";
    uint8_t data2[] = "World!";
    int i;
    
    // 初始化上下文
    sm3_starts(&ctx);
    
    // 分块更新
    sm3_update(&ctx, data1, strlen((char*)data1));
    sm3_update(&ctx, data2, strlen((char*)data2));
    
    // 完成计算
    sm3_finish(&ctx, output);
    
    // 打印结果
    printf("SM3(\"Hello, World!\") = ");
    for (i = 0; i < 32; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    return 0;
}
```

### 文件哈希示例

```c
#include "sm3.h"
#include <stdio.h>

int main() {
    uint8_t output[32];
    int ret, i;
    
    // 计算文件哈希
    ret = sm3_file("test.txt", output);
    
    if (ret == 0) {
        printf("File hash: ");
        for (i = 0; i < 32; i++) {
            printf("%02x", output[i]);
        }
        printf("\n");
    } else {
        printf("Error: %d\n", ret);
    }
    
    return 0;
}
```

### HMAC-SM3示例

```c
#include "sm3.h"
#include <stdio.h>
#include <string.h>

int main() {
    uint8_t key[] = "secret_key";
    uint8_t message[] = "Hello, HMAC!";
    uint8_t output[32];
    int i;
    
    // 计算HMAC
    sm3_hmac(key, strlen((char*)key), message, strlen((char*)message), output);
    
    // 打印结果
    printf("HMAC-SM3 = ");
    for (i = 0; i < 32; i++) {
        printf("%02x", output[i]);
    }
    printf("\n");
    
    return 0;
}
```

## 调试模式

编译时定义`_DEBUG`宏可以启用调试输出：

```bash
gcc -D_DEBUG -o sm3_debug sm3.c main.c
```

调试模式会输出：
- 消息填充后的内容
- 消息扩展结果（W[0-67]和W'[0-63]）
- 每轮压缩函数的寄存器状态

## 注意事项

1. **字节序**：算法使用大端字节序
2. **内存安全**：使用后请清零敏感数据
3. **编译器兼容**：针对VC6等老编译器进行了优化
4. **性能**：适合处理大文件，内存占用固定

## 测试验证

代码包含标准测试向量，可验证实现正确性：
- `sm3("abc")` 应该输出：`66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0`
- 64字节重复"abcd"应该输出：`debe9ff92275b8a138604889c18e5a4d6fdb70e5387e5765293dcba39c0c5732`

## 许可证

请根据实际情况添加相应的许可证信息。