import binascii
from random import choice
import func
from gmssl import sm3
from Cryptodome.Util.asn1 import DerSequence, DerInteger
from binascii import unhexlify
# 选择素域，设置椭圆曲线参数

default_ecc_table = {
    'n': 'FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123',
    'p': 'FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF',
    'g': '32c4ae2c1f1981195f9904466a39c9948fe30bbff2660be1715a4589334c74c7'
         'bc3736a2f4f6779c59bdcee36b692153d0a9877cc62a474002df32e52139f0a0',
    'a': 'FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC',
    'b': '28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93',
}


class CryptSM2(object):

    def __init__(self, private_key, public_key, ecc_table=default_ecc_table, mode=0, asn1=False):
        """
        mode: 0-C1C2C3, 1-C1C3C2 (default is 1)
        """
        self.private_key = private_key
        self.public_key = public_key[2:] if (public_key.startswith("04") and len(public_key)==130) else public_key
        self.para_len = len(ecc_table['n'])
        self.ecc_a3 = (
            int(ecc_table['a'], base=16) + 3) % int(ecc_table['p'], base=16)
        self.ecc_table = ecc_table
        assert mode in (0, 1), 'mode must be one of (0, 1)'
        self.mode = mode
        self.asn1 = asn1

    def _point_on_curve(self, point):
        x = int(point[0:self.para_len], 16)
        y = int(point[self.para_len:len(point)], 16)
        left = (y * y) % int(self.ecc_table['p'], base=16)
        right = (x * x * x) % int(self.ecc_table['p'], base=16)
        right = (right + int(self.ecc_table['a'], base=16) * x) %  int(self.ecc_table['p'], base=16)
        right = (right + int(self.ecc_table['b'], base=16)) % int(self.ecc_table['p'], base=16)
        return (left == right)

    def _double_point(self, Point):  # 倍点，对最常用函数进行优化，输入可以为仿射坐标，也可以为Jacobian坐标，输出为Jacobian坐标
        l = len(Point)
        len_2 = 2 * self.para_len
        if l < self.para_len * 2:
            return None
        else:
            x1 = int(Point[0:self.para_len], 16)
            y1 = int(Point[self.para_len:len_2], 16)
            if l == len_2:
                z1 = 1
            else:
                z1 = int(Point[len_2:], 16)

            T6 = (z1 * z1) % int(self.ecc_table['p'], base=16)
            T2 = (y1 * y1) % int(self.ecc_table['p'], base=16)
            T3 = (x1 + T6) % int(self.ecc_table['p'], base=16)
            T4 = (x1 - T6) % int(self.ecc_table['p'], base=16)
            T1 = (T3 * T4) % int(self.ecc_table['p'], base=16)
            T3 = (y1 * z1) % int(self.ecc_table['p'], base=16)
            T4 = (T2 * 8) % int(self.ecc_table['p'], base=16)
            T5 = (x1 * T4) % int(self.ecc_table['p'], base=16)
            T1 = (T1 * 3) % int(self.ecc_table['p'], base=16)
            T6 = (T6 * T6) % int(self.ecc_table['p'], base=16)
            T6 = (self.ecc_a3 * T6) % int(self.ecc_table['p'], base=16)
            T1 = (T1 + T6) % int(self.ecc_table['p'], base=16)
            z3 = (T3 + T3) % int(self.ecc_table['p'], base=16)
            T3 = (T1 * T1) % int(self.ecc_table['p'], base=16)
            T2 = (T2 * T4) % int(self.ecc_table['p'], base=16)
            x3 = (T3 - T5) % int(self.ecc_table['p'], base=16)

            if (T5 % 2) == 1:
                T4 = (T5 + ((T5 + int(self.ecc_table['p'], base=16)) >> 1) - T3) % int(
                    self.ecc_table['p'], base=16)
            else:
                T4 = (T5 + (T5 >> 1) - T3) % int(self.ecc_table['p'], base=16)

            T1 = (T1 * T4) % int(self.ecc_table['p'], base=16)
            y3 = (T1 - T2) % int(self.ecc_table['p'], base=16)

            form = '%%0%dx' % self.para_len
            form = form * 3
            return form % (x3, y3, z3)
        
    def _kg(self, k, Point):  # kP运算，输入输出均为仿射坐标
        Point = '%s%s' % (Point, '1')
        mask_str = '8'
        for i in range(self.para_len - 1):
            mask_str += '0'
        mask = int(mask_str, 16)
        Temp = Point
        flag = False
        for n in range(self.para_len * 4):
            if (flag):
                Temp = self._double_point(Temp)
            if (k & mask) != 0:
                if (flag):
                    Temp = self._add_point(Temp, Point)
                else:
                    flag = True
                    Temp = Point
            k = k << 1
        return self._convert_jacb_to_nor(Temp)

    def _add_point(self, P1, P2):  # 点加函数，P2点为仿射坐标即z=1，P1为Jacobian坐标，用于更好匹配kg函数
        len_2 = 2 * self.para_len
        l1 = len(P1)
        l2 = len(P2)
        if (l1 < len_2) or (l2 < len_2):
            return None
        else:
            X1 = int(P1[0:self.para_len], 16)
            Y1 = int(P1[self.para_len:len_2], 16)
            if (l1 == len_2):
                Z1 = 1
            else:
                Z1 = int(P1[len_2:], 16)
            x2 = int(P2[0:self.para_len], 16)
            y2 = int(P2[self.para_len:len_2], 16)

            T1 = (Z1 * Z1) % int(self.ecc_table['p'], base=16)
            T2 = (y2 * Z1) % int(self.ecc_table['p'], base=16)
            T3 = (x2 * T1) % int(self.ecc_table['p'], base=16)
            T1 = (T1 * T2) % int(self.ecc_table['p'], base=16)
            T2 = (T3 - X1) % int(self.ecc_table['p'], base=16)
            T3 = (T3 + X1) % int(self.ecc_table['p'], base=16)
            T4 = (T2 * T2) % int(self.ecc_table['p'], base=16)
            T1 = (T1 - Y1) % int(self.ecc_table['p'], base=16)
            Z3 = (Z1 * T2) % int(self.ecc_table['p'], base=16)
            T2 = (T2 * T4) % int(self.ecc_table['p'], base=16)
            T3 = (T3 * T4) % int(self.ecc_table['p'], base=16)
            T5 = (T1 * T1) % int(self.ecc_table['p'], base=16)
            T4 = (X1 * T4) % int(self.ecc_table['p'], base=16)
            X3 = (T5 - T3) % int(self.ecc_table['p'], base=16)
            T2 = (Y1 * T2) % int(self.ecc_table['p'], base=16)
            T3 = (T4 - X3) % int(self.ecc_table['p'], base=16)
            T1 = (T1 * T3) % int(self.ecc_table['p'], base=16)
            Y3 = (T1 - T2) % int(self.ecc_table['p'], base=16)

            form = '%%0%dx' % self.para_len
            form = form * 3
            return form % (X3, Y3, Z3)

    def _convert_jacb_to_nor(self, Point):  # Jacobian加重射影坐标转换成仿射坐标
        len_2 = 2 * self.para_len
        x = int(Point[0:self.para_len], 16)
        y = int(Point[self.para_len:len_2], 16)
        z = int(Point[len_2:], 16)
        z_inv = pow(
            z, int(self.ecc_table['p'], base=16) - 2, int(self.ecc_table['p'], base=16))
        z_invSquar = (z_inv * z_inv) % int(self.ecc_table['p'], base=16)
        z_invQube = (z_invSquar * z_inv) % int(self.ecc_table['p'], base=16)
        x_new = (x * z_invSquar) % int(self.ecc_table['p'], base=16)
        y_new = (y * z_invQube) % int(self.ecc_table['p'], base=16)
        z_new = (z * z_inv) % int(self.ecc_table['p'], base=16)
        if z_new == 1:
            form = '%%0%dx' % self.para_len
            form = form * 2
            return form % (x_new, y_new)
        else:
            return None

    def verify(self, Sign, data):
        # 验签函数，sign签名r||s，E消息hash，public_key公钥
        if self.asn1:
            unhex_sign = unhexlify(Sign.encode())
            seq_der = DerSequence()
            origin_sign = seq_der.decode(unhex_sign)
            r = origin_sign[0]
            s = origin_sign[1]
        else:
            r = int(Sign[0:self.para_len], 16)
            s = int(Sign[self.para_len:2*self.para_len], 16)
        e = int(data.hex(), 16)
        t = (r + s) % int(self.ecc_table['n'], base=16)
        if t == 0:
            return 0

        P1 = self._kg(s, self.ecc_table['g'])
        P2 = self._kg(t, self.public_key)
        # print(P1)
        # print(P2)
        if P1 == P2:
            P1 = '%s%s' % (P1, 1)
            P1 = self._double_point(P1)
        else:
            P1 = '%s%s' % (P1, 1)
            P1 = self._add_point(P1, P2)
            P1 = self._convert_jacb_to_nor(P1)

        x = int(P1[0:self.para_len], 16)
        return r == ((e + x) % int(self.ecc_table['n'], base=16))

    def sign(self, data, K):
        """
        签名函数, data消息的hash，private_key私钥，K随机数，均为16进制字符串
        :param self: 
        :param data: data消息的hash
        :param K: K随机数
        :return: 
        """
        E = data.hex()  # 消息转化为16进制字符串
        e = int(E, 16)

        d = int(self.private_key, 16)
        k = int(K, 16)

        P1 = self._kg(k, self.ecc_table['g'])

        x = int(P1[0:self.para_len], 16)
        R = ((e + x) % int(self.ecc_table['n'], base=16))
        if R == 0 or R + k == int(self.ecc_table['n'], base=16):
            return None
        d_1 = pow(
            d+1, int(self.ecc_table['n'], base=16) - 2, int(self.ecc_table['n'], base=16))
        S = (d_1*(k + R) - R) % int(self.ecc_table['n'], base=16)
        if S == 0:
            return None
        elif self.asn1:
            return DerSequence([DerInteger(R), DerInteger(S)]).encode().hex()
        else:
            return '%064x%064x' % (R, S)

    def encrypt(self, data):
        # 加密函数，data消息(bytes)
        msg = data.hex()  # 消息转化为16进制字符串
        k = func.random_hex(self.para_len)
        C1 = self._kg(int(k, 16), self.ecc_table['g'])
        xy = self._kg(int(k, 16), self.public_key)
        x2 = xy[0:self.para_len]
        y2 = xy[self.para_len:2*self.para_len]
        ml = len(msg)        
        # 使用gmssl库的KDF函数进行密钥派生
        t = sm3.sm3_kdf(xy.encode('utf8'), ml//2)
        if int(t, 16) == 0:
            return None
        else:
            form = '%%0%dx' % ml
            C2 = form % (int(msg, 16) ^ int(t, 16))           
            # 使用gmssl库的SM3哈希函数
            hash_input = bytes.fromhex('%s%s%s' % (x2, msg, y2))
            C3 = sm3.sm3_hash(list(hash_input))            
            if self.mode:
                return bytes.fromhex('%s%s%s' % (C1, C3, C2))
            else:
                return bytes.fromhex('%s%s%s' % (C1, C2, C3))

    def decrypt(self, data):
        # 解密函数，data密文（bytes）
        data = data.hex()
        len_2 = 2 * self.para_len
        len_3 = len_2 + 64
        C1 = data[0:len_2]
        if not self._point_on_curve(C1):
            return None

        if self.mode:
            C3 = data[len_2:len_3]
            C2 = data[len_3:]
        else:
            C2 = data[len_2:-64]
            C3 = data[-64:]

        xy = self._kg(int(self.private_key, 16), C1)
        # print('xy = %s' % xy)
        x2 = xy[0:self.para_len]
        y2 = xy[self.para_len:len_2]
        cl = len(C2)
        
        # 使用gmssl库的KDF函数进行密钥派生
        t = sm3.sm3_kdf(xy.encode('utf8'), cl//2)
        if int(t, 16) == 0:
            return None
        else:
            form = '%%0%dx' % cl
            M = form % (int(C2, 16) ^ int(t, 16))
            
            # 使用gmssl库的SM3哈希函数进行消息完整性校验
            hash_input = bytes.fromhex('%s%s%s' % (x2, M, y2))
            u = sm3.sm3_hash(list(hash_input))
            
            return bytes.fromhex(M)

    def _sm3_z(self, data):
        """
        SM3WITHSM2 签名规则:  SM2.sign(SM3(Z+MSG)，PrivateKey)
        其中: z = Hash256(Len(ID) + ID + a + b + xG + yG + xA + yA)
        """
        # sm3withsm2 的 z 值
        z = '0080'+'31323334353637383132333435363738' + \
            self.ecc_table['a'] + self.ecc_table['b'] + self.ecc_table['g'] + \
            self.public_key
        z = binascii.a2b_hex(z)    
        # 使用gmssl库计算SM3哈希得到Za值
        Za = sm3.sm3_hash(list(z))    
        M_ = (Za + data.hex()).encode('utf-8')        
        # 使用gmssl库计算最终的SM3哈希值
        e = sm3.sm3_hash(list(binascii.a2b_hex(M_)))        
        return e

    def sign_with_sm3(self, data, random_hex_str=None):
        sign_data = binascii.a2b_hex(self._sm3_z(data).encode('utf-8'))
        if random_hex_str is None:
            random_hex_str = func.random_hex(self.para_len)
        sign = self.sign(sign_data, random_hex_str)  # 16进制
        return sign

    def verify_with_sm3(self, sign, data):
        sign_data = binascii.a2b_hex(self._sm3_z(data).encode('utf-8'))
        return self.verify(sign, sign_data)

    def recover_public_keys(self, sign: str, data: bytes, v: int = None):
        """
        根据签名和被签数据的hash，还原签名者的公钥
        :param sign: 签名结果
        :param data: 被签数据(的hash)
        :param v: V in (R, S, V)
        :return: Set[签名者公钥]，长度为2(或4?)
        """
        r = int(sign[0:self.para_len], 16)
        s = int(sign[self.para_len:2 * self.para_len], 16)
        if len(sign) > 2 * self.para_len:
            # 65-byte signature, with the last byte as v
            v = int(sign[2 * self.para_len:2 * self.para_len + 2], 16)
        n = int(self.ecc_table['n'], base=16)
        p = int(self.ecc_table['p'], base=16)
        
        e = int(data.hex(), 16)
        # x1 = (r - e) mod n if restrict x1 in [1, n-1]
        x = (r - e) % n
        # g = x1^3 + a*x1 + b (mod p)
        factor1 = (x * x) % p
        factor1 = (factor1 * x) % p
        factor2 = (x * int(self.ecc_table['a'], base=16)) % p
        g = (factor1 + factor2) % p
        g = (g + int(self.ecc_table['b'], base=16)) % p
        # U = (P - 3)/4 + 1;
        u = (p - 3) // 4 + 1
        # y1 = g^u (mod p)
        y = func.exp_mod(g, u, p)
        # y1^2 = g (mod p) 验证
        if ((y * y) % p != g):
            raise ValueError('y*y == g (mod p) 验证失败')
        results = set()
        # 关于v，一般来说v只会有27或者28两种情况，标志着奇偶性
        # TODO: v in (29, 30)? For magnitude of x greater than the curve order
        for v in (v, ) if v else (27, 28):
            v -= 27
            if (y & 1 != v):
                y = p - y
            # 计算 g = -(s + r)^-1 (mod n)
            g = (s + r) % n
            g = n - func.inv_mod(g, n)
            # 计算Q= -Q = (x, -y)
            y = p - y
            form = '%%0%dx' % self.para_len
            form = form * 3
            Q = form % (x, y, 1)
            # 计算s*G
            P = self._kg(s, self.ecc_table['g'])
            # -Q+s*G
            P = self._add_point(Q, P)
            # 雅各比坐标转仿射坐标
            P = self._convert_jacb_to_nor(P)
            # 计算点乘
            P = self._kg(g, P)
            results.add(P)
        return results
    
    def test_k_reuse_attack(self, M1: bytes, M2: bytes):
        """
        测试 K 值重用攻击，演示如何通过两个使用相同 K 签名的消息来推导出私钥。
        :param M1: 第一条消息 (bytes)
        :param M2: 第二条消息 (bytes)，与 M1 使用相同的 K 进行签名
        :return: 推导出的私钥 (hex string)，如果攻击失败则返回 None
        """
        print("\n--- 启动 K 值重用攻击测试 ---")

        # 1. 模拟签名者使用相同的 K 签署两条不同的消息
        # 为了演示目的，我们手动指定一个 K 值。在实际攻击中，攻击者不会知道 K。
        # 这里的 K 是为了让你能复现这个场景。
        # 在真实攻击中，攻击者需要通过侧信道等方式推测或获取 k，或仅仅是观察到两次签名的 R 值相同（强烈提示 k 可能相同）。
        # 这里我们直接设置一个 K 来简化 PoC 的复现。
        reused_k_hex = func.random_hex(self.para_len) # 模拟一个被重用的 K
        print(f"模拟重用的随机数 K: {reused_k_hex}")

        # 计算 Z_A
        z_A = binascii.a2b_hex(self._sm3_z(b'dummy_data_for_za_calc').encode('utf-8')) # 这里用一个dummy data来获取Za，因为Z_A的计算不依赖具体消息

        # 对 M1 进行签名
        # 注意：这里调用_sm3_z是为了获取正确的消息哈希e
        e1_bytes = binascii.a2b_hex(self._sm3_z(M1).encode('utf-8'))
        e1 = int(e1_bytes.hex(), 16) # Ensure e1 is integer
        sign1_raw = self.sign(e1_bytes, reused_k_hex) # 使用相同的 K 签名 M1
        if sign1_raw is None:
            print("M1 签名失败，可能 R 或 S 为 0。请重试或调整 K。")
            return None
        
        # 解析签名1
        if self.asn1:
            unhex_sign1 = unhexlify(sign1_raw.encode())
            seq_der1 = DerSequence()
            origin_sign1 = seq_der1.decode(unhex_sign1)
            r1 = origin_sign1[0]
            s1 = origin_sign1[1]
        else:
            r1 = int(sign1_raw[0:self.para_len], 16)
            s1 = int(sign1_raw[self.para_len:2*self.para_len], 16)

        print(f"消息 M1: {M1.hex()}")
        print(f"M1 的签名 (r1, s1): ({hex(r1)}, {hex(s1)})")

        # 对 M2 进行签名
        e2_bytes = binascii.a2b_hex(self._sm3_z(M2).encode('utf-8'))
        e2 = int(e2_bytes.hex(), 16) # Ensure e2 is integer
        sign2_raw = self.sign(e2_bytes, reused_k_hex) # **再次使用相同的 K 签名 M2**
        if sign2_raw is None:
            print("M2 签名失败，可能 R 或 S 为 0。请重试或调整 K。")
            return None
        
        # 解析签名2
        if self.asn1:
            unhex_sign2 = unhexlify(sign2_raw.encode())
            seq_der2 = DerSequence()
            origin_sign2 = seq_der2.decode(unhex_sign2)
            r2 = origin_sign2[0]
            s2 = origin_sign2[1]
        else:
            r2 = int(sign2_raw[0:self.para_len], 16)
            s2 = int(sign2_raw[self.para_len:2*self.para_len], 16)

        print(f"消息 M2: {M2.hex()}")
        print(f"M2 的签名 (r2, s2): ({hex(r2)}, {hex(s2)})")

        # 2. 攻击者利用两个签名进行反推
        # 核心公式 (推导过程已在之前的Markdown文档中给出):
        # d_A = (s1 - s2) * (s2 + r2 - s1 - r1)^-1 mod n

        n = int(self.ecc_table['n'], base=16)

        # 计算 (s2 + r2 - s1 - r1) mod n
        # 注意 Python 的 % 运算符对于负数的结果：-5 % 7 = 2
        # 所以我们需要确保结果为正数
        denominator = (s2 + r2 - s1 - r1) % n
        if denominator < 0: # 确保结果在 [0, n-1] 范围内
            denominator += n

        # 检查分母是否为 0，如果是，则无法求逆，攻击失败
        if denominator == 0:
            print("攻击失败：分母 (s2 + r2 - s1 - r1) 为 0，无法求逆。")
            return None

        # 求 (s2 + r2 - s1 - r1) 在模 n 意义下的逆元
        try:
            inv_denominator = pow(denominator, n - 2, n) # 费马小定理求模逆 (n为素数时)
        except ValueError: # 如果 n 不是素数，或 denominator 与 n 不互素
            print("攻击失败：分母与 n 不互素，无法求模逆。")
            return None

        # 计算 (s1 - s2) mod n
        numerator = (s1 - s2) % n
        if numerator < 0:
            numerator += n

        # 计算推导出的私钥 d_A_cracked
        d_A_cracked = (numerator * inv_denominator) % n

        print(f"\n推导出的私钥 d_A_cracked: {hex(d_A_cracked)}")
        print(f"原始私钥 d_A (用于验证): {self.private_key}")

        # 3. 验证推导出的私钥是否正确
        if d_A_cracked == int(self.private_key, 16):
            print("!!! K 值重用攻击成功：推导出的私钥与原始私钥一致 !!!")
            return hex(d_A_cracked)
        else:
            print("K 值重用攻击失败：推导出的私钥与原始私钥不一致。")
            return None
    
