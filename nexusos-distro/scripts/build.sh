#!/bin/bash
# NexusOS Linux Build Script
# Builds a minimal Arch-based Linux distro with NexusOS pre-installed

set -e

# Configuration
DISTRO_NAME="NexusOS"
VERSION="1.0.0"
ARCH="x86_64"
OUTPUT_DIR="/data/.openclaw/workspace/nexusos-distro/output"
WORK_DIR="/tmp/nexusos-build"

echo "=== Building $DISTRO_NAME Linux $VERSION ==="

# Clean previous build
rm -rf "$WORK_DIR" "$OUTPUT_DIR"
mkdir -p "$WORK_DIR" "$OUTPUT_DIR"

# Install build dependencies if needed
if ! command -v pacman &> /dev/null; then
    echo "This script must be run on Arch Linux or with pacman available"
    exit 1
fi

# Install build dependencies
echo "Installing build dependencies..."
sudo pacman -Sy --noconfirm archiso

# Create the build directory
echo "Creating build environment..."
mkdir -p "$WORK_DIR/nexusos-iso"
cd "$WORK_DIR"

# Clone or use current archiso profile
sudo cp -r /usr/share/archiso/configs/releng/* "$WORK_DIR/nexusos-iso/"

# Modify the build configuration
cat > "$WORK_DIR/nexusos-iso/airootfs/etc/os-release" << 'EOF'
NAME="NexusOS Linux"
VERSION="1.0.0"
ID=nexusos
ID_LIKE=arch
PRETTY_NAME="NexusOS Linux 1.0.0"
VERSION_ID="1.0.0"
EOF

# Add NexusOS packages to packages.x86_64
cat > "$WORK_DIR/nexusos-iso/packages.x86_64" << 'EOF'
# Core
base
base-devel
linux
linux-firmware

# Networking
openssh
ufw
iptables
nftables
NetworkManager

# Docker & Container
docker
docker-compose
podman

# Development
python
python-pip
nodejs
npm

# System
systemd
systemd-sysv
cronie

# Utilities
curl
wget
git
vim
htop
btop
rsync

# Security
audit
fail2ban
clamav
EOF

# Add NexusOS-specific configuration
mkdir -p "$WORK_DIR/nexusos-iso/airootfs/etc/nexusos"

# Copy the NexusOS application
echo "Copying NexusOS application..."
cp -r /data/.openclaw/workspace/nexusos-v2 "$WORK_DIR/nexusos-iso/airootfs/opt/nexusos/" 2>/dev/null || true
cp -r /data/.openclaw/workspace/nexusos-gui "$WORK_DIR/nexusos-iso/airootfs/opt/nexusos/" 2>/dev/null || true

# Create systemd service for NexusOS
cat > "$WORK_DIR/nexusos-iso/airootfs/etc/systemd/system/nexusos.service" << 'EOF'
[Unit]
Description=NexusOS Agent Platform
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/nexusos/start.sh
ExecStop=/opt/nexusos/stop.sh

[Install]
WantedBy=multi-user.target
EOF

# Create start/stop scripts
cat > "$WORK_DIR/nexusos-iso/airootfs/opt/nexusos/start.sh" << 'EOF'
#!/bin/bash
cd /opt/nexusos
docker-compose up -d
systemctl enable nexusos-api
EOF

cat > "$WORK_DIR/nexusos-iso/airootfs/opt/nexusos/stop.sh" << 'EOF'
#!/bin/bash
cd /opt/nexusos
docker-compose down
EOF

chmod +x "$WORK_DIR/nexusos-iso/airootfs/opt/nexusos/"*.sh

# Build the ISO
echo "Building ISO (this may take a while)..."
cd "$WORK_DIR/nexusos-iso"
sudo mkarchiso -v -w "$WORK_DIR/iso-work" -o "$OUTPUT_DIR" .

echo "=== Build Complete ==="
echo "ISO location: $OUTPUT_DIR/nexusos-$VERSION-$ARCH.iso"
ls -lh "$OUTPUT_DIR/"
