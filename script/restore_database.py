#!/usr/bin/env python3
"""
MongoDB Restore Script for MaiMBot (Python version)
Restores all collections from JSON files
Usage: python restore_database.py <backup_directory>
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables
load_dotenv()


def get_mongo_client():
    """Create MongoDB client from environment variables"""
    uri = os.getenv("MONGODB_URI")
    host = os.getenv("MONGODB_HOST", "127.0.0.1")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    username = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")
    auth_source = os.getenv("MONGODB_AUTH_SOURCE")

    if uri and uri.startswith("mongodb://"):
        return MongoClient(uri)

    if username and password:
        return MongoClient(
            host, port, username=username, password=password, authSource=auth_source
        )

    return MongoClient(host, port)


def restore_database(backup_dir):
    """Restore all collections from JSON files"""
    backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        print(f"Error: Backup directory not found: {backup_dir}")
        sys.exit(1)

    # Connect to database
    client = get_mongo_client()
    db_name = os.getenv("DATABASE_NAME", "MegBot")
    db = client[db_name]

    print("=" * 60)
    print("MaiMBot Database Restore (Python)")
    print("=" * 60)
    print(f"Database: {db_name}")
    print(f"Backup: {backup_dir}")
    print("=" * 60)

    # Show backup info if available
    info_file = backup_dir / "backup_info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            backup_info = json.load(f)
            print(f"Backup Date: {backup_info['backup_date']}")
            print(f"Original Database: {backup_info['database_name']}")
            print(f"Collections: {len(backup_info['collections'])}")
            print("=" * 60)

    # Ask for confirmation
    confirm = input("This will overwrite existing data. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Restore cancelled")
        sys.exit(0)

    # Find all JSON files
    json_files = list(backup_dir.glob("*.json"))
    if not json_files:
        print("Error: No JSON files found in backup directory")
        sys.exit(1)

    # Filter out metadata files
    json_files = [f for f in json_files if f.stem != "backup_info"]

    print(f"\nFound {len(json_files)} collections to restore")

    # Restore each collection
    for json_file in json_files:
        collection_name = json_file.stem
        print(f"Restoring: {collection_name}...", end=" ")

        # Load documents
        with open(json_file, "r", encoding="utf-8") as f:
            documents = json.load(f)

        if not documents:
            print("✓ (empty collection)")
            continue

        # Convert string _id back to ObjectId if needed
        for doc in documents:
            if "_id" in doc and isinstance(doc["_id"], str):
                try:
                    doc["_id"] = ObjectId(doc["_id"])
                except Exception:
                    # If conversion fails, keep as string
                    pass

        # Drop existing collection and insert documents
        collection = db[collection_name]
        collection.drop()

        if documents:
            collection.insert_many(documents)

        print(f"✓ ({len(documents)} documents)")

    print("=" * 60)
    print("Restore completed successfully!")
    print("=" * 60)

    client.close()


def main():
    if len(sys.argv) < 2:
        print("Error: Please provide backup directory")
        print("Usage: python restore_database.py <backup_directory>")
        sys.exit(1)

    backup_dir = sys.argv[1]

    try:
        restore_database(backup_dir)
    except Exception as e:
        print(f"Error during restore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
