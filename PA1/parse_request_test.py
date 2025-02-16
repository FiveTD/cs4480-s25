from HTTPproxy import parse_request, ParseError

notimplreq = (ParseError.NOTIMPL, None, None, None, None)
badreq = (ParseError.BADREQ, None, None, None, None)

requests = [
    # Just a kick the tires test
    (b'GET http://www.google.com/ HTTP/1.0\r\n\r\n', (None, b'www.google.com', 80, b'/', {})),
    # 102.2) Test handling of malformed request lines [0.5 points]
    (b'HEAD http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n', notimplreq),
    (b'POST http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n', notimplreq),
    (b'GIBBERISH http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n', badreq),
    # 102.3) Test handling of malformed header lines [0.5 points]
    (b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\nthis is not a header\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\nConnection : close\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\nConnection:close\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:50.0) Firefox/50.0\r\ngibberish\r\n\r\n', badreq),
    # 102.4) Test handling of malformed URIs [0.5 points]
    (b'GET www.flux.utah.edu/cs4480/simple.html HTTP/1.0\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu HTTP/1.0\r\n\r\n', badreq),
    (b'GET /cs4480/simple.html HTTP/1.0\r\n\r\n', badreq),
    (b'GET gibberish HTTP/1.0\r\n\r\n', badreq),
    # 102.5) Test handling of wrong HTTP versions
    (b'GET http://www.flux.utah.edu/cs4480/simple.html HTTP/1.1\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html 1.0\r\n\r\n', badreq),
    (b'GET http://www.flux.utah.edu/cs4480/simple.html gibberish\r\n\r\n', badreq),
    # 103.5) Requests should include the specified headers [0.5 points]
    (b'GET http://localhost:8080/simple.html HTTP/1.0\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:50.0) Firefox/50.0\r\n\r\n',
      (None, b'localhost', 8080, b'/simple.html', {b'Connection': b'close', b'User-Agent': b'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:50.0) Firefox/50.0'}))
]

for request, expected in requests:
    print(f"Testing {request}")
    parsed = parse_request(request)
    assert parsed == expected, f"{request} yielded {parsed} instead of {expected}"
print('All tests passed!')