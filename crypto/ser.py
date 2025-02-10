import socket

# Permutation tables and S-boxes
P10 = [3, 5, 2, 7, 4, 10, 1, 9, 8, 6]
P8 = [6, 3, 7, 4, 8, 5, 10, 9]
IP = [2, 6, 3, 1, 4, 8, 5, 7]
IP_INV = [4, 1, 3, 5, 7, 2, 8, 6]
EP = [4, 1, 2, 3, 2, 3, 4, 1]
P4 = [2, 4, 3, 1]

S0 = [
    [1, 0, 3, 2],
    [3, 2, 1, 0],
    [0, 2, 1, 3],
    [3, 1, 3, 2],]

S1 = [
    [0, 1, 2, 3],
    [2, 0, 1, 3],
    [3, 0, 1, 0],
    [2, 1, 0, 3],]

# Utility functions
def permute(bits, table):
    return [bits[i - 1] for i in table]

def shift_left(bits, shifts):
    return bits[shifts:] + bits[:shifts]

def xor(bits1, bits2):
    return [b1 ^ b2 for b1, b2 in zip(bits1, bits2)]

def sbox_lookup(sbox, row, col):
    return format(sbox[row][col], '02b')

# Key generation
def generate_keys(key):
    key = [int(b) for b in key]
    p10 = permute(key, P10)
    left, right = p10[:5], p10[5:]
    left, right = shift_left(left, 1), shift_left(right, 1)
    k1 = permute(left + right, P8)
    left, right = shift_left(left, 2), shift_left(right, 2)
    k2 = permute(left + right, P8)
    return k1, k2

# Feistel function
def feistel(right, subkey):
    expanded = permute(right, EP)
    xored = xor(expanded, subkey)
    left, right = xored[:4], xored[4:]
    row1, col1 = int(str(left[0]) + str(left[3]), 2), int(str(left[1]) + str(left[2]), 2)
    row2, col2 = int(str(right[0]) + str(right[3]), 2), int(str(right[1]) + str(right[2]), 2)
    sbox_result = sbox_lookup(S0, row1, col1) + sbox_lookup(S1, row2, col2)
    return permute([int(b) for b in sbox_result], P4)

# Encryption and decryption
def sdes_encrypt_decrypt(bits, key, mode):
    k1, k2 = generate_keys(key)
    if mode == "DECRYPT":
        k1, k2 = k2, k1
    bits = [int(b) for b in bits]
    permuted = permute(bits, IP)
    left, right = permuted[:4], permuted[4:]
    left = xor(left, feistel(right, k1))
    left, right = right, left
    left = xor(left, feistel(right, k2))
    result = permute(left + right, IP_INV)
    return ''.join(map(str, result))

# Server setup
server = socket.socket()
server.bind(('localhost', 12345))
server.listen(1)

print("S-DES Server started. Waiting for client...")
while True:
    conn, addr = server.accept()
    print(f"Connected to {addr}")
    data = conn.recv(1024).decode().split(',')
    mode, plaintext, key = data[0], data[1], data[2]
    result = sdes_encrypt_decrypt(plaintext, key, mode)
    conn.send(result.encode())
    conn.close()

