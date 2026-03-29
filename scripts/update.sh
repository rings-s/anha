#!/bin/bash
# ============================================
# ANHA Trading - Update Script
# Pull latest code and redeploy
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_header "ANHA Trading - Update"

# Check if git repo
if [ ! -d ".git" ]; then
    print_error "Not a git repository. Please use deploy.sh instead."
    exit 1
fi

# 1. Backup database before update
print_info "Creating pre-update backup..."
./scripts/backup.sh || {
    print_warning "Backup failed, but continuing with update..."
}

# 2. Pull latest code
print_info "Pulling latest code from git..."
git pull origin main || {
    print_error "Failed to pull latest code"
    exit 1
}
print_status "Code updated"

# 3. Rebuild and restart
print_header "Rebuilding and restarting services..."

# Stop services gracefully
docker-compose -f docker-compose.prod.yml stop app

# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Rebuild app
docker-compose -f docker-compose.prod.yml build --no-cache app

# Start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Clean up old images
print_info "Cleaning up old Docker images..."
docker image prune -f

# 5. Check health
print_info "Checking service health..."
sleep 10

if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
    print_status "All services are healthy"
else
    print_warning "Some services may not be healthy. Check logs:"
    docker-compose -f docker-compose.prod.yml logs --tail=50
fi

print_header "Update Complete!"
print_status "Your application has been updated to the latest version"
