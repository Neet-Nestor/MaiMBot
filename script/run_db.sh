#!/bin/bash
# Start MongoDB with local data directory
# Usage: ./script/run_db.sh

cd "$(dirname "$0")/.."

# Create mongodb data directory if it doesn't exist
mkdir -p mongodb

echo "Starting MongoDB on port 27017..."
echo "Data directory: $(pwd)/mongodb"
echo "Press Ctrl+C to stop"
echo "=========================================="

# Start MongoDB
mongod --dbpath="mongodb" --port 27017
