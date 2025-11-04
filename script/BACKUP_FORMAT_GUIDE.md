# MongoDB Backup Format Guide

## Overview

The `mongodb_backup` directory uses the **standard MongoDB dump format** created by the official `mongodump` tool. This format is:
- **Binary efficient**: Smaller and faster than JSON
- **Type-preserving**: Maintains MongoDB-specific data types
- **Official standard**: Compatible with all MongoDB tools

## Creation Information

**Your backup was created on**: March 28, 2025
**Method**: `mongodump` command (Git commit: "mongodump database")
**Location**: `/home/nqin/code/MaiMBot/mongodb_backup/`

## Directory Structure

```
mongodb_backup/
├── admin/                          # Admin database (system)
└── MegBot/                         # Your bot database
    ├── chat_streams.bson           # Binary data
    ├── chat_streams.metadata.json  # Index definitions
    ├── emoji.bson
    ├── emoji.metadata.json
    ├── graph_data.edges.bson
    ├── graph_data.edges.metadata.json
    ├── graph_data.nodes.bson
    ├── graph_data.nodes.metadata.json
    ├── messages.bson
    ├── messages.metadata.json
    └── ... (more collections)
```

## File Types

### 1. BSON Files (`.bson`)

**Format**: Binary JSON
**Purpose**: Contains actual document data
**Size**: More compact than JSON

**Example structure** (emoji.bson):
```
Binary representation of documents like:
{
  "_id": ObjectId("67d0fdf9acd31b702939ec8a"),
  "filename": "1741442312_d4ef40d8.jpg",
  "path": "data/emoji/1741442312_d4ef40d8.jpg",
  "embedding": [array of 768 floats],
  "tags": ["happy", "smile"],
  "usage_count": 5
}
```

**Viewing BSON data**:
```bash
# Convert BSON to readable JSON
bsondump mongodb_backup/MegBot/messages.bson --pretty

# Count documents
bsondump mongodb_backup/MegBot/messages.bson | wc -l

# Search for specific content
bsondump mongodb_backup/MegBot/messages.bson | grep "specific_text"
```

### 2. Metadata Files (`.metadata.json`)

**Format**: JSON
**Purpose**: Stores collection metadata and index definitions
**Size**: Very small (< 1KB each)

**Structure**:
```json
{
  "indexes": [
    {
      "v": {"$numberInt": "2"},       // Index version
      "key": {"_id": {"$numberInt": "1"}},  // Index key
      "name": "_id_"                  // Index name
    },
    {
      "v": {"$numberInt": "2"},
      "key": {"filename": {"$numberInt": "1"}},
      "name": "filename_1",
      "unique": true                  // Unique constraint
    }
  ],
  "uuid": "78b5c180502e47fb9df8c9a9c3ea10f3",  // Collection UUID
  "collectionName": "emoji",         // Collection name
  "type": "collection"               // Type
}
```

**Why metadata is important**:
- Preserves database indexes (performance)
- Maintains unique constraints (data integrity)
- Stores collection configuration

## How It Was Created

### Original Command (likely):
```bash
mongodump --host=127.0.0.1 --port=27017 --db=MegBot --out=mongodb_backup
```

### What mongodump does:
1. Connects to MongoDB
2. For each collection:
   - Exports documents to `.bson` file (binary format)
   - Exports indexes to `.metadata.json` file
3. Creates directory structure matching database/collection hierarchy

## Data Statistics

```
Total Size: ~14 MB
Collections: 12
Documents: 27,569

Breakdown:
- llm_usage.bson: 5.3 MB (22,801 documents)
- graph_data.nodes.bson: 3.2 MB (553 documents)
- reasoning_logs.bson: 1.9 MB (221 documents)
- emoji.bson: 1.7 MB (83 documents)
- messages.bson: 1.3 MB (1,995 documents)
- graph_data.edges.bson: 232 KB (1,667 documents)
- Other collections: < 100 KB each
```

## Format Comparison

### mongodump Format (BSON) vs Python Backup (JSON)

| Feature | mongodump (BSON) | Python Script (JSON) |
|---------|------------------|----------------------|
| **File Size** | ~14 MB | ~17 MB |
| **Speed** | Very Fast | Moderate |
| **Human Readable** | No (binary) | Yes (text) |
| **Type Preservation** | Perfect | Approximate |
| **Tools Required** | mongodump/mongorestore | Python + pymongo |
| **ObjectId** | Native binary | String representation |
| **Dates** | Native BSON date | ISO string |
| **Binary Data** | Native binary | Base64 encoded |
| **Editing** | Difficult | Easy (text editor) |
| **Best For** | Production backups | Development/migration |

### Type Preservation Examples

**BSON (mongodump)**:
```javascript
{
  "_id": ObjectId("67cc17e46a40f5eb4c24b501"),  // Native ObjectId
  "relationship_value": 224.0,                  // Native double
  "created_at": ISODate("2025-03-28T10:30:00Z") // Native date
}
```

**JSON (Python backup)**:
```json
{
  "_id": "67cc17e46a40f5eb4c24b501",            // String
  "relationship_value": 224.0,                  // Number
  "created_at": "2025-03-28T10:30:00.000Z"      // String
}
```

## Inspecting the Backup

### Check what's in the backup:
```bash
# List all collections
ls -lh mongodb_backup/MegBot/*.bson

# Count documents per collection
for file in mongodb_backup/MegBot/*.bson; do
    echo -n "$(basename $file .bson): "
    bsondump "$file" 2>/dev/null | wc -l
done
```

### View sample data:
```bash
# View first document from messages collection
bsondump mongodb_backup/MegBot/messages.bson --pretty | head -50

# Search for specific user
bsondump mongodb_backup/MegBot/messages.bson | grep "user_id.*398429004"

# Export specific collection to JSON
bsondump mongodb_backup/MegBot/relationships.bson --pretty > relationships_readable.json
```

### Check indexes:
```bash
# Pretty-print metadata
python3 -m json.tool mongodb_backup/MegBot/emoji.metadata.json

# List all indexes
for file in mongodb_backup/MegBot/*.metadata.json; do
    echo "=== $(basename $file) ==="
    jq '.indexes[].name' "$file" 2>/dev/null
done
```

## Converting Between Formats

### Convert BSON to JSON (for editing):
```bash
# Convert entire collection
bsondump mongodb_backup/MegBot/messages.bson --pretty > messages.json

# Edit messages.json with text editor

# Convert back (requires mongoimport)
mongoimport --db=MegBot --collection=messages --file=messages.json --drop
```

### Convert JSON backup to BSON:
```bash
# If you have JSON from Python backup
for collection in backups/restored_*/*.json; do
    name=$(basename "$collection" .json)
    mongoimport --db=MegBot --collection="$name" --file="$collection"
done

# Then create BSON backup
mongodump --db=MegBot --out=new_backup
```

## Advantages of This Format

### ✅ Pros:
1. **Official MongoDB format** - Guaranteed compatibility
2. **Efficient storage** - Binary format is compact
3. **Fast restore** - Native binary loading
4. **Type-safe** - Preserves all MongoDB data types perfectly
5. **Index preservation** - Maintains database performance characteristics
6. **Large dataset friendly** - Handles gigabytes efficiently
7. **Standard tooling** - Works with MongoDB Compass, Studio 3T, etc.

### ⚠️ Cons:
1. **Not human-readable** - Need `bsondump` to view
2. **Requires MongoDB tools** - mongodump/mongorestore installation
3. **Harder to edit** - Can't simply edit in text editor
4. **Binary format** - May have compatibility issues across very different MongoDB versions

## When to Use Each Format

### Use mongodump (BSON) for:
- ✅ Production backups
- ✅ Large databases (> 100 MB)
- ✅ Regular automated backups
- ✅ Disaster recovery
- ✅ Migrating between MongoDB servers
- ✅ Need exact type preservation

### Use Python/JSON for:
- ✅ Development/testing
- ✅ Small databases (< 50 MB)
- ✅ Manual data inspection
- ✅ One-time migrations
- ✅ Need to edit backup data
- ✅ Sharing with non-MongoDB tools

## Restore Commands

### Restore entire database:
```bash
mongorestore --host=127.0.0.1 --port=27017 --db=MegBot --drop mongodb_backup/MegBot/
```

### Restore specific collection:
```bash
mongorestore --host=127.0.0.1 --port=27017 \
    --db=MegBot \
    --collection=messages \
    mongodb_backup/MegBot/messages.bson
```

### Restore to different database name:
```bash
mongorestore --host=127.0.0.1 --port=27017 \
    --db=MegBot_test \
    mongodb_backup/MegBot/
```

## Summary

Your `mongodb_backup` directory is a **standard mongodump backup** created on March 28, 2025. It contains:
- **Binary BSON files** with all your document data
- **JSON metadata files** with index definitions
- **Complete database state** at the time of backup

This is the **recommended format for production use** and has now been successfully restored to your active database.
