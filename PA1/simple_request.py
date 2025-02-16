from socket import *

def send(msg: bytes):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect(('localhost', 2100))
    sock.sendall(msg)
    print(sock.makefile('rb').read())