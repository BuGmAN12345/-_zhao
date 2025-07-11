# 实验报告

## 一、实验目的
- 掌握国密 SM4 对称分组密码算法的工作原理与实现方法。  
- 理解 SM4 算法中的轮函数、线性变换与 S‑box 查表的具体实现。  
- 在源码层面分析并总结本实现所采用的各种优化手段。

## 二、算法原理

### 1. SM4 概述
SM4 是中国国家密码管理局发布的对称分组密码标准，分组长度 128 bit，密钥长度 128 bit，采用 32 轮非对称 Feistel 结构。每轮主要包含以下操作：  
1. **轮密钥加**：将当前轮的子密钥与状态字进行异或。  
2. **非线性变换 S‑box**：对 32 bit 输入分为 4 个字节，分别通过 8×8 S‑box 查表得到输出。  
3. **线性变换 L**：对 S‑box 输出做循环左移并异或，产生新的 32 bit 状态字。  
4. **状态更新**：将新状态与前四次状态按特定次序组合，继续进入下一轮。

### 2. 主要函数流程
- **sm4_setkey** / **sm4_setkey_enc** / **sm4_setkey_dec**：  
  - 从 128 bit 主密钥派生 32 个 32 bit 轮密钥（子密钥），包含取大端、异或系统常量 FK、经 S‑box + 线性变换 L′ 后与 CK 异或等步骤。  
  - 加密和解密的子密钥序列顺序相反，以支持反向运算。
- **sm4_one_round**：  
  - 将 128 bit 明文切分为四个 32 bit 状态字，依次调用 **sm4F**（结合 S‑box + 线性变换 sm4Lt）与轮密钥，迭代 32 轮，最后输出逆序拼接的四个状态字作为一轮加密结果。
- **sm4_crypt_ecb** / **sm4_crypt_cbc**：  
  - ECB 模式：每 16 Bytes 独立加密；  
  - CBC 模式：加密时先与 IV 异或再加密，并更新 IV；解密时先解密再与 IV 异或。

## 三、本代码的优化方案

1. **宏定义简化高性能位运算**  
   - 使用 `GET_ULONG_BE` / `PUT_ULONG_BE` 宏实现大端字节序与 32 bit 整数相互转换，将循环与位移合并，减少函数调用开销。  
   - `SHL`、`ROTL` 宏一次完成 32 bit 循环左移，避免多步位移和掩码操作。

2. **S‑box 查表与线性变换合并**  
   - 在 `sm4Lt` 与 `sm4CalciRK` 中，先将输入打散为 4 字节通过 `sm4Sbox` 查表，再一次性用 `GET_ULONG_BE` 还原并进行多次循环移位与异或，将非线性和线性变换合并，提高缓存命中率。

3. **内联小函数避免额外调用开销**  
   - 将 `sm4Sbox`、`sm4Lt`、`sm4F`、`sm4CalciRK` 等声明为 `static inline`（或按宏展开），减少函数栈开销与跳转延迟。

4. **循环展开与本地变量重用**  
   - 在 `sm4_one_round` 中，将状态字数组 `ulbuf` 预先申请一次，循环内部只更新必要位置，避免动态分配或频繁 memset。

5. **模式复用**  
   - ECB 与 CBC 模式的核心都调用同一轮函数 `sm4_one_round`，减少重复代码，便于编译器优化。

---

# README

## 一、简介
本项目提供国密 SM4 对称分组密码的纯 C 语言实现，支持 ECB 与 CBC 两种加解密模式，适用于嵌入式与高性能场景。

## 二、环境依赖
- C99 标准兼容编译器（如 `gcc`, `clang`）
- 无额外第三方库依赖

## 三、接口说明

```c
// SM4 上下文结构
typedef struct {
    int      mode;   // SM4_ENCRYPT 或 SM4_DECRYPT
    unsigned long sk[32];  // 32 轮子密钥
} sm4_context;

// 轮密钥生成（加密用）
void sm4_setkey_enc( sm4_context *ctx, unsigned char key[16] );
// 轮密钥生成（解密用）
void sm4_setkey_dec( sm4_context *ctx, unsigned char key[16] );

// ECB 模式加/解密
// mode: SM4_ENCRYPT 或 SM4_DECRYPT
// length: 字节数，必须是 16 的整数倍
void sm4_crypt_ecb( sm4_context *ctx,
                    int mode,
                    int length,
                    unsigned char *input,
                    unsigned char *output );

// CBC 模式加/解密
// iv: 初始向量，16 字节
void sm4_crypt_cbc( sm4_context *ctx,
                    int mode,
                    int length,
                    unsigned char iv[16],
                    unsigned char *input,
                    unsigned char *output );
```

## 四、基本函数测试：
在100万次加密测试中，结果如下：
![普通加密测试](加密.png)