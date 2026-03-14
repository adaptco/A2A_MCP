# Qube Runtime Kernel

## Overview

The **Qube Runtime** is a minimal, edge-optimized execution environment for Token Pixel Agents.
It enables deterministic execution of agent state transitions based on a hash-anchored stream of "Token Pixels".

## Components

- **TokenPixel**: The atomic unit of input, containing a timestamp, sequence ID, hash chain, and payload.
- **QubeRuntime**: The kernel that initializes, executes pixels, and maintains the audit log.
- **QubeMain**: A standalone entry point to run the kernel.

## Build

The Qube Runtime is integrated into the `ghost-void` Makefile.
To build:

```bash
make qube
```

The binary will be output to `bin/qube_kernel`.

## Usage

Currently, `QubeMain` runs a hardcoded simulation.
To extend, pipe standard input to the binary formatted as TokenPixels (implementation pending serialization).
