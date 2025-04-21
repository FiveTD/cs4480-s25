#!/bin/bash

HOSTNAME=$(hostname)

# Configure default route
if [ "$HOSTNAME" = "ha" ]; then
    ip route replace default via 10.0.14.4
elif [ "$HOSTNAME" = "hb" ]; then
    ip route replace default via 10.0.15.4
fi

# Keep container running
bash