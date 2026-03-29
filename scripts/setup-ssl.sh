#!/bin/bash
# ============================================
# ANHA Trading - SSL Certificate Setup Script
# For Hostinger VPS Deployment
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-your-domain.com}"
EMAIL="${2:-your-email@example.com}"
NGINX_CERT_DIR="./nginx/ssl"
CERTBOT_DIR="./nginx/certbot-data"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if domain is provided
if [ "$DOMAIN" = "your-domain.com" ]; then
    print_error "Please provide your domain as the first argument"
    echo "Usage: $0 your-domain.com your-email@example.com"
    exit 1
fi

if [ "$EMAIL" = "your-email@example.com" ]; then
    print_warning "Using default email. Please provide your email as the second argument"
    echo "Usage: $0 your-domain.com your-email@example.com"
fi

print_status "Setting up SSL certificates for $DOMAIN"

# Create necessary directories
mkdir -p $NGINX_CERT_DIR
mkdir -p ./nginx/www/certbot

# Stop existing containers if running
print_status "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Start nginx with temporary HTTP-only configuration for certbot
print_status "Starting Nginx for initial setup..."
docker-compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
sleep 5

# Generate SSL certificate
print_status "Generating SSL certificate with Let's Encrypt..."
docker run -it --rm \
    -v "$(pwd)/nginx/certbot-data:/etc/letsencrypt" \
    -v "$(pwd)/nginx/www/certbot:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --preferred-challenges http \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN" \
    --non-interactive \
    || {
        print_error "Failed to generate SSL certificate"
        print_warning "Make sure your domain is pointing to this server and port 80 is open"
        exit 1
    }

# Copy certificates to nginx ssl directory
print_status "Copying certificates to nginx directory..."
mkdir -p $NGINX_CERT_DIR

# Create symbolic links or copy files
if [ -f "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" ]; then
    cp "$CERTBOT_DIR/live/$DOMAIN/fullchain.pem" "$NGINX_CERT_DIR/fullchain.pem"
    cp "$CERTBOT_DIR/live/$DOMAIN/privkey.pem" "$NGINX_CERT_DIR/privkey.pem"
    cp "$CERTBOT_DIR/live/$DOMAIN/chain.pem" "$NGINX_CERT_DIR/chain.pem"
    print_status "Certificates copied successfully"
else
    print_error "Certificates not found in expected location"
    exit 1
fi

# Set proper permissions
chmod 644 "$NGINX_CERT_DIR/fullchain.pem"
chmod 600 "$NGINX_CERT_DIR/privkey.pem"
chmod 644 "$NGINX_CERT_DIR/chain.pem"

print_status "SSL certificates setup complete!"
print_status "Certificates location: $NGINX_CERT_DIR"
print_status "You can now start the full stack with: docker-compose -f docker-compose.prod.yml up -d"

# Test nginx configuration
print_status "Testing Nginx configuration..."
docker-compose -f docker-compose.prod.yml exec nginx nginx -t || {
    print_error "Nginx configuration test failed"
    exit 1
}

print_status "SSL setup complete! Your site should now be accessible via HTTPS"
