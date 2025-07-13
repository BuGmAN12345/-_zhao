import hashlib
from sympy import randprime
import secrets
from Crypto.Util.number import GCD
import random
from phe import paillier

class Func: # 基础函数类
    p = None  # 大素数

    @classmethod
    def _generate_large_random_prime_sympy(cls,bits): #随机生成bit位的大素数
        lower_bound = 2**(bits - 1)
        upper_bound = 2**bits - 1
        return randprime(lower_bound, upper_bound)
    
    @classmethod
    def setup(cls, bits=1024):  # 设置大素数
        cls.p = cls._generate_large_random_prime_sympy(bits)

    def exp_mod(self,x, e): # x ** e (mod p)
        r = 1
        while e > 0:
            if e & 1 == 1:
                r = (r * x) % self.p
            x = (x * x) % self.p
            e >>= 1
        return r

    def generate_private_key(self): #生成k1,k2
        # 生成 [1, p-2] 范围内的随机数
        if self.p is None:
            raise ValueError("请先调用 Func.setup() 初始化大素数 p")
        while True:
            k = secrets.randbelow(self.p-1) + 1
            if k < self.p-1:  # 确保 k != p-1
                return k
    
    def hash_password(self,password): #str->int
        if self.p is None:
            raise ValueError("请先调用 Func.setup() 初始化大素数 p")
        sha256_hex=hashlib.sha256(password.encode()).hexdigest()
        return int(sha256_hex, 16)%self.p
    
    def hash_passwords(self,passwords): #set->list
        if self.p is None: 
            raise ValueError("请先调用 Func.setup() 初始化大素数 p")
        return [self.hash_password(password) for password in passwords]
    
    

class P1(Func):
    def __init__(self,password={"你好，我是你爹","你是谁？", "你是谁？我是谁？", "你是谁？我是谁？你是谁？", "你是谁？我是谁？你是谁？我是谁？"}):
        self.password = password
        self.k1= self.generate_private_key()

    def round1(self):
        hash_list= self.hash_passwords(self.password) #求H(wj)^k1
        hash_list = [self.exp_mod(i, self.k1) for i in hash_list]
        random.shuffle(hash_list)
        return hash_list
    
    def round2(self,Z, hash_list): #接受参数
        self.Z=Z
        self.hash_list=hash_list
    
    def round3(self):
        P2_pass = [(self.exp_mod(tup[0], self.k1),tup[1]) for tup in self.hash_list]  # 求(H(wj')^k1k2,Enc(tj'))
        sum=None
        for pair in P2_pass:
            if pair[0] in self.Z:
                if sum is None:
                    sum = pair[1]  # 初始化sum
                else:
                    sum += pair[1]
        return sum  # 返回sum

class P2(Func):
    def __init__(self,password={("你好，我是你娘",10),("你是谁？",50), ("你是谁？我是谁？",100),("你是我儿子吗？",160), ("你是谁？我是你娘？你是谁？我是你娘？",520)}):
        self.password = password
        self.k2= self.generate_private_key()
        self.pk,self.sk = paillier.generate_paillier_keypair()

    def round1(self, hash_list): #接受参数
        self.hash_list = hash_list

    def round2(self): #pk包含在密文对象中隐式传递
        Z=[self.exp_mod(i, self.k2) for i in self.hash_list]
        random.shuffle(Z)
        tmp = [(self.exp_mod(self.hash_password(tup[0]), self.k2),self.pk.encrypt(tup[1])) for tup in self.password] #获取(H(wj')^k2,Enc(tj'))
        random.shuffle(tmp)
        return set(Z), tmp
    
    def round3(self,sum): #接受参数
        if sum is None:
            return 0
        all_t=self.sk.decrypt(sum)  # 解密sum
        return all_t
    
def test_protocol():
    Func.setup()
    p1= P1()
    p2= P2()
    hash_list= p1.round1()  # P1的第一轮
    p2.round1(hash_list)  # P2的第一轮
    print("第一轮交互完成")
    Z, hash_list = p2.round2()  # P2的第二轮
    p1.round2(Z, hash_list)  # P1的第二轮
    print("第二轮交互完成")
    sum = p1.round3()  # P1的第三轮
    all_t = p2.round3(sum)  # P2的第三轮
    print("交互协议完成")
    return p1.password, p2.password, all_t  # 返回密码和总和

if __name__ == "__main__":
    passwd1,passwd2,output= test_protocol()
    print("passwd1为", passwd1, "\npasswd2为", passwd2, "\n输出为", output)

