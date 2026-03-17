# NexusOS Linux - Custom Distro

A minimal Debian-based Linux distribution with NexusOS agent platform pre-installed.

## Why Debian?

- **Stable** - Enterprise-tested, battle-hardened
- **Familiar** - Most widely recognized Linux distro
- **Mature** - Great driver support, extensive repos
- **Size** - Minimal install ~800MB, full ~2GB

## Quick Start

### Option 1: Docker Image (Easiest)
```bash
# Load the pre-built image
docker load -i nexusos-docker.tar

# Or use docker-compose
docker-compose up -d
```

### Option 2: Build from Source

**Debian-based (Recommended):**
```bash
# Build minimal Debian image with NexusOS
sudo ./scripts/build-debian.sh

# Output: nexusos-1.0.0-amd64.tar.gz
```

**Docker build (works on any Linux):**
```bash
./scripts/build-docker.sh
```

**GUI build:**
```bash
./scripts/build-gui.sh
```

## What's Included

### Core (Debian Base)
- Debian 12 (Bookworm)
- Linux kernel (latest)
- Python 3.x + pip
- Node.js + npm
- Docker + Docker Compose

### NexusOS Platform
- Agent Kernel (`kernel.py`)
- Agent Executor with Inner Life
- Persistent Memory (PostgreSQL)
- Tool Engine (32+ tools)
- Semantic Recall
- Smart Planning
- ReAct prompting

### GUI
- Web Dashboard
- Agent Management UI

### Security
- UFW Firewall (enabled)
- SSH hardening (no root, key-only)
- Fail2ban (installed)
- Audit logging

## System Requirements

- 4GB RAM minimum
- 20GB disk
- x86_64/amd64 architecture
- UEFI boot

## Usage

### From tar.gz:
```bash
# Extract to a partition or VM
sudo tar -xzf nexusos-1.0.0-amd64.tar.gz -C /target/

# Or run directly in a container
docker import nexusos-1.0.0-amd64.tar.gz nexusos:installed
```

### Post-Install (when deployed):
```bash
# Set up network
nmtui

# Enable firewall
ufw status

# Start NexusOS
systemctl start nexusos

# Access dashboard
http://localhost:8080
```

## Build Customization

Edit `scripts/build-debian.sh` to:
- Add/remove Debian packages
- Pre-configure settings
- Add your own applications
- Configure network defaults

## Project Structure

```
nexusos-distro/
├── README.md
└── scripts/
    ├── build-debian.sh   # Main build (Debian-based) ⭐
    ├── build-docker.sh   # Docker image
    └── build-gui.sh      # GUI build
```

## License

Proprietary - Nexus AI Inc.
