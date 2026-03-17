#!/bin/bash
# NexusOS Linux Build Script - Docker-based
# Builds a Debian-based Linux system with NexusOS pre-installed
# Works on any platform with Docker (Linux, macOS, Windows)

set -e

DISTRO_NAME="NexusOS"
VERSION="1.0.0"
ARCH="amd64"
OUTPUT_DIR="/data/.openclaw/workspace/nexusos-distro/output"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

mkdir -p "$OUTPUT_DIR"

echo "=== Building $DISTRO_NAME Linux $VERSION (Debian via Docker) ==="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker."
    exit 1
fi

# Use a Debian container to build the system
echo "Building in Docker container..."

docker run --rm \
    -v "$OUTPUT_DIR:/output" \
    -v "$PROJECT_DIR:/source" \
    debian:bookworm-slim /bin/bash << 'EOF'
set -e

echo "=== Starting build in Debian container ==="

# Install build tools
apt-get update
apt-get install -y --no-install-recommends \
    debootstrap \
    xorriso \
    squashfs-tools \
    gzip \
    tar \
    curl \
    wget \
    git \
    vim \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    docker.io \
    docker-compose \
    ufw \
    iptables \
    cron \
    htop \
    rsync \
    ca-certificates \
    gnupg

# Create build directory
mkdir -p /build/chroot
WORK_DIR="/build"

# Build minimal Debian base
echo "Installing Debian base..."
debootstrap --variant=minbase --include=curl,wget,git,vim,gnupg \
    bookworm "$WORK_DIR/chroot" http://deb.debian.org/debian

# Configure OS
echo "Configuring OS..."
cat > "$WORK_DIR/chroot/etc/os-release" << 'OS'
NAME="NexusOS Linux"
VERSION="1.0.0"
ID=nexusos
ID_LIKE=debian
PRETTY_NAME="NexusOS Linux 1.0.0"
VERSION_ID="1.0.0"
OS

# Install packages
echo "Installing packages..."
chroot "$WORK_DIR/chroot" /bin/bash -c '
apt-get update
apt-get install -y --no-install-recommends \
    linux-image-amd64 \
    systemd \
    systemd-sysv \
    openssh-server \
    curl \
    wget \
    git \
    vim \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    docker.io \
    docker-compose \
    ufw \
    iptables \
    cron \
    htop \
    rsync \
    ca-certificates
'

# Copy NexusOS
echo "Copying NexusOS..."
mkdir -p "$WORK_DIR/chroot/opt/nexusos"
cp -r /source/nexusos-v2 "$WORK_DIR/chroot/opt/nexusos/" 2>/dev/null || true
cp -r /source/nexusos-gui "$WORK_DIR/chroot/opt/nexusos/" 2>/dev/null || true

# Create systemd service
mkdir -p "$WORK_DIR/chroot/etc/systemd/system"
cat > "$WORK_DIR/chroot/etc/systemd/system/nexusos.service" << 'SVC'
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
SVC

# Create scripts
cat > "$WORK_DIR/chroot/opt/nexusos/start.sh" << 'START'
#!/bin/bash
cd /opt/nexusos
docker-compose up -d
systemctl enable nexusos
START

cat > "$WORK_DIR/chroot/opt/nexusos/stop.sh" << 'STOP'
#!/bin/bash
cd /opt/nexusos
docker-compose down
STOP

chmod +x "$WORK_DIR/chroot/opt/nexusos/"*.sh

# Configure SSH
mkdir -p "$WORK_DIR/chroot/etc/ssh/sshd_config.d"
cat > "$WORK_DIR/chroot/etc/ssh/sshd_config.d/nexusos.conf" << 'SSH'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
SSH

# Create output
echo "Creating output..."

# Tar.gz (importable by Docker)
cd "$WORK_DIR"
tar -czf /output/nexusos-$VERSION-$ARCH.tar.gz -C chroot .

# Create Docker image
echo "Building Docker image..."
cat > /tmp/Dockerfile.nexusos << 'DF'
FROM scratch
COPY nexusos-1.0.0-amd64.tar.gz /
CMD ["/bin/bash"]
DF

cd "$WORK_DIR"
docker build -f /tmp/Dockerfile.nexusos -t nexusos:base .

# Save Docker image
docker save nexusos:base -o /output/nexusos-docker-image.tar

echo "=== Build Complete ==="
ls -lh /output/

EOF

echo ""
echo "=== Build Results ==="
ls -lh "$OUTPUT_DIR/"
