#!/usr/bin/env python3

# Simple OSPF network orchestrator using FRRouting
# Written by Tim Lawrence for CS4480, Spring 2025

import argparse
import os, subprocess
import time

def parse_args() -> argparse.Namespace | None:
    '''Parse command line arguments. If no arguments are provided,
    prints the help message and returns `None`.'''
    parser = argparse.ArgumentParser(description='Simple OSPF network orchestrator using FRRouting')
    parser.add_argument('-c', '--construct', help='construct the network topology',
                       action='store_true')
    parser.add_argument('-d', '--daemon', help='start and config OSPF daemon',
                       action='store_true')
    parser.add_argument('-r', '--route', help='set host routing',
                       action='store_true')
    parser.add_argument('-p', '--path', help='set the preferred network traffic path',
                       choices=('north', 'south'))
    parser.add_argument('-q', '--quit', help='shut down and deconstruct the network',
                        action='store_true')
    
    args = parser.parse_args()
    if not any(vars(args).values()): # If no option, print help message
        parser.print_help()
        return None
    return args

def construct_network():
    '''Constructs the network topology using Docker containers.'''
    print('ORCH: Constructing network')
    
    os.system('docker compose up -d')
    
def start_ospf_daemon():
    '''Starts the OSPF daemon and sets configurations for each router.'''
    print('ORCH: Starting OSPF daemons')
    
    for i in range(1, 5):
        os.system(f'docker exec -it r{i} ./startdaemon.sh')
        
def set_host_routes():
    '''Sets routing for attached hosts.'''
    print('ORCH: Installing host routing')
    
    for i in 'ab':
        os.system(f'docker exec -it h{i} ./installroute.sh')
    
    print('ORCH: Waiting for route between hosts', end='')
    while True:
        result = subprocess.run(
            'docker exec -it r1 vtysh -c \'show ip route\'',
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if '10.0.15.0' in result.stdout:
            print('.done')
            break
        else:
            print('.', end='', flush=True)
            time.sleep(1)
        
def set_preferred_path(path: str):
    '''Sets the preferred path for network traffic.'''
    print(f'ORCH: Moving traffic to {path} path')
    
    if path == 'north': cost = 10
    elif path == 'south': cost = 1
    for i in (1, 3):
        os.system(f'docker exec -it r{i} vtysh -c \'configure terminal\' ' +
                  f'-c \'interface eth2\' -c\'ip ospf cost {cost}\' -c \'end\'')
        
def close_network():
    '''Shuts down the network and cleans up the docker setup.'''
    print('ORCH: Shutting down the network')
    
    os.system('docker compose down')

def main():
    args = parse_args()
    if args is None: return
    
    if args.construct: construct_network()
    if args.daemon: start_ospf_daemon()
    if args.route: set_host_routes()
    if args.path: set_preferred_path(args.path)
    if args.quit: close_network()

if __name__ == '__main__':
    main()