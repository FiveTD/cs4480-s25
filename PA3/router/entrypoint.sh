#!/bin/bash

HOSTNAME=$(hostname)

if [ -f "/etc/frr/config/${HOSTNAME}.conf" ]; then
    cp /etc/frr/config/${HOSTNAME}.conf /etc/frr/frr.conf
    chown frr:frr /etc/frr/frr.conf
fi

service frr restart

bash