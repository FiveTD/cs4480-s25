#!/bin/bash

HOSTNAME=$(hostname)
if [ "$HOSTNAME" = "ha" ]; then
    route add -net 10.0.15.0/24 gw 10.0.14.4
elif [ "$HOSTNAME" = "hb" ]; then
    route add -net 10.0.14.0/24 gw 10.0.15.4
fi