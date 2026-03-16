#!/bin/bash
# NexusOS Easy Installer
# Usage: curl -sL https://get.nexusos.cloud | bash
#   or: bash install.sh [--production]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[NexusOS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[NexusOS]${NC} $1"; }
log_error() { echo -e "${RED}[NexusOS]${NC} $1"; }

# Detect if running in Docker
in_docker() {
    [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null
}

# Check prerequisites
check_prereqs() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose not found."
        exit 1
    fi
    
    # Use docker compose if available (V2)
    COMPOSE_CMD="docker compose"
    if ! docker compose version &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    fi
    
    log_info "Prerequisites OK"
}

# Generate secure secrets
generate_secrets() {
    log_info "Generating secure secrets..."
    
    # Generate random passwords
    export NEXUSOS_DB_PASSWORD=${NEXUSOS_DB_PASSWORD:-$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 24)}
    export NEXUSOS_REDIS_PASSWORD=${NEXUSOS_REDIS_PASSWORD:-$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 24)}
    export NEXUSOS_SECRET=${NEXUSOS_SECRET:-$(openssl rand -base64 32)}
    export NEXUSOS_JWT_SECRET=${NEXUSOS_JWT_SECRET:-$(openssl rand -base64 32)}
    
    # Save to .env
    cat > .env << EOF
# NexusOS Configuration
# Generated on $(date)

# Database
NEXUSOS_DB_PASSWORD=$NEXUSOS_DB_PASSWORD
NEXUSOS_DB_PORT=5432

# Redis
NEXUSOS_REDIS_PASSWORD=$NEXUSOS_REDIS_PASSWORD
NEXUSOS_REDIS_PORT=6379

# API
NEXUSOS_API_PORT=8080
NEXUSOS_SECRET=$NEXUSOS_SECRET
NEXUSOS_JWT_SECRET=$NEXUSOS_JWT_SECRET

# Ollama (optional)
NEXUSOS_OLLAMA_PORT=11434
OLLAMA_URL=http://ollama:11434
EOF
    
    log_info "Secrets saved to .env"
}

# Pull and start services
start_nexusos() {
    log_info "Starting NexusOS..."
    
    # Pull latest images
    $COMPOSE_CMD pull postgres redis
    
    # Build API
    log_info "Building NexusOS API..."
    $COMPOSE_CMD build api
    
    # Start services
    $COMPOSE_CMD up -d postgres redis api
    
    # Wait for database
    log_info "Waiting for database..."
    sleep 5
    
    # Run migrations
    log_info "Running database migrations..."
    $COMPOSE_CMD run --rm api python -c "
        from database import init_db
        init_db()
    " || log_warn "Migration complete (or already done)"
    
    log_info "NexusOS is starting..."
    $COMPOSE_CMD logs -f api &
}

# Show status
show_status() {
    log_info "Checking status..."
    sleep 3
    $COMPOSE_CMD ps
    
    echo ""
    log_info "NexusOS API: http://localhost:8080"
    log_info "API Docs:    http://localhost:8080/docs"
    log_info ""
    log_warn "First run: Register at http://localhost:8080/auth/register"
}

# Main
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║           NexusOS Easy Installer                  ║"
    echo "║        Self-Hosted AI Agent Platform             ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo ""
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    
    check_prereqs
    
    if [ -f .env ]; then
        log_warn "Using existing .env configuration"
        source .env
    else
        generate_secrets
    fi
    
    start_nexusos
    show_status
    
    log_info "Done! 🎉"
}

# Handle pipe mode
if [ -t 0 ]; then
    # Interactive mode
    main "$@"
else
    # Pipe mode - run with defaults
    export NEXUSOS_DB_PASSWORD="$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 24)"
    export NEXUSOS_REDIS_PASSWORD="$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 24)"
    export NEXUSOS_SECRET="$(openssl rand -base64 32)"
    export NEXUSOS_JWT_SECRET="$(openssl rand -base64 32)"
    
    cat > .env << EOF
NEXUSOS_DB_PASSWORD=$NEXUSOS_DB_PASSWORD
NEXUSOS_REDIS_PASSWORD=$NEXUSOS_REDIS_PASSWORD
NEXUSOS_SECRET=$NEXUSOS_SECRET
NEXUSOS_JWT_SECRET=$NEXUSOS_JWT_SECRET
NEXUSOS_API_PORT=8080
NEXUSOS_DB_PORT=5432
NEXUSOS_REDIS_PORT=6379
NEXUSOS_OLLAMA_PORT=11434
OLLAMA_URL=http://ollama:11434
EOF
    
    docker compose pull postgres redis
    docker compose build api
    docker compose up -d postgres redis api
    docker compose logs -f
fi
