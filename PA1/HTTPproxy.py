#!/usr/bin/env python3

# Simple HTTP proxy server
# Written by Tim Lawrence for CS4480, last updated 02-15-2025
# Additional code provided by class resources

import signal
from optparse import OptionParser
import sys
from socket import *
import logging
from enum import Enum
import re
import threading
from wsgiref.handlers import format_date_time
import time

MAX_THREADS: int = 100

responseCache: dict[bytes, bytes] = dict()
cacheEnabled: bool = False

requestBlocklist: set[bytes] = set()
blocklistEnabled: bool = False

def ctrl_c_pressed(signal, frame):
    '''Signal handler for pressing ctrl-c'''
    sys.exit(0)

class ParseError(Enum):
    NOTIMPL = "501 Not Implemented"
    BADREQ = "400 Bad Request"
    FORBID = "403 Forbidden"

def receive_request(client_skt: socket) -> bytes:
    '''Receives a complete HTTP request from ``client_skt``.'''
    request: bytes = b''
    while b'\r\n\r\n' not in request:
        request += client_skt.recv(2048)
    return request

def parse_request(message: bytes) -> tuple[ParseError, bytes, int, bytes, dict[bytes, bytes]]:
    '''Parses a received HTTP request and extracts host, port, path, and headers.
    Returns a ``ParseError`` if the request is malformed or can't be processed.'''
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
        # logging.debug("Parsed method")
        
        # Parse URL
        url = message_tokens[1]
        url_match = re.fullmatch(rb"http:\/\/([^:]+?)(?::(\d+)|)(/.*)", url)
        assert url_match
        host = url_match[1]
        port = int(url_match[2]) if url_match[2] else 80
        path = url_match[3]
        if host_blocked(host):
            return ParseError.FORBID, None, None, None, None
        # logging.debug("Parsed URL")

        # Check protocol
        assert message_tokens[2] == b'HTTP/1.0'
        # logging.debug("Parsed protocol")

        # Parse headers
        headers = {}
        if len(message_tokens) == 4: # Additional headers exist
            # logging.debug("Detected headers")
            message_headers = message_tokens[-1].split(b'\r\n')
            for header_line in message_headers:
                if not header_line: break # ignore trailing empty string
                assert re.match(rb'\S+: .+', header_line)
                mh_key, mh_value = (i.strip() for i in header_line.split(b': ', maxsplit=1))
                headers[mh_key] = mh_value
        # logging.debug("Parsed headers")

    except AssertionError:
        return ParseError.BADREQ, None, None, None, None
    else:
        return None, host, port, path, headers
    
def parse_settings(path: bytes) -> bool:
    '''Parses proxy settings request from the request path.
    Returns ``True`` if settings were modified.'''
    global cacheEnabled, blocklistEnabled
    
    if path == b'/proxy/cache/enable': cacheEnabled = True
    elif path == b'/proxy/cache/disable': cacheEnabled = False
    elif path == b'/proxy/cache/flush': responseCache.clear()
    elif path == b'/proxy/blocklist/enable': blocklistEnabled = True
    elif path == b'/proxy/blocklist/disable': blocklistEnabled = False
    elif path == b'/proxy/blocklist/flush': requestBlocklist.clear()
    elif path.startswith(b'/proxy/blocklist/add/'): 
        blockedHost = path.removeprefix(b'/proxy/blocklist/add/')
        add_to_blocklist(blockedHost)
    elif path.startswith(b'/proxy/blocklist/remove/'):
        blockedHost = path.removeprefix(b'/proxy/blocklist/remove/')
        remove_from_blocklist(blockedHost)
    else: return False
    logging.info(f"Settings updated: {path.decode()}")
    return True

def request_server(host: bytes, port: int, path: bytes, headers: dict[bytes, bytes]) -> bytes:
    '''Fetches the requested resource from the server.
    If caching is enabled, reads from and updates cache appropriately.'''
    # Construct headers
    headers[b'Host'] = host
    headers[b'Connection'] = b'close'
    if cached_obj := fetch_from_cache(host, port, path):
        headers[b'If-Modified-Since'] = get_modified_date()
    
    # Construct GET header string
    header_str = f"GET {path.decode()} HTTP/1.0\r\n"
    for headkey, headval in headers.items():
        header_str += f"{headkey.decode()}: {headval.decode()}\r\n"
    header_str += "\r\n"
    # logging.debug(header_str)
    
    # Connect to server and receive response
    with socket(AF_INET, SOCK_STREAM) as server_skt:
        try:
            server_skt.connect((host, port))
        except:
            logging.info(f"Unable to connect to {host.decode()}:{port}")
            return status_code_response(ParseError.BADREQ.value)
        server_skt.send(header_str.encode())

        response = b''
        while chunk := server_skt.recv(2048): # Returns None on connection close and breaks loop
            response += chunk
    
    # Consult cache
    if cacheEnabled:
        responseCode = response.split(b' ')[1]
        logging.debug(f"Response code: {responseCode.decode()}")
        if responseCode == b'304': return cached_obj
        elif responseCode == b'200': add_to_cache(host, port, path, response)
    return response

def send_client_response(client_skt: socket, response: bytes) -> None:
    '''Sends a server response back to the client and closes the connection.'''
    client_skt.send(response)
    client_skt.close()

def status_code_response(responseMsg: str) -> None:
    '''Constructs a client response with the provided response code and message.'''
    return f"HTTP/1.0 {responseMsg}\r\n\r\n".encode()

def get_cache_key(host: bytes, port: int, path: bytes) -> bytes:
    return host + b':' + bytes(port) + path

def get_modified_date() -> bytes:
    '''Gets the current time as HTTP-date
    ([RFC 1945, 3.3](https://www.rfc-editor.org/rfc/rfc1945#section-3.3)).'''
    return format_date_time(time.time()).encode()

def fetch_from_cache(host: bytes, port: int, path: bytes) -> bytes | None:
    '''If the resource is cached and caching is enabled, returns the cached resource. If not, returns ``None``.'''
    if not cacheEnabled: return None
    logging.debug(f"Fetching from cache")
    key = get_cache_key(host, port, path)
    return responseCache.get(key, None)

def add_to_cache(host: bytes, port: int, path: bytes, obj: bytes) -> None:
    '''Caches the resouce at ``host``:``port``/``path``.'''
    logging.info(f"Adding {host.decode()}:{port}{path.decode()} to cache")
    key = get_cache_key(host, port, path)
    responseCache[key] = obj
    
def add_to_blocklist(host: bytes) -> None:
    '''Adds ``host`` to the blocklist.'''
    logging.info(f"Adding {host.decode()} to blocklist")
    host = host.split(b':')[0] # Remove port from host if present
    requestBlocklist.add(host)
    
def remove_from_blocklist(host: bytes) -> None:
    '''Removes ``host`` from the blocklist.'''
    logging.debug(f"Removing {host.decode()} from blocklist")
    requestBlocklist.remove(host)
    
def host_blocked(host: bytes) -> bool:
    '''Checks if ``host`` is currently blocked.'''
    if not blocklistEnabled: return False
    for blockedHost in requestBlocklist:
        if blockedHost in host: return True
    return False

def handle_client(client_skt: socket) -> None:
    '''Manages a request from a single client.'''
    message = receive_request(client_skt)
    error, host, port, path, headers = parse_request(message)
    if not error:
        if parse_settings(path):
            response = status_code_response("200 OK")
        else:
            response = request_server(host, port, path, headers)
    else:
        response = status_code_response(error.value)
    send_client_response(client_skt, response)

def main():
    # Parse out the command line server address and port number to listen to
    parser = OptionParser()
    parser.add_option('-p', type='int', dest='serverPort')
    parser.add_option('-a', type='string', dest='serverAddress')
    parser.add_option('-l', type='string', dest='loggingLevel')
    (options, args) = parser.parse_args()

    # Set logging level
    loggingLevel: str = options.loggingLevel
    if loggingLevel is None: loggingLevel = 'ERROR'
    loggingLevel = loggingLevel.lower()
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
            send_client_response(client_skt, status_code_response("503 Service Unavailable"))
        
        logging.info(f"Accepted client {client_skt.getsockname()}")
        client_thread = threading.Thread(target=handle_client, args=[client_skt])
        client_thread.start()
       
if __name__ == '__main__':
    main()