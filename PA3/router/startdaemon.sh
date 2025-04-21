#!/bin/bash

# Get config file
HOSTNAME=$(hostname)
if [ -f "/etc/frr/config/${HOSTNAME}.conf" ]; then
    cp /etc/frr/config/${HOSTNAME}.conf /etc/frr/frr.conf
    chown frr:frr /etc/frr/frr.conf
fi

# Start OSPF daemon
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
service frr restart