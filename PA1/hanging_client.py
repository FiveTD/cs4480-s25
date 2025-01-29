from socket import *

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('localhost', 2100))
sock.sendall(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n') # Server hangs because final \r\n not sent

# never runs
print(sock.makefile('rb').read())