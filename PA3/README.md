# PA3
Simple OSPF network orchestrator using FRR.
Written by Tim Lawrence for CS4480, Spring 2025.

**Orchestrator file: Timothy_Lawrence_u1311540.py** \
**Demo recording: [YouTube](https://youtu.be/q6LIRDfVKQQ)**

## Options

- **`-h, --help`** \
*Print a help message and exit.*

- **`-c, --construct`** \
*Construct the network topology.* \
Creates Docker containers for two hosts (ha and hb) and four routers (r1-r4). ha and hb are connected to r1 and r3, respectively, while r2 ("north") and r4 ("south") both connect to r1 and r3.

- **`-d, --daemon`** \
*Start and configure the OSPF daemons.* \
Configures the OSPF daemons on all routers, defining relationships between themselves and the hosts, and then starts/restarts the FRR service.

- **`-r, --route`** \
*Set host routing.* \
Routes traffic from ha to hb (and vice versa) through the router network. Waits for OSPF convergence before continuing.

- **`-p, --path PATH`** \
*Set the preferred network traffic path (default = 'north').* \
Sets the preferred path for all network traffic, either through the 'north' (r2) or the 'south' (r4). *See `--construct`*.

- **`-q, --quit`** \
*Shut down and deconstruct the network.* \
Shuts down all Docker containers and cleans up related networks.

## Example arguments
- To set up the network from scratch: `-cdr`
- To adjust the traffic path: `-p 'north'` or `-p 'south'`
- To shut down the network: `-q`