# Simple HTTP proxy server
# Written by Tim Lawrence for CS4480
# Additional code provided by class resources

import signal
from optparse import OptionParser
import sys
from socket import *
import logging
from enum import Enum
import re
import threading

MAX_THREADS: int = 100

# Signal handler for pressing ctrl-c
def ctrl_c_pressed(signal, frame):
    sys.exit(0)

class ParseError(Enum):
    NOTIMPL = 1
    BADREQ = 2

def receive_request(client_skt: socket) -> bytes:
    '''Handles a client connection and receives an HTTP request.'''
    request: bytes = b''
    while b'\r\n\r\n' not in request:
        request += client_skt.recv(2048)
    return request

def parse_request(message: bytes) -> tuple[ParseError, bytes, int, bytes, dict[bytes, bytes]]:
    '''Parses a received HTTP request and extracts host, port, path, and headers.
    Returns a ParseError if the request is malformed or can't be processed.'''
    host, port, path, headers = None, None, None, None

    try:
        # Parse header into basic tokens
        message_tokens = message.split(maxsplit=3)
        assert len(message_tokens) >= 3

        # Check method
        method = message_tokens[0]
        assert method in [b'GET', b'HEAD', b'OPTIONS', b'TRACE', b'PUT', b'DELETE', b'POST', b'PATCH', b'CONNECT']
        if method != b'GET':
            return ParseError.NOTIMPL, None, None, None, None
        
        # Parse URL
        url = message_tokens[1]
        url_match = re.fullmatch(rb"http:\/\/([^:]+?)(?::(\d+)|)(/.*)", url)
        assert url_match
        host = url_match[1]
        port = int(url_match[2]) if url_match[2] else 80
        path = url_match[3]

        # Check protocol
        assert message_tokens[2] == b'HTTP/1.0'

        # Parse headers
        headers = {}
        if len(message_tokens) == 4: # Additional headers exist
            message_headers = message_tokens[-1].split(b'\r\n')
            for header_line in message_headers:
                if not header_line: break # ignore trailing empty string
                assert re.match(rb'\S+: .+', header_line)
                mh_key, mh_value = (i.strip() for i in header_line.split(b': ', maxsplit=1))
                headers[mh_key] = mh_value

    except AssertionError:
        return ParseError.BADREQ, None, None, None, None
    else:
        return None, host, port, path, headers

def request_server(host: bytes, port: int, path: bytes, headers: dict) -> bytes:
    '''Reconstructs and passes an HTTP request to the intended host.
    Closes connection after receipt.'''
    with socket(AF_INET, SOCK_STREAM) as server_skt:
        server_skt.connect((host, port))
        
        header_str = f"GET {path.decode()} HTTP/1.0\r\n"
        headers[b'Host'] = host
        headers[b'Connection'] = b'close' # Override or add connection info to header
        for headkey, headval in headers.items():
            header_str += f"{headkey.decode()}: {headval.decode()}\r\n"
        header_str += "\r\n"
        logging.debug(header_str)
        logging.debug(header_str.encode())
        server_skt.send(header_str.encode())

        response = b''
        while chunk := server_skt.recv(2048): # Returns None on connection close and breaks loop
            response += chunk
        return response
    
def send_client_response(client_skt: socket, response: bytes):
    '''Sends a server response back to the client and closes the connection.'''
    client_skt.send(response)
    client_skt.close()

def send_client_error(client_skt: socket, errormsg: str):
    '''Sends an error to the client if their request could not be processed.'''
    logging.info(f"Error on client {client_skt.getsockname()}: {errormsg}")
    error_header = f"HTTP/1.0 {errormsg}\r\n\r\n"
    client_skt.send(error_header.encode())
    client_skt.close()

def handle_client(client_skt: socket):
    message = receive_request(client_skt)
    error, host, port, path, headers = parse_request(message)
    if not error:
        response = request_server(host, port, path, headers)
        send_client_response(client_skt, response)
    elif error == ParseError.BADREQ:
        send_client_error(client_skt, "400 Bad Request")
    elif error == ParseError.NOTIMPL:
        send_client_error(client_skt, "501 Not Implemented")

# Start of program execution
def main():
    # Parse out the command line server address and port number to listen to
    parser = OptionParser()
    parser.add_option('-p', type='int', dest='serverPort')
    parser.add_option('-a', type='string', dest='serverAddress')
    parser.add_option('-l', type='string', dest='loggingLevel')
    (options, args) = parser.parse_args()

    # Set logging level 
    loggingLevel: str = options.loggingLevel.lower()
    if loggingLevel == 'info':
        logging.basicConfig(level=logging.INFO)
    elif loggingLevel == 'debug':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    port = options.serverPort
    address = options.serverAddress
    if address is None:
        address = 'localhost'
    if port is None:
        port = 2100

    # Set up signal handling (ctrl-c)
    signal.signal(signal.SIGINT, ctrl_c_pressed)

    # Set up socket to receive requests
    listener_skt = socket(AF_INET, SOCK_STREAM)
    listener_skt.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # Make the autograder behave
    listener_skt.bind((address, port))
    listener_skt.listen()
    logging.info("Accepting clients...")

    # Accept client sockets and handle requests
    while True:
        client_skt, client_address = listener_skt.accept()
        if threading.active_count() > MAX_THREADS:
            logging.info(f"Rejected client {client_skt.getsockname()}: too many threads")
            send_client_error(client_skt, "503 Service Unavailable")
        
        logging.info(f"Accepted client {client_skt.getsockname()}")
        client_thread = threading.Thread(target=handle_client, args=[client_skt])
        client_thread.start()
       
if __name__ == '__main__':
    main()