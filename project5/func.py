from random import choice

list_to_bytes = lambda data: b''.join([bytes((i,)) for i in data])

bytes_to_list = lambda data: [i for i in data]

random_hex = lambda x: ''.join([choice('0123456789abcdef') for _ in range(x)])


def exp_mod(x: int, e: int, p: int) -> int:
    """
    x ** e (mod p)
    :param x:
    :param e:
    :param p:
    :return:
    """
    r = 1
    while e > 0:
        if e & 1 == 1:
            r = (r * x) % p
        x = (x * x) % p
        e >>= 1
    return r


def inv_mod(x: int, p: int) -> int:
    """
    x ^ -1 (mod p)
    :param x:
    :param p:
    :return:
    """
    return exp_mod(x, p - 2, p)