#!/usr/bin/env python3

from socket import *

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('www.flux.utah.edu', 80))
sock.sendall(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n')

print(sock.makefile('rb').read())