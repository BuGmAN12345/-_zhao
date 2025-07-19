#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "sm3.h"

#define HASH_SIZE 32
#define LEAF_COUNT 100000

typedef struct {
    uint8_t hash[HASH_SIZE];
} HashNode;

typedef struct {
    HashNode **nodes;
    int *level_counts;
    int height;
} MerkleTree;

typedef struct {
    uint8_t **hashes;
    int *directions; // 0=left, 1=right
    int path_length;
} MerkleProof;

// 叶子节点哈希：hash(0x00 || leaf_data)
void hash_leaf(uint8_t *leaf_data, int data_len, uint8_t *output) {
    uint8_t *input = malloc(1 + data_len);
    input[0] = 0x00;
    memcpy(input + 1, leaf_data, data_len);
    sm3(input, 1 + data_len, output);
    free(input);
}

// 内部节点哈希：hash(0x01 || left_hash || right_hash)
void hash_internal(uint8_t *left_hash, uint8_t *right_hash, uint8_t *output) {
    uint8_t input[1 + 2 * HASH_SIZE];
    input[0] = 0x01;
    memcpy(input + 1, left_hash, HASH_SIZE);
    memcpy(input + 1 + HASH_SIZE, right_hash, HASH_SIZE);
    sm3(input, 1 + 2 * HASH_SIZE, output);
}

// 构建Merkle树
MerkleTree* build_merkle_tree(uint8_t **leaf_data, int *data_lengths) {
    MerkleTree *tree = malloc(sizeof(MerkleTree));
    
    // 计算树的高度
    int temp_count = LEAF_COUNT;
    tree->height = 0;
    while (temp_count > 1) {
        temp_count = (temp_count + 1) / 2;
        tree->height++;
    }
    tree->height++; // 包括叶子层
    
    // 分配内存
    tree->level_counts = malloc(tree->height * sizeof(int));
    tree->nodes = malloc(tree->height * sizeof(HashNode*));
    
    // 计算每层节点数
    temp_count = LEAF_COUNT;
    for (int i = 0; i < tree->height; i++) {
        tree->level_counts[i] = temp_count;
        tree->nodes[i] = malloc(temp_count * sizeof(HashNode));
        temp_count = (temp_count + 1) / 2;
    }
    
    // 构建叶子层
    for (int i = 0; i < LEAF_COUNT; i++) {
        hash_leaf(leaf_data[i], data_lengths[i], tree->nodes[0][i].hash);
    }
    
    // 构建内部层
    for (int level = 1; level < tree->height; level++) {
        int prev_level = level - 1;
        int prev_count = tree->level_counts[prev_level];
        
        for (int i = 0; i < tree->level_counts[level]; i++) {
            int left_idx = 2 * i;
            int right_idx = 2 * i + 1;
            
            if (right_idx < prev_count) {
                hash_internal(tree->nodes[prev_level][left_idx].hash,
                            tree->nodes[prev_level][right_idx].hash,
                            tree->nodes[level][i].hash);
            } else {
                // 奇数个节点，直接提升左节点
                memcpy(tree->nodes[level][i].hash, 
                       tree->nodes[prev_level][left_idx].hash, HASH_SIZE);
            }
        }
    }
    
    return tree;
}

// 生成存在性证明
MerkleProof* generate_inclusion_proof(MerkleTree *tree, int leaf_index) {
    if (leaf_index >= LEAF_COUNT) return NULL;
    
    MerkleProof *proof = malloc(sizeof(MerkleProof));
    proof->path_length = tree->height - 1;
    proof->hashes = malloc(proof->path_length * sizeof(uint8_t*));
    proof->directions = malloc(proof->path_length * sizeof(int));
    
    for (int i = 0; i < proof->path_length; i++) {
        proof->hashes[i] = malloc(HASH_SIZE);
    }
    
    int current_index = leaf_index;
    
    for (int level = 0; level < tree->height - 1; level++) {
        int sibling_index;
        
        if (current_index % 2 == 0) {
            // 当前节点是左子节点
            sibling_index = current_index + 1;
            proof->directions[level] = 1; // 兄弟节点在右侧
        } else {
            // 当前节点是右子节点
            sibling_index = current_index - 1;
            proof->directions[level] = 0; // 兄弟节点在左侧
        }
        
        if (sibling_index < tree->level_counts[level]) {
            memcpy(proof->hashes[level], 
                   tree->nodes[level][sibling_index].hash, HASH_SIZE);
        } else {
            // 没有兄弟节点，使用空哈希
            memset(proof->hashes[level], 0, HASH_SIZE);
        }
        
        current_index = current_index / 2;
    }
    
    return proof;
}

// 验证存在性证明
int verify_inclusion_proof(MerkleProof *proof, uint8_t *leaf_data, int data_len,
                          int leaf_index, uint8_t *root_hash) {
    uint8_t current_hash[HASH_SIZE];
    hash_leaf(leaf_data, data_len, current_hash);
    
    for (int i = 0; i < proof->path_length; i++) {
        uint8_t next_hash[HASH_SIZE];
        
        if (proof->directions[i] == 0) {
            // 兄弟节点在左侧
            hash_internal(proof->hashes[i], current_hash, next_hash);
        } else {
            // 兄弟节点在右侧
            hash_internal(current_hash, proof->hashes[i], next_hash);
        }
        
        memcpy(current_hash, next_hash, HASH_SIZE);
    }
    
    return memcmp(current_hash, root_hash, HASH_SIZE) == 0;
}

// 生成不存在性证明
MerkleProof* generate_non_inclusion_proof(MerkleTree *tree, uint8_t *target_hash) {
    // 找到目标哈希应该插入的位置
    int insert_pos = 0;
    for (int i = 0; i < LEAF_COUNT; i++) {
        if (memcmp(tree->nodes[0][i].hash, target_hash, HASH_SIZE) < 0) {
            insert_pos = i + 1;
        } else if (memcmp(tree->nodes[0][i].hash, target_hash, HASH_SIZE) == 0) {
            return NULL; // 目标已存在
        } else {
            break;
        }
    }
    
    // 生成相邻叶子节点的证明
    MerkleProof *proof = malloc(sizeof(MerkleProof));
    proof->path_length = 2; // 包含前后两个相邻节点的信息
    proof->hashes = malloc(2 * sizeof(uint8_t*));
    proof->directions = malloc(2 * sizeof(int));
    
    for (int i = 0; i < 2; i++) {
        proof->hashes[i] = malloc(HASH_SIZE);
    }
    
    // 前一个节点
    if (insert_pos > 0) {
        memcpy(proof->hashes[0], tree->nodes[0][insert_pos - 1].hash, HASH_SIZE);
        proof->directions[0] = 0;
    } else {
        memset(proof->hashes[0], 0, HASH_SIZE);
        proof->directions[0] = 0;
    }
    
    // 后一个节点
    if (insert_pos < LEAF_COUNT) {
        memcpy(proof->hashes[1], tree->nodes[0][insert_pos].hash, HASH_SIZE);
        proof->directions[1] = 1;
    } else {
        memset(proof->hashes[1], 0xFF, HASH_SIZE);
        proof->directions[1] = 1;
    }
    
    return proof;
}

// 验证不存在性证明
int verify_non_inclusion_proof(MerkleProof *proof, uint8_t *target_hash) {
    if (proof->path_length != 2) return 0;
    
    uint8_t *prev_hash = proof->hashes[0];
    uint8_t *next_hash = proof->hashes[1];
    
    // 检查目标哈希是否在两个相邻节点之间
    int prev_cmp = memcmp(prev_hash, target_hash, HASH_SIZE);
    int next_cmp = memcmp(target_hash, next_hash, HASH_SIZE);
    
    return (prev_cmp < 0 && next_cmp < 0);
}

// 释放Merkle树内存
void free_merkle_tree(MerkleTree *tree) {
    for (int i = 0; i < tree->height; i++) {
        free(tree->nodes[i]);
    }
    free(tree->nodes);
    free(tree->level_counts);
    free(tree);
}

// 释放证明内存
void free_proof(MerkleProof *proof) {
    for (int i = 0; i < proof->path_length; i++) {
        free(proof->hashes[i]);
    }
    free(proof->hashes);
    free(proof->directions);
    free(proof);
}

// 测试函数
int main() {
    // 准备叶子数据
    uint8_t **leaf_data = malloc(LEAF_COUNT * sizeof(uint8_t*));
    int *data_lengths = malloc(LEAF_COUNT * sizeof(int));
    
    for (int i = 0; i < LEAF_COUNT; i++) {
        leaf_data[i] = malloc(32);
        snprintf((char*)leaf_data[i], 32, "leaf_%d", i);
        data_lengths[i] = strlen((char*)leaf_data[i]);
    }
    
    printf("构建Merkle树...\n");
    MerkleTree *tree = build_merkle_tree(leaf_data, data_lengths);
    
    // 获取根哈希
    uint8_t *root_hash = tree->nodes[tree->height - 1][0].hash;
    
    printf("根哈希: ");
    for (int i = 0; i < HASH_SIZE; i++) {
        printf("%02x", root_hash[i]);
    }
    printf("\n");
    
    // 测试存在性证明
    int test_index = 12345;
    MerkleProof *inclusion_proof = generate_inclusion_proof(tree, test_index);
    
    int inclusion_result = verify_inclusion_proof(inclusion_proof, 
                                                 leaf_data[test_index], 
                                                 data_lengths[test_index],
                                                 test_index, root_hash);
    
    printf("存在性证明验证: %s\n", inclusion_result ? "通过" : "失败");
    
    // 测试不存在性证明
    uint8_t fake_data[] = "non_existent_leaf";
    uint8_t fake_hash[HASH_SIZE];
    hash_leaf(fake_data, strlen((char*)fake_data), fake_hash);
    
    MerkleProof *non_inclusion_proof = generate_non_inclusion_proof(tree, fake_hash);
    
    if (non_inclusion_proof) {
        int non_inclusion_result = verify_non_inclusion_proof(non_inclusion_proof, fake_hash);
        printf("不存在性证明验证: %s\n", non_inclusion_result ? "通过" : "失败");
        free_proof(non_inclusion_proof);
    } else {
        printf("目标已存在，无法生成不存在性证明\n");
    }
    
    // 清理内存
    free_proof(inclusion_proof);
    free_merkle_tree(tree);
    
    for (int i = 0; i < LEAF_COUNT; i++) {
        free(leaf_data[i]);
    }
    free(leaf_data);
    free(data_lengths);
    
    return 0;
}