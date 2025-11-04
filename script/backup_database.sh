#!/bin/bash
# MongoDB Backup Script for MaiMBot (mongodump - BSON format)
# Usage: ./backup_database.sh [output_directory]
# This script uses mongodump to create backups in the same format as mongodb_backup

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
DB_HOST="${MONGODB_HOST:-127.0.0.1}"
DB_PORT="${MONGODB_PORT:-27017}"
DB_NAME="${DATABASE_NAME:-MegBot}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${1:-backups/${TIMESTAMP}}"

echo "========================================"
echo "MaiMBot Database Backup (mongodump)"
echo "========================================"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Output: $BACKUP_DIR"
echo "Format: BSON (Binary JSON)"
echo "========================================"

# Check if mongodump is available
if ! command -v mongodump &> /dev/null; then
    echo "ERROR: mongodump not found!"
    echo ""
    echo "Please install MongoDB Database Tools:"
    echo "  https://www.mongodb.com/try/download/database-tools"
    echo ""
    echo "Or use the Python backup script instead:"
    echo "  python script/backup_database.py"
    exit 1
fi

# Check if authentication is needed
if [ ! -z "$MONGODB_USERNAME" ] && [ ! -z "$MONGODB_PASSWORD" ]; then
    AUTH_SOURCE="${MONGODB_AUTH_SOURCE:-admin}"
    echo "Using authentication (user: $MONGODB_USERNAME)"
    mongodump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$MONGODB_USERNAME" \
        --password="$MONGODB_PASSWORD" \
        --authenticationDatabase="$AUTH_SOURCE" \
        --db="$DB_NAME" \
        --out="$BACKUP_DIR"
elif [ ! -z "$MONGODB_URI" ]; then
    echo "Using MongoDB URI connection"
    mongodump \
        --uri="$MONGODB_URI" \
        --out="$BACKUP_DIR"
else
    echo "No authentication"
    mongodump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --db="$DB_NAME" \
        --out="$BACKUP_DIR"
fi

# Create a metadata file with backup information
cat > "$BACKUP_DIR/backup_info.txt" << EOF
MaiMBot Database Backup
=======================
Backup Date: $(date)
Database Name: $DB_NAME
Host: $DB_HOST:$DB_PORT
Format: BSON (mongodump)

Collections Backed Up:
- messages (chat history)
- graph_data.nodes (memory graph nodes)
- graph_data.edges (memory graph edges)
- llm_usage (LLM usage statistics)
- reasoning_logs (reasoning process logs)
- schedule (schedule data)
- images (image metadata)
- image_descriptions (image descriptions)
- emoji (emoji data)
- relationships (user relationships)
- chat_streams (chat stream metadata)
- recalled_messages (recalled message records)

Restore Command:
  mongorestore --host=$DB_HOST --port=$DB_PORT --db=$DB_NAME --drop $BACKUP_DIR/$DB_NAME/

Or use the restore script:
  ./script/restore_database.sh $BACKUP_DIR
EOF

# List what was backed up
echo ""
echo "Collections backed up:"
ls -lh "$BACKUP_DIR/$DB_NAME/" 2>/dev/null | grep ".bson" | awk '{printf "  %-30s %s\n", $9, $5}'

# Calculate size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "Backup directory size: $BACKUP_SIZE"

# Compress the backup (optional)
read -p "Compress backup to tar.gz? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    echo "Compressing backup..."
    tar -czf "$BACKUP_DIR.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR)"
    COMPRESSED_SIZE=$(du -h "$BACKUP_DIR.tar.gz" | cut -f1)
    echo "Backup compressed to: $BACKUP_DIR.tar.gz ($COMPRESSED_SIZE)"
fi

echo "========================================"
echo "Backup completed successfully!"
echo "Location: $BACKUP_DIR"
echo "========================================"
