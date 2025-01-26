# Place your imports here
import signal
from optparse import OptionParser
import sys
from socket import *
import logging
from enum import Enum
import re

# Signal handler for pressing ctrl-c
def ctrl_c_pressed(signal, frame):
    sys.exit(0)

class ParseError(Enum):
    NOTIMPL = 1
    BADREQ = 2

def receive_request(client_skt: socket) -> bytes:
    request: bytes = b''
    # TODO: recv loop
    request = client_skt.recv(2048)
    logging.info(request)
    return request

def parse_request(message: bytes) -> tuple[ParseError, bytes, int, bytes, dict[bytes, bytes]]:
    host, port, path, headers = None, None, None, None

    logging.debug('start parse')
    try:
        message_tokens = message.split(maxsplit=3)
        assert len(message_tokens) >= 3
        logging.debug('correct length')

        method = message_tokens[0]
        assert method in [b'GET', b'HEAD', b'OPTIONS', b'TRACE', b'PUT', b'DELETE', b'POST', b'PATCH', b'CONNECT']
        if method != b'GET':
            return ParseError.NOTIMPL, None, None, None, None
        logging.debug('correct method')
        
        url = message_tokens[1]
        url_match = re.fullmatch(rb"http:\/\/([^:]+?)(?::(\d+)|)(/.*)", url)
        assert url_match
        host = url_match[1]
        port = int(url_match[2]) if url_match[2] else 80
        path = url_match[3]
        logging.debug(f"host: {host}")
        logging.debug(f"port: {port}")
        logging.debug(f"path: {path}")
        logging.debug('correct url')

        assert message_tokens[2] == b'HTTP/1.0'
        logging.debug('correct protocol')

        headers = {}
        if len(message_tokens) == 4: # Additional headers exist
            message_headers = message_tokens[-1].split(b'\r\n')
            for mh in message_headers:
                if not mh: break
                assert re.match(rb'\S+: .+', mh)
                mh_split = mh.split(b': ', maxsplit=1)
                mh_key, mh_value = (i.strip() for i in mh_split)
                headers[mh_key] = mh_value
                logging.debug(f'added kvpair {mh_key}: {mh_value}')
        logging.debug(f'correct headers: {headers}')

    except AssertionError:
        logging.debug('fail parse')
        return ParseError.BADREQ, None, None, None, None
    else:
        logging.debug('end parse')
        return None, host, port, path, headers

def send_to_server(host: bytes, port: int, path: bytes, headers: dict) -> bytes:
    with socket(AF_INET, SOCK_STREAM) as server_skt:
        server_skt.connect((host, port))
        
        header_str = f"GET http://{host.decode()}{path.decode()} HTTP/1.0\r\nConnection: close\r\n"
        for headkey, headval in headers.items():
            header_str += f"{headkey}: {headval}\r\n"
        header_str += "\r\n"
        logging.debug(header_str)
        server_skt.send(header_str.encode())

        response = server_skt.recv(2048)
        logging.info(response)
        return response
    
def send_client_response(client_skt: socket, response: bytes):
    client_skt.send(response)
    client_skt.close()

def send_client_error(client_skt: socket, errormsg: str):
    error_header = f"HTTP/1.0 {errormsg}\r\n\r\n"
    client_skt.send(error_header.encode())
    client_skt.close()

# Start of program execution
def main():
    # Parse out the command line server address and port number to listen to
    parser = OptionParser()
    parser.add_option('-p', type='int', dest='serverPort')
    parser.add_option('-a', type='string', dest='serverAddress')
    (options, args) = parser.parse_args()

    port = options.serverPort
    address = options.serverAddress
    if address is None:
        address = 'localhost'
    if port is None:
        port = 2100

    # Set up signal handling (ctrl-c)
    signal.signal(signal.SIGINT, ctrl_c_pressed)

    # TODO: Set up sockets to receive requests
    listener_skt = socket(AF_INET, SOCK_STREAM)
    listener_skt.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # Make the autograder behave
    listener_skt.bind((address, port))
    listener_skt.listen()

    while True:
        client_skt, client_address = listener_skt.accept()
        message = receive_request(client_skt)
        error, host, port, path, headers = parse_request(message)
        if not error:
            response = send_to_server(host, port, path, headers)
            send_client_response(client_skt, response)
        elif error == ParseError.BADREQ:
            send_client_error(client_skt, "400 Bad Request")
        elif error == ParseError.NOTIMPL:
            logging.debug("NOTIMPL")
            send_client_error(client_skt, "501 Not Implemented")

# Set logging level
logging.basicConfig(level=logging.DEBUG)        
if __name__ == '__main__':
    main()