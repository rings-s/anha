#!/bin/bash
# ============================================
# ANHA Trading - Production Deployment Script
# For Hostinger VPS
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

# Check if .env file exists
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    print_info "Please create .env.production from .env.example"
    echo "  cp .env.example .env.production"
    echo "  nano .env.production  # Edit with your production values"
    exit 1
fi

print_header "ANHA Trading - Production Deployment"

# 1. System Requirements Check
print_info "Checking system requirements..."

# Check Docker
docker --version > /dev/null 2>&1 || {
    print_error "Docker is not installed. Please install Docker first."
    exit 1
}

# Check Docker Compose
docker-compose --version > /dev/null 2>&1 || {
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
}

print_status "Docker and Docker Compose are installed"

# Check if required ports are available
print_info "Checking port availability..."
for port in 80 443; do
    if ! nc -z localhost $port 2>/dev/null; then
        print_status "Port $port is available"
    else
        print_warning "Port $port might be in use"
    fi
done

# 2. Create necessary directories
print_info "Creating necessary directories..."
mkdir -p nginx/ssl
mkdir -p nginx/www/certbot
mkdir -p nginx/certbot-data
mkdir -p init-scripts
mkdir -p backups
print_status "Directories created"

# 3. Check SSL certificates
print_info "Checking SSL certificates..."
if [ ! -f "nginx/ssl/fullchain.pem" ] || [ ! -f "nginx/ssl/privkey.pem" ]; then
    print_warning "SSL certificates not found"
    print_info "Please run SSL setup first: ./scripts/setup-ssl.sh your-domain.com your-email@example.com"
    
    read -p "Do you want to continue without SSL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_status "SSL certificates found"
fi

# 4. Pull latest images and build
print_header "Building and pulling images..."
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml build --no-cache

# 5. Start services
print_header "Starting services..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.yml up -d

# 6. Wait for services to be healthy
print_info "Waiting for services to be healthy..."
sleep 10

# Check service health
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose -f docker-compose.prod.yml ps | grep -q "healthy"; then
        print_status "Services are healthy"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Services failed to become healthy"
    print_info "Check logs with: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi

# 7. Verify deployment
print_header "Verifying deployment..."

# Check if containers are running
RUNNING_CONTAINERS=$(docker-compose -f docker-compose.prod.yml ps -q | wc -l)
if [ "$RUNNING_CONTAINERS" -ge 3 ]; then
    print_status "All containers are running ($RUNNING_CONTAINERS containers)"
else
    print_error "Some containers are not running"
    docker-compose -f docker-compose.prod.yml ps
    exit 1
fi

# Check Nginx is responding
print_info "Testing Nginx endpoint..."
if curl -sf http://localhost/health > /dev/null 2>&1; then
    print_status "Nginx is responding"
else
    print_warning "Nginx health check not responding (this is OK if SSL is not set up)"
fi

# 8. Setup log rotation
print_info "Setting up log rotation..."
if [ ! -f "/etc/logrotate.d/anha-nginx" ]; then
    sudo tee /etc/logrotate.d/anha-nginx > /dev/null << EOF
/var/lib/docker/volumes/anha_nginx-logs/_data/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker kill --signal="USR1" anha-nginx 2>/dev/null || true
    endscript
}
EOF
    print_status "Log rotation configured"
else
    print_status "Log rotation already configured"
fi

# 9. Setup automated backups
print_info "Setting up automated backups..."
if [ ! -f "/etc/cron.daily/anha-backup" ]; then
    sudo tee /etc/cron.daily/anha-backup > /dev/null << 'EOF'
#!/bin/bash
# ANHA Trading Database Backup
BACKUP_DIR="/home/$(whoami)/anha/backups"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)
docker exec anha-db pg_dump -U anha_user anha_db | gzip > "$BACKUP_DIR/anha_db_$DATE.sql.gz"
find "$BACKUP_DIR" -name "anha_db_*.sql.gz" -mtime +7 -delete
EOF
    sudo chmod +x /etc/cron.daily/anha-backup
    print_status "Automated backups configured (daily at cron time)"
else
    print_status "Backup script already exists"
fi

print_header "Deployment Complete!"
echo ""
print_status "Your ANHA Trading application is now deployed!"
echo ""
print_info "Useful commands:"
echo "  View logs:       docker-compose -f docker-compose.prod.yml logs -f"
echo "  View status:     docker-compose -f docker-compose.prod.yml ps"
echo "  Restart:         docker-compose -f docker-compose.prod.yml restart"
echo "  Stop:            docker-compose -f docker-compose.prod.yml down"
echo "  Update:          ./scripts/deploy.sh"
echo ""
print_info "Your application should be accessible at:"
echo "  - HTTP:  http://your-domain.com"
echo "  - HTTPS: https://your-domain.com (if SSL is configured)"
echo ""
