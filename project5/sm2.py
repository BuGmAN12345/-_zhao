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
    
    def point_double(self, P):
        if P is None:  # 无穷远点的2倍还是无穷远点
            return None
        x1 = int(P[0:self.para_len], 16)
        y1 = int(P[self.para_len:len(P)], 16)
        # 如果 y1 = 0，则 2P = O (无穷远点)
        if y1 == 0:
            return None
        # 计算斜率 λ = (3x₁² + a) / (2y₁)
        numerator = (3 * x1 * x1 + int(self.ecc_table['a'], base=16)) % int(self.ecc_table['p'], base=16)
        denominator = (2 * y1) % int(self.ecc_table['p'], base=16)
        lambda_val = (numerator * func.inv_mod(denominator, int(self.ecc_table['p'], base=16))) % int(self.ecc_table['p'], base=16)
        # 计算新的坐标
        x3 = (lambda_val * lambda_val - 2 * x1) % int(self.ecc_table['p'], base=16)
        y3 = (lambda_val * (x1 - x3) - y1) % int(self.ecc_table['p'], base=16)
        form = '%%0%dx' % self.para_len
        form = form * 2
        return form % (x3, y3)

    def _add_point(self, P1, P2):
        if P1 is None:  # P是无穷远点
            return P2
        if P2 is None:  # Q是无穷远点
            return P1  
        x1 = int(P1[0:self.para_len], 16)
        y1 = int(P1[self.para_len:len(P1)], 16)
        x2 = int(P2[0:self.para_len], 16)
        y2 = int(P2[self.para_len:len(P2)], 16)
        if x1 == x2:
            if y1 == y2:
                # 点倍乘
                return self.point_double(P1)
            else:
                # P + (-P) = O (无穷远点)
                return None
        # 一般情况的点加法
        numerator = (y2 - y1) % int(self.ecc_table['p'], base=16)
        denominator = (x2 - x1) % int(self.ecc_table['p'], base=16)
        lambda_val = (numerator * func.inv_mod(denominator, int(self.ecc_table['p'], base=16))) % int(self.ecc_table['p'], base=16)
        x3 = (lambda_val * lambda_val - x1 - x2) % int(self.ecc_table['p'], base=16)
        y3 = (lambda_val * (x1 - x3) - y1) % int(self.ecc_table['p'], base=16)
        form = '%%0%dx' % self.para_len
        form = form * 2
        return form % (x3, y3)
    
    def _kg(self, k, P):
        if k == 0:
            return None  # 无穷远点
        if k == 1:
            return P
        result = P
        # 进行k-1次点加法
        for _ in range(k - 1):
            result = self._add_point(result, P)
        return result

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
            P1 = self.point_double(P1)
        else:
            P1 = self._add_point(P1, P2)
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
        C1_point = self._kg(int(k, 16), self.ecc_table['g'])
        C1 = '%064x%064x' % (C1_point[0], C1_point[1])  
        xy_point = self._kg(int(k, 16), self.public_key)
        xy = '%064x%064x' % (xy_point[0], xy_point[1])  
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
            C3 = sm3.sm3_hash(list(hash_input)) #校验码         
            if self.mode:
                return bytes.fromhex('%s%s%s' % (C1, C3, C2))
            else:
                return bytes.fromhex('%s%s%s' % (C1, C2, C3))

    def decrypt(self, data):
        data = data.hex()
        len_2 = 2 * self.para_len
        len_3 = len_2 + 64
        C1 = data[0:len_2]
        C1_x = int(C1[0:self.para_len], 16)
        C1_y = int(C1[self.para_len:len_2], 16)
        C1_point = (C1_x, C1_y)
        if not self._point_on_curve(C1_point):
            return None
        if self.mode:
            C3 = data[len_2:len_3]
            C2 = data[len_3:]
        else:
            C2 = data[len_2:-64]
            C3 = data[-64:]

        # [d_B]C1，_kg需要仿射坐标点作为输入，返回仿射坐标点
        xy_point = self._kg(int(self.private_key, 16), C1_point)
        xy = '%064x%064x' % (xy_point[0], xy_point[1])  # 转换为十六进制字符串
        
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
    
