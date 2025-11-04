#!/usr/bin/env python3
"""
MongoDB Backup Script for MaiMBot (Python version)
Exports all collections to JSON files for easy backup and migration
Usage: python backup_database.py [output_directory]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from pymongo import MongoClient

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


def backup_database(output_dir=None):
    """Backup all collections to JSON files"""
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent / "backups" / timestamp
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Connect to database
    client = get_mongo_client()
    db_name = os.getenv("DATABASE_NAME", "MegBot")
    db = client[db_name]

    print("=" * 60)
    print("MaiMBot Database Backup (Python)")
    print("=" * 60)
    print(f"Database: {db_name}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    # Get all collection names
    collections = db.list_collection_names()
    print(f"Found {len(collections)} collections to backup")

    backup_info = {
        "backup_date": datetime.now().isoformat(),
        "database_name": db_name,
        "collections": {},
    }

    # Backup each collection
    for collection_name in collections:
        print(f"Backing up: {collection_name}...", end=" ")
        collection = db[collection_name]

        # Get all documents
        documents = list(collection.find())
        doc_count = len(documents)

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        # Save to JSON file
        output_file = output_dir / f"{collection_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2, default=str)

        backup_info["collections"][collection_name] = {
            "document_count": doc_count,
            "file_size": output_file.stat().st_size,
        }

        print(f"✓ ({doc_count} documents)")

    # Save backup metadata
    metadata_file = output_dir / "backup_info.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(backup_info, f, indent=2)

    # Create human-readable info file
    info_file = output_dir / "backup_info.txt"
    with open(info_file, "w", encoding="utf-8") as f:
        f.write(f"Backup Date: {backup_info['backup_date']}\n")
        f.write(f"Database Name: {db_name}\n")
        f.write(f"\nCollections Backed Up:\n")
        for coll_name, info in backup_info["collections"].items():
            f.write(
                f"  - {coll_name}: {info['document_count']} documents "
                f"({info['file_size']} bytes)\n"
            )

    # Calculate total size
    total_size = sum(
        f.stat().st_size for f in output_dir.glob("*.json")
    )

    print("=" * 60)
    print(f"Backup completed successfully!")
    print(f"Total collections: {len(collections)}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
    print(f"Location: {output_dir}")
    print("=" * 60)

    client.close()
    return output_dir


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        backup_database(output_dir)
    except Exception as e:
        print(f"Error during backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
