#!/usr/bin/env python3

import simple_request

simple_request.send(b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n') # Server hangs because final \r\n not sent