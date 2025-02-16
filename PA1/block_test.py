#!/usr/bin/env python3

import simple_request

simple_request.send(b'GET http://localhost/proxy/blocklist/flush HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://localhost/proxy/blocklist/enable HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://localhost/proxy/blocklist/add/flux HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://localhost/proxy/blocklist/disable HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n')