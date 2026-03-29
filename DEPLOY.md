# ============================================
# ANHA Trading - Production Deployment Guide
# For Hostinger VPS
# ============================================

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [VPS Setup](#vps-setup)
3. [Initial Deployment](#initial-deployment)
4. [SSL Certificate Setup](#ssl-certificate-setup)
5. [Maintenance](#maintenance)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hostinger VPS Requirements
- **OS**: Ubuntu 22.04 LTS (recommended) or 20.04 LTS
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: Minimum 20GB SSD
- **Ports**: 80, 443 must be open
- **Domain**: Point your domain to VPS IP address

### Software Requirements
- Docker 24.0+
- Docker Compose 2.20+
- Git

---

## VPS Setup

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Docker
```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository:
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker:
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group:
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Install Additional Tools
```bash
sudo apt install -y git curl ncdu htop ufw fail2ban
```

### 4. Configure Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Initial Deployment

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/anha-trading.git
cd anha-trading
```

### 2. Configure Environment
```bash
# Copy production environment template
cp .env.production .env.production.local

# Edit with your values
nano .env.production.local
```

**Important: Update these values in .env.production.local:**
- `BASE_URL`: Your domain (e.g., https://your-domain.com)
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `POSTGRES_PASSWORD`: Strong random password
- `SMTP_USER`, `SMTP_PASSWORD`: Your Hostinger email credentials

### 3. Make Scripts Executable
```bash
chmod +x scripts/*.sh
```

### 4. Deploy (Without SSL - Initial)
```bash
# For first deployment without SSL
# Edit nginx/conf.d/default.conf and comment out SSL lines if needed
./scripts/deploy.sh
```

### 5. Verify Deployment
```bash
# Check containers are running
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Test locally
curl http://localhost/health
```

---

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended - Free)

```bash
# Run the SSL setup script
./scripts/setup-ssl.sh your-domain.com your-email@example.com

# Example:
./scripts/setup-ssl.sh app.yourdomain.com admin@yourdomain.com
```

This will:
1. Obtain SSL certificate from Let's Encrypt
2. Configure Nginx for HTTPS
3. Auto-renew certificates

### Option 2: Hostinger SSL (If purchased)

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Upload your Hostinger SSL certificates:
# - certificate.crt -> nginx/ssl/fullchain.pem
# - private.key -> nginx/ssl/privkey.pem
# - ca_bundle.crt -> nginx/ssl/chain.pem

# Set permissions
chmod 600 nginx/ssl/privkey.pem
chmod 644 nginx/ssl/fullchain.pem
chmod 644 nginx/ssl/chain.pem

# Restart Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## Maintenance

### Daily Operations

**View logs:**
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f app
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f db
```

**Check status:**
```bash
docker-compose -f docker-compose.prod.yml ps
docker stats
```

### Backup Database

**Manual backup:**
```bash
./scripts/backup.sh
```

**Automatic backups:** (Already configured by deploy.sh)
- Daily at system cron time
- Stored in `./backups/`
- 7-day retention

### Update Application

```bash
# Pull latest code and redeploy
./scripts/update.sh
```

### Database Maintenance

```bash
# Connect to database
docker exec -it anha-db psql -U anha_user -d anha_db

# Vacuum database
docker exec anha-db psql -U anha_user -d anha_db -c "VACUUM ANALYZE;"
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs --tail=100 [service-name]

# Check for port conflicts
sudo netstat -tlnp | grep -E '80|443|8000|5432'

# Restart service
docker-compose -f docker-compose.prod.yml restart [service-name]
```

### Database Connection Issues

```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Check logs
docker-compose -f docker-compose.prod.yml logs db

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec app env | grep DATABASE
```

### SSL Certificate Issues

```bash
# Renew certificate manually
docker run -it --rm \
  -v "$(pwd)/nginx/certbot-data:/etc/letsencrypt" \
  -v "$(pwd)/nginx/www/certbot:/var/www/certbot" \
  -p 80:80 \
  certbot/certbot renew --force-renewal

# Test Nginx config
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### High Memory Usage

```bash
# Check memory usage
docker stats --no-stream

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Prune unused images
docker system prune -a
```

### Reset Everything (⚠️ DANGER - Data Loss)

```bash
# Stop all containers
docker-compose -f docker-compose.prod.yml down

# Remove volumes (DELETES ALL DATA)
docker-compose -f docker-compose.prod.yml down -v

# Remove all images
docker system prune -a --volumes

# Redeploy
./scripts/deploy.sh
```

---

## Security Checklist

- [ ] Changed default `SECRET_KEY` in `.env.production.local`
- [ ] Changed default `POSTGRES_PASSWORD`
- [ ] Enabled firewall (UFW)
- [ ] SSL certificate installed
- [ ] Regular backups configured
- [ ] Fail2ban installed and running
- [ ] Docker containers running as non-root
- [ ] No sensitive data in code repository
- [ ] Environment file not tracked in git
- [ ] Database not exposed to internet

---

## Useful Commands Reference

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart service
docker-compose -f docker-compose.prod.yml restart [service]

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Access container shell
docker-compose -f docker-compose.prod.yml exec [service] sh

# Database backup
./scripts/backup.sh

# Database restore
./scripts/restore.sh backups/anha_db_20240115_120000.sql.gz
```

---

## Support

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Check this troubleshooting guide
3. Contact Hostinger support for VPS issues
4. Open an issue in the project repository
