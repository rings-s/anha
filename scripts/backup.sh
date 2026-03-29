#!/bin/bash
# ============================================
# ANHA Trading - Database Backup Script
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_CONTAINER="anha-db"
DB_USER="${POSTGRES_USER:-anha_user}"
DB_NAME="${POSTGRES_DB:-anha_db}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/anha_db_$TIMESTAMP.sql.gz"

echo -e "${GREEN}[INFO]${NC} Starting database backup..."
echo -e "${GREEN}[INFO]${NC} Backup file: $BACKUP_FILE"

# Perform backup
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo -e "${GREEN}[✓]${NC} Backup completed successfully"
    ls -lh "$BACKUP_FILE"
else
    echo -e "${RED}[✗]${NC} Backup failed"
    exit 1
fi

# Clean up old backups
echo -e "${YELLOW}[INFO]${NC} Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "anha_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo -e "${GREEN}[INFO]${NC} Current backups:"
ls -lh "$BACKUP_DIR"
