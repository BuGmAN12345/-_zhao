pragma circom 2.2.2;

// S-box 模板：计算 x^5
template SBox() {
    signal input in_val;   // 输入值 x
    signal output out_val; // 输出值 x^5

    // 中间信号，用于将 x^5 的计算分解为二次约束
    signal val_sq;     // x^2
    signal val_cub;    // x^3
    signal val_quad;   // x^4

    // 二次约束实现 x^5
    val_sq <== in_val * in_val;
    val_cub <== val_sq * in_val;
    val_quad <== val_cub * in_val;
    out_val <== val_quad * in_val;
}

// 实现 Poseidon2 哈希函数的一轮逻辑
template Poseidon2Round(current_round_type, round_index, state_width, total_rounds_count) {
    signal input prev_state[state_width];  // 上一轮的状态输入
    signal output next_state[state_width]; // 本轮计算后的状态输出

    // MDS (Maximum Distance Separable) 矩阵，这里硬编码为 t=3
    var mds_matrix[3][3];
    mds_matrix[0][0] = 2; mds_matrix[0][1] = 1; mds_matrix[0][2] = 1;
    mds_matrix[1][0] = 1; mds_matrix[1][1] = 2; mds_matrix[1][2] = 1;
    mds_matrix[2][0] = 1; mds_matrix[2][1] = 1; mds_matrix[2][2] = 2;

    // 轮常数，硬编码为总轮数 64，状态宽度 3
    var round_constants[64][3];
    for (var r_idx = 0; r_idx < 64; r_idx++) {
        for (var i = 0; i < 3; i++) {
            round_constants[r_idx][i] = (r_idx * 3 + i + 1);
        }
    }

    // 1. 添加轮常数
    signal state_with_rc[state_width];
    for (var i = 0; i < state_width; i++) {
        state_with_rc[i] <== prev_state[i] + round_constants[round_index][i];
    }

    // 2. 应用 S-box
    signal state_after_sbox[state_width];
    component sbox_instances[state_width];

    if (current_round_type == 0) { // 全 S-box 轮次 (类型 0)
        for (var i = 0; i < state_width; i++) {
            sbox_instances[i] = SBox();
            sbox_instances[i].in_val <== state_with_rc[i];
            state_after_sbox[i] <== sbox_instances[i].out_val;
        }
    } else { // 部分 S-box 轮次 (类型 1)
        sbox_instances[0] = SBox();
        sbox_instances[0].in_val <== state_with_rc[0];
        state_after_sbox[0] <== sbox_instances[0].out_val;

        for (var i = 1; i < state_width; i++) {
            state_after_sbox[i] <== state_with_rc[i]; // 其他元素保持不变
        }
    }

    // 3. MDS 矩阵乘法
    for (var i = 0; i < state_width; i++) {
        next_state[i] <== (mds_matrix[i][0] * state_after_sbox[0]) +
                           (mds_matrix[i][1] * state_after_sbox[1]) +
                           (mds_matrix[i][2] * state_after_sbox[2]);
    }
}

// 实现整个 Poseidon2 哈希算法
template Poseidon2Hash() {
    // 定义全轮次、部分轮次和状态宽度
    var RF_FULL_ROUNDS = 8;     // 全 S-box 轮次数量
    var RF_PARTIAL_ROUNDS = 56; // 部分 S-box 轮次数量
    var TOTAL_ROUNDS = RF_FULL_ROUNDS + RF_PARTIAL_ROUNDS; // 总轮次：64
    var STATE_WIDTH = 3;        // 状态宽度 t

    // 输入：消息元素和预期哈希输出
    signal input in_message[STATE_WIDTH - 1];
    signal input expected_hash_output;
    //signal output actual_hash_output;

    // 存储每轮状态的数组
    signal states_history[TOTAL_ROUNDS + 1][STATE_WIDTH];

    // 初始化第一个状态：前两个元素来自输入消息，最后一个元素（容量元素）为 0
    states_history[0][0] <== in_message[0];
    states_history[0][1] <== in_message[1];
    states_history[0][2] <== 0;

    // 轮次组件实例数组
    component round_components[TOTAL_ROUNDS];

    // 循环执行所有哈希轮次
    for (var r_idx = 0; r_idx < TOTAL_ROUNDS; r_idx++) {
        // 判断当前轮次是全 S-box 轮次 (0) 还是部分 S-box 轮次 (1)
        var current_round_type_val = (r_idx < (RF_FULL_ROUNDS / 2)) ||
                                     (r_idx >= TOTAL_ROUNDS - (RF_FULL_ROUNDS / 2)) ? 0 : 1;

        // 实例化并连接当前轮次组件
        round_components[r_idx] = Poseidon2Round(current_round_type_val, r_idx, STATE_WIDTH, TOTAL_ROUNDS);

        // 连接当前轮次的输入状态
        for (var i = 0; i < STATE_WIDTH; i++) {
            round_components[r_idx].prev_state[i] <== states_history[r_idx][i];
        }

        // 保存当前轮次的输出状态，作为下一轮的输入
        for (var i = 0; i < STATE_WIDTH; i++) {
            states_history[r_idx + 1][i] <== round_components[r_idx].next_state[i];
        }
    }

    // 最终哈希结果：约束预期输出与最终状态的第一个元素相等
    expected_hash_output === states_history[TOTAL_ROUNDS][0];
    //actual_hash_output <== states_history[TOTAL_ROUNDS][0]; // 输出最终哈希结果用于获取hash值
}

// Main component of the circuit
component main = Poseidon2Hash();