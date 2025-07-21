from sm2_opt import CryptSM2
from func import random_hex

def test_sm2():
    private_key = '00B9AB0B828FF68872F21A837FC303668428DEA11DCD1B24429D0C99E24EED83D5'
    public_key = 'B9C9A6E04E9C91F7BA880429273747D7EF5DDEB0BB2FF6317EB00BEF331A83081A6994B8993F3F5D6EADDDB81872266C87C018FB4162F5AF347B483E24620207'

    sm2_crypt = CryptSM2(
        public_key=public_key, private_key=private_key)
    data = b"111"
    print("before encrypt data:", data.decode())
    enc_data = sm2_crypt.encrypt(data)
    #print("enc_data:%s" % enc_data)
    #print("enc_data_base64:%s" % base64.b64encode(bytes.fromhex(enc_data)))
    dec_data = sm2_crypt.decrypt(enc_data)
    print("dec_data:" ,dec_data.decode())
    assert data == dec_data

    print("-----------------test sign and verify---------------")
    random_hex_str = random_hex(sm2_crypt.para_len)
    sign = sm2_crypt.sign(data, random_hex_str)
    print('sign:%s' % sign)
    verify = sm2_crypt.verify(sign, data)
    print('verify:%s' % verify)
    assert verify
    
    print("-----------------test recovering public key from signature and hashed data---------------")
    public_keys_recovered = sm2_crypt.recover_public_keys(sign, data)
    print(public_keys_recovered)
    assert public_key.lower() in public_keys_recovered

    print("-----------------test sign with same k---------------")
    message1 = b'This is the first message for testing K reuse.'
    message2 = b'This is the second message, different from the first.'

    # 运行 K 值重用攻击测试
    # test_k_reuse_attack 会在内部模拟使用相同的 K 进行两次签名，并尝试推导私钥。
    derived_private_key = sm2_crypt.test_k_reuse_attack(message1, message2)

    if derived_private_key:
        print(f"\n攻击成功！推导出的私钥为: {derived_private_key}")
    else:
        print("\n攻击失败或未能推导出私钥。")

if __name__ == '__main__':
    test_sm2()