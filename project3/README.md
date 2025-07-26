# 用circom实现poseidon2哈希算法的电路

## 任务概述

使用circom实现poseidon2哈希算法的电路（其中哈希算法参数(n,t,d)=(256,3,5)），然后使用SnarkJS工具运行circom代码，
构建基于Groth16算法的poseidon2哈希函数零知识证明协议并验证

## Groth16 简要介绍

### 1. 核心思想
- **类型**：非交互式 zk‑SNARK（零知识简洁非交互式论证）。  
- **目标**：在不泄露私有输入（witness）的前提下，对任何可表示为 R1CS（Rank‑1 Constraint System）的计算关系生成极短的证明，并能快速验证。  
- **技术基础**：  
  - 多项式承诺（Polynomial Commitments）  
  - 椭圆曲线双线性配对（Bilinear Pairing）  
  - Fiat–Shamir 变换（将交互式协议非交互化）

### 2. 基本流程
1. **Trusted Setup（可信设置）**  
   - 输入：电路的 R1CS 文件 + 通用憑證（如 Powers‑of‑Tau）。  
   - 输出：  
     - **Proving Key (PK)**：用于生成证明  
     - **Verifying Key (VK)**：用于验证证明  
2. **Prove（生成证明）**  
   - 输入：PK + 私有输入（witness） + 公开输入  
   - 步骤：  
     1. 构造一系列多项式承诺  
     2. 对承诺值执行 Fiat–Shamir 哈希，生成随机挑战  
     3. 计算配对相关元素  
   - 输出：固定大小 (~200 字节) 的 **Proof**  
3. **Verify（验证证明）**  
   - 输入：VK + 公开输入 + Proof  
   - 步骤：  
     - 执行若干次椭圆曲线配对检验  
   - 输出：`true` 或 `false`

### 3. 优缺点
- **优点**  
  - 证明体积小（≈200 B），与电路复杂度无关  
  - 验证快速（几次配对运算）  
  - 工具链成熟（Circom + SnarkJS、libsnark、Arkworks 等）  
- **缺点**  
  - 需要 per‑circuit 的 Trusted Setup  
  - 不原生支持递归证明（需额外构造）

### 4. 典型应用
- **隐私币**：Zcash  
- **Layer‑2 扩容**：zkSync v1、StarkNet（部分方案）  
- **通用 ZK电路**：Circom/SnarkJS 平台上的各种自定义证明  

## 3.证明流程

### 1.编译电路
```
circom poseidon2.circom --r1cs --wasm --sym -o build/
```

### 2.Groth16初始化
```
# 1) 初次 setup：.r1cs + ptau → .zkey（将通用参数“定制化”到特定的电路上，生成一个与电路结构绑定的初始密钥文件。）
snarkjs groth16 setup build/poseidon2.r1cs \
  powersOfTau28_hez_final_10.ptau \
  build/poseidon2_0000.zkey

# 2) 贡献熵（增强证明系统在理论上的安全性，将贡献熵设置为helloworld）
snarkjs zkey contribute \
  build/poseidon2_0000.zkey \
  build/poseidon2_final.zkey \
  --name="First contribution" \
  -v

# 3) 导出 Verification Key（用于链上或本地验证）
snarkjs zkey export verificationkey \
  build/poseidon2_final.zkey \
  build/verification_key.json

```

### 3.生成input.json文件（指定输入以及期望的hash结果）
可以先随机写入两个输入（根据给定接口），形如：
```
{
    "in_message": ["1234567890123456", "1111111111111111"],
    "expected_hash_output": "0"
}
```
然后直接进行第四步，根据报错结果查看内容，但是对于某些版本来说，可能这个方案无法行得通，例如报错：
```
/program/project3/build/poseidon2_js/witness_calculator.js:166
                    throw new Error(err);
                          ^

Error: Error: Assert Failed.
Error in template Poseidon2Hash_65 line: 117

    at /mnt/d/SDU/second_semester_of_junior_year/网络安全创新创业实践/program/project3/build/poseidon2_js/witness_calculator.js:166:27
    at Array.forEach (<anonymous>)
    at WitnessCalculator._doCalculateWitness (/mnt/d/SDU/second_semester_of_junior_year/网络安全创新创业实践/program/project3/build/poseidon2_js/witness_calculator.js:141:14)
    at WitnessCalculator.calculateWitness (/mnt/d/SDU/second_semester_of_junior_year/网络安全创新创业实践/program/project3/build/poseidon2_js/witness_calculator.js:179:20)
    at /mnt/d/SDU/second_semester_of_junior_year/网络安全创新创业实践/program/project3/build/poseidon2_js/generate_witness.js:11:39

Node.js v22.17.0
```
此时，只能选择修改.circom文件，将`signal input expected_hash_output;`修改为`signal output actual_hash_output;`，将`expected_hash_output === states_history[TOTAL_ROUNDS][0];`
修改为`actual_hash_output <== states_history[TOTAL_ROUNDS][0];`，然后重复1,2两步后，修改json输入（去除第二个参数），进行第4步，在成功运行后，会发现build文件夹中多出了witness.wtns文件，使用指令：
```
snarkjs wtns export json build/witness.wtns build/witness.json
```
将其转换为json格式并查看，得到最终的生成结果，注意，第二个参数为hash函数输出结果

### 4.生成witness
```
node build/poseidon2_js/generate_witness.js \
  build/poseidon2_js/poseidon2.wasm \
  input.json \
  build/witness.wtns
```
成功后会在 build/poseidon2_js/ 目录下看到 witness.wtns。

### 5.生成proof
```
snarkjs groth16 prove \
  build/poseidon2_final.zkey \
  build/witness.wtns \
  build/proof.json \
  build/public.json
```
其中proof.json：零知识证明  public.json：公开输入（包含 hashPub）

### 6.验证 Proof
```
snarkjs groth16 verify \
  build/verification_key.json \
  build/public.json \
  build/proof.json
```
可以看到验证成功：
![零知识证明结果](images/zkoutput.png)

```
```

# 附录：
**poseidon2算法说明与代码README**

## 报告 (Report)

### 1. 引言

本报告详细介绍了基于 Circom 2.2.2 实现的 Poseidon2 哈希函数电路设计与实现思路。Poseidon 是一种适用于零知识证明系统（ZK-SNARKs）的哈希函数，其核心特性是：

* **高效的多项式约束结构**，能够在算术电路中以较少的约束实现非线性映射。
* **可调参数化**，通过全 S-Box 轮和部分 S-Box 轮的组合，确保抗差分和抗线性攻击强度。

本电路模板包括：

1. **S-Box**: 非线性映射，采用 $x^5$ 实现。
2. **Poseidon2Round**: 单轮逻辑，包括加轮常数、S-Box 变换、MDS 矩阵扩散。
3. **Poseidon2Hash**: 整体哈希流程，按顺序执行全轮和部分轮并在末尾约束输出。

---

### 2. 数学推导与表示

#### 2.1 S-Box 设计 ($x^5$)

S-Box 是 Poseidon 的核心非线性部分，定义如下：

$\mathrm{SBox}(x) = x^5. $

将 $x^5$ 分解以减少电路约束：

1. $x^2 = x \cdot x$;
2. $x^3 = x^2 \cdot x$;
3. $x^4 = x^3 \cdot x$;
4. $x^5 = x^4 \cdot x$.

对应 Circom 电路，每一步通过一次乘法约束完成，合计 4 次乘法约束实现 $x^5$。

#### 2.2 轮常数加法

Poseidon 的第 $r$ 轮，对状态向量 $\mathbf{s}^r = (s\_0, s\_1, \dots, s\_{t-1})$ 添加轮常数：

$s_i' = s_i + c^r_i, \quad i = 0, \dots, t-1,$

其中 $c^r\_i$ 是预先定义的常量阵。本实现简化为：

$c^r_i = 3r + i + 1.$

#### 2.3 部分与全 S-Box 轮

* **全 S-Box 轮 (full rounds)**: 对所有 $t$ 个分量均应用 S-Box。
* **部分 S-Box 轮 (partial rounds)**: 仅对第 0 分量应用 S-Box，其余分量保持线性。

设总轮数为 $R = R\_F + R\_P$，其中 $R\_F$ 全轮数，$R\_P$ 部分轮数。通常取 $R\_F$ 较小，$R\_P$ 较大，以在保证安全的前提下降低非线性代价。

#### 2.4 MDS 矩阵扩散

扩散层使用最大距离可分离 (Maximum Distance Separable, MDS) 矩阵 $M \in \mathbb{F}^{t\times t}$，保证任何输入差异都能影响所有输出：

$\mathbf{s}^{r+1} = M \times \mathbf{s}_{\text{after SBox}}^r.$

本实现硬编码 $t=3$ 时的 MDS 矩阵：

$M = \begin{pmatrix} 2 & 1 & 1 \\ 1 & 2 & 1 \\ 1 & 1 & 2 \end{pmatrix}.$

### 3. Circom 实现细节

1. **模板参数化**：

   * `Poseidon2Round(current_round_type, round_index, state_width, total_rounds_count)` 接受当前轮类型、轮索引、状态宽度和总轮数，使得模板可扩展。
2. **常量定义**：

   * 在编译时通过 `var` 硬编码 MDS 矩阵和轮常数数组；简化了运行时计算成本。
3. **电路连接**：

   * 使用 `signal input` 和 `signal output` 定义输入输出；`component` 数组按顺序链接轮组件。
4. **输出约束**：

   * 在 `Poseidon2Hash` 中，使用 `expected_hash_output === states_history[TOTAL_ROUNDS][0];` 约束预期输出与电路最终状态相等。

### 4. 性能与安全性考虑

* **约束计数**：

  * 每个 S-Box 消耗 4 个乘法约束，全轮 $t$ 个分量即 $4t$ 约束，部分轮 4 个约束。MDS 线性层无乘法约束开销。
  * 总乘法约束约为 $4tR\_F + 4R\_P$。
* **安全强度**：

  * 采用全/部分轮混合设计，可防止差分/线性攻击。
  * MDS 矩阵保证扩散性，使扰动无法局限于部分分量。

---

## README

# Poseidon2 Circom 实现

## 简介

本项目基于 Circom 2.2.2 实现了适用于 ZK-SNARKs 的 Poseidon2 哈希函数电路。

## 接口说明

- **SBox**
  - 输入: `in_val` (field)
  - 输出: `out_val = in_val^5`

- **Poseidon2Round**
  - 参数: `current_round_type` (0 全轮, 1 部分轮), `round_index`, `state_width`, `total_rounds_count`
  - 输入: `prev_state[ state_width ]`
  - 输出: `next_state[ state_width ]`

- **Poseidon2Hash**
  - 输入: `in_message[2]` (消息元素数组)
  - 输入: `expected_hash_output` (约束输出)
  - 将抛出约束，确保最终哈希与预期一致。

## 快速开始 (Demo)

1. 安装 Circom：
   ```bash
   npm install -g circom@2.2.2
   ```

2. 编译电路：

   ```bash
   circom poseidon2.circom --r1cs --wasm --sym
   ```
3. 生成证明与验证：

   ```bash
   snarkjs groth16 setup poseidon2.r1cs pot12_final.ptau circuit_0000.zkey
   snarkjs groth16 prove circuit_0000.zkey witness.wtns proof.json public.json
   snarkjs groth16 verify verification_key.json public.json proof.json
   ```

## 参数配置

* `RF_FULL_ROUNDS`: 全 S-Box 轮数，默认 8。
* `RF_PARTIAL_ROUNDS`: 部分 S-Box 轮数，默认 56。
* `STATE_WIDTH`: 状态宽度，默认 3。























