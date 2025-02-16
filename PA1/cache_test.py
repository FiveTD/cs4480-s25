#!/usr/bin/env python3

import simple_request

simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n') # Should not add to cache
simple_request.send(b'GET http://localhost:2100/proxy/cache/enable HTTP/1.0\r\n\r\n')
simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n') # Should not be cached
simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n') # Should be cached