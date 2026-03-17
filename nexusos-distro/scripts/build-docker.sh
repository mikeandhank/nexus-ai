#!/bin/bash
# Simple Docker-based NexusOS Build
# Builds a minimal container with everything pre-installed

set -e

OUTPUT_DIR="/data/.openclaw/workspace/nexusos-distro/output"
mkdir -p "$OUTPUT_DIR"

echo "=== Building NexusOS Docker Image ==="

# Build from Dockerfile
cd /data/.openclaw/workspace/nexusos-v2

# Create Dockerfile
cat > Dockerfile.nexusos << 'EOF'
FROM archlinux:latest

# Install packages
RUN pacman -Sy --noconfirm \
    python \
    python-pip \
    nodejs \
    npm \
    git \
    curl \
    wget \
    docker \
    docker-compose \
    openssh \
    ufw \
    && pacman -Scc --noconfirm

# Create nexusos user
RUN useradd -m -s /bin/bash nexusos

# Copy NexusOS application
COPY . /opt/nexusos/
WORKDIR /opt/nexusos

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Build GUI
WORKDIR /opt/nexusos/../nexusos-gui
RUN npm install && npm run build

# Return to NexusOS
WORKDIR /opt/nexusos

# Create startup script
RUN echo '#!/bin/bash\ndocker-compose up -d' > /start.sh && \
    echo '#!/bin/bash\ndocker-compose down' > /stop.sh && \
    chmod +x /start.sh /stop.sh

# Expose ports
EXPOSE 8080 3000 5432 6379

# Start command
CMD ["/start.sh"]
EOF

# Build the image
echo "Building Docker image..."
docker build -f Dockerfile.nexusos -t nexusos:latest .

# Save as tar
echo "Saving to tar..."
docker save nexusos:latest -o "$OUTPUT_DIR/nexusos-docker.tar"

# Also create a docker-compose.yml for the image
cat > "$OUTPUT_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  api:
    image: nexusos:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://nexusos:nexusos@postgres:5432/nexusos
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - postgres
      - redis
      - ollama

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: nexusos
      POSTGRES_PASSWORD: nexusos
      POSTGRES_DB: nexusos
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama

volumes:
  postgres-data:
  ollama-data:
EOF

echo "=== Build Complete ==="
ls -lh "$OUTPUT_DIR/"
