#!/bin/bash
# MongoDB Restore Script for MaiMBot (mongorestore - BSON format)
# Usage: ./restore_database.sh <backup_directory_or_tar_gz>
# Restores backups created by mongodump (like mongodb_backup)

set -e

if [ -z "$1" ]; then
    echo "Error: Please provide backup directory or tar.gz file"
    echo ""
    echo "Usage: ./restore_database.sh <backup_directory_or_tar_gz>"
    echo ""
    echo "Examples:"
    echo "  ./restore_database.sh mongodb_backup"
    echo "  ./restore_database.sh backups/20251103_230402"
    echo "  ./restore_database.sh backups/20251103_230402.tar.gz"
    exit 1
fi

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
BACKUP_PATH="$1"

echo "========================================"
echo "MaiMBot Database Restore (mongorestore)"
echo "========================================"

# Check if mongorestore is available
if ! command -v mongorestore &> /dev/null; then
    echo "ERROR: mongorestore not found!"
    echo ""
    echo "Please install MongoDB Database Tools:"
    echo "  https://www.mongodb.com/try/download/database-tools"
    echo ""
    echo "Or use the Python restore script instead:"
    echo "  python script/restore_database.py <backup_dir>"
    exit 1
fi

# Check if input is a tar.gz file
if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    echo "Extracting backup archive..."
    EXTRACT_DIR="temp_restore_$$"
    mkdir -p "$EXTRACT_DIR"
    tar -xzf "$BACKUP_PATH" -C "$EXTRACT_DIR"
    BACKUP_DIR="$EXTRACT_DIR/$(ls "$EXTRACT_DIR" | head -n 1)"
else
    BACKUP_DIR="$BACKUP_PATH"
fi

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Detect database directory in backup
if [ -d "$BACKUP_DIR/$DB_NAME" ]; then
    RESTORE_PATH="$BACKUP_DIR/$DB_NAME"
elif [ -d "$BACKUP_DIR/MegBot" ]; then
    RESTORE_PATH="$BACKUP_DIR/MegBot"
    echo "Note: Backup contains 'MegBot' database, will restore to '$DB_NAME'"
else
    # Try to restore entire directory
    RESTORE_PATH="$BACKUP_DIR"
fi

echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup: $BACKUP_DIR"
echo "Restore path: $RESTORE_PATH"
echo "Format: BSON (mongodump)"
echo "========================================"

# Show backup info if available
if [ -f "$BACKUP_DIR/backup_info.txt" ]; then
    echo "Backup Information:"
    echo ""
    cat "$BACKUP_DIR/backup_info.txt"
    echo ""
    echo "========================================"
fi

# List collections in backup
if [ -d "$RESTORE_PATH" ]; then
    echo "Collections to restore:"
    ls "$RESTORE_PATH"/*.bson 2>/dev/null | while read file; do
        filename=$(basename "$file" .bson)
        size=$(du -h "$file" | cut -f1)
        count=$(bsondump "$file" 2>/dev/null | wc -l || echo "?")
        printf "  %-30s %6s  (%s documents)\n" "$filename" "$size" "$count"
    done
    echo "========================================"
fi

# Ask for confirmation
echo ""
echo "WARNING: This will DROP and replace existing collections!"
read -p "Continue? Type 'yes' to confirm: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    # Clean up if we extracted
    if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
        rm -rf "$EXTRACT_DIR"
    fi
    exit 0
fi

echo ""
echo "Starting restore..."

# Perform restore
if [ ! -z "$MONGODB_USERNAME" ] && [ ! -z "$MONGODB_PASSWORD" ]; then
    AUTH_SOURCE="${MONGODB_AUTH_SOURCE:-admin}"
    echo "Using authentication (user: $MONGODB_USERNAME)"
    mongorestore \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$MONGODB_USERNAME" \
        --password="$MONGODB_PASSWORD" \
        --authenticationDatabase="$AUTH_SOURCE" \
        --db="$DB_NAME" \
        --drop \
        "$RESTORE_PATH"
elif [ ! -z "$MONGODB_URI" ]; then
    echo "Using MongoDB URI connection"
    mongorestore \
        --uri="$MONGODB_URI" \
        --db="$DB_NAME" \
        --drop \
        "$RESTORE_PATH"
else
    echo "No authentication"
    mongorestore \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --db="$DB_NAME" \
        --drop \
        "$RESTORE_PATH"
fi

# Clean up temporary extraction directory
if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    echo ""
    echo "Cleaning up temporary files..."
    rm -rf "$EXTRACT_DIR"
fi

echo ""
echo "========================================"
echo "Restore completed successfully!"
echo "Database: $DB_NAME on $DB_HOST:$DB_PORT"
echo "========================================"
