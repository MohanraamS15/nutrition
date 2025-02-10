import socket

client = socket.socket()
client.connect(('localhost', 12345))

mode = input("Enter mode (ENCRYPT/DECRYPT): ").strip().upper()
plaintext = input("Enter 8-bit binary text: ").strip()
key = input("Enter 10-bit binary key: ").strip()

client.send(f"{mode},{plaintext},{key}".encode())

result = client.recv(1024).decode()
print(f"{mode}ED Text:", result)

client.close()
