#!/bin/bash
# ============================================
# ANHA Trading - Database Restore Script
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

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}[INFO]${NC} Available backups:"
    ls -lh "$BACKUP_DIR"
    echo ""
    echo "Usage: $0 <backup-file>"
    echo "Example: $0 anha_db_20240115_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    # Try with backup directory prefix
    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        echo -e "${RED}[ERROR]${NC} Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

echo -e "${YELLOW}[WARNING]${NC} This will restore the database from: $BACKUP_FILE"
echo -e "${YELLOW}[WARNING]${NC} Current database will be overwritten!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${GREEN}[INFO]${NC} Restore cancelled"
    exit 0
fi

echo -e "${GREEN}[INFO]${NC} Restoring database..."

# Stop the app to prevent writes during restore
docker-compose -f docker-compose.prod.yml stop app

# Restore the database
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip < "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"
else
    docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME" < "$BACKUP_FILE"
fi

# Restart the app
docker-compose -f docker-compose.prod.yml start app

echo -e "${GREEN}[✓]${NC} Database restored successfully"
