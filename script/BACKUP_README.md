# Database Backup & Restore Guide

## Overview

MaiMBot uses MongoDB to store all data including:
- **messages**: Chat history
- **graph_data.nodes**: Memory graph nodes
- **graph_data.edges**: Memory graph edges
- **llm_usage**: LLM usage statistics
- **reasoning_logs**: Reasoning process logs
- **schedule**: Schedule data
- **images**: Image metadata
- **image_descriptions**: Image descriptions
- **knowledges**: Knowledge library data
- **processed_files**: Processed file records
- **emoji**: Emoji data
- **store_memory_dots**: Memory visualization data

## Backup Methods

### Method 1: MongoDB Tools (Recommended - Default)

**Format**: BSON (Binary JSON) - Same format as `mongodb_backup`

**Advantages:**
- ✅ Official MongoDB tools (standard format)
- ✅ Binary format (faster, smaller - ~14MB vs ~17MB)
- ✅ Preserves all MongoDB-specific data types perfectly
- ✅ Better for large databases
- ✅ Same format as your existing `mongodb_backup`
- ✅ Compatible with MongoDB Compass and other tools

**Requirements:**
Install MongoDB Database Tools from: https://www.mongodb.com/try/download/database-tools

**Backup:**
```bash
# Linux/Mac
./script/backup_database.sh

# Custom output directory
./script/backup_database.sh backups/my_backup

# Windows
script\backup_database.bat
```

**Restore:**
```bash
# Linux/Mac
./script/restore_database.sh mongodb_backup
./script/restore_database.sh backups/20251103_230402
./script/restore_database.sh backups/20251103_230402.tar.gz

# Windows
script\restore_database.bat mongodb_backup
script\restore_database.bat backups\20251103_230402
script\restore_database.bat backups\20251103_230402.tar.gz
```

### Method 2: Python Scripts (Alternative - No tools required)

**Format**: JSON (human-readable text files)

**Advantages:**
- ✅ No additional tools required (uses pymongo)
- ✅ Creates JSON files (human-readable)
- ✅ Cross-platform
- ✅ Easy to inspect and modify

**Backup:**
```bash
# Linux/Mac/Windows
python script/backup_database.py

# Custom output directory
python script/backup_database.py backups/my_backup
```

**Restore:**
```bash
# Linux/Mac/Windows
python script/restore_database.py backups/20250103_123456
```

## Migrating to Another Machine

### Step 1: Create Backup on Source Machine
```bash
# Using mongodump (recommended)
./script/backup_database.sh backups/migration_backup
# Press 'Y' when asked to compress

# Or using Python method
python script/backup_database.py backups/migration_backup
tar -czf backups/migration_backup.tar.gz -C backups migration_backup
```

### Step 2: Transfer Backup Files
```bash
# Transfer compressed backup
scp backups/migration_backup.tar.gz user@target-machine:/path/to/MaiMBot/backups/

# Or transfer entire directory
rsync -avz backups/migration_backup/ user@target-machine:/path/to/MaiMBot/backups/migration_backup/
```

### Step 3: Restore on Target Machine
```bash
# Using mongorestore (recommended)
./script/restore_database.sh backups/migration_backup.tar.gz
# Or
./script/restore_database.sh backups/migration_backup

# Using Python method
python script/restore_database.py backups/migration_backup
```

## Backup Schedule Recommendations

### Development Environment
- **Daily**: Before major code changes
- **Weekly**: Regular backups
- **Before Updates**: Always backup before updating dependencies

### Production Environment
- **Hourly**: For active bots with important data
- **Daily**: Minimum recommendation
- **Before Deployment**: Always backup before updates

### Automated Backups (Linux/Mac)

Add to crontab:
```bash
# Edit crontab
crontab -e

# Daily backup at 3 AM
0 3 * * * cd /path/to/MaiMBot && python script/backup_database.py backups/auto_$(date +\%Y\%m\%d)

# Weekly backup (keep only last 4 weeks)
0 3 * * 0 cd /path/to/MaiMBot && python script/backup_database.py backups/weekly_$(date +\%Y\%W) && find backups/weekly_* -mtime +28 -delete
```

## Backup Storage Best Practices

1. **Multiple Locations**: Store backups in at least 2 different locations
2. **Cloud Storage**: Consider uploading to cloud services (Google Drive, Dropbox, S3)
3. **Versioning**: Keep multiple versions (e.g., daily for 7 days, weekly for 4 weeks)
4. **Testing**: Regularly test restore process to ensure backups are valid
5. **Compression**: Backups are automatically compressed to save space

## Troubleshooting

### "Connection refused" Error
- Ensure MongoDB is running: `systemctl status mongodb` or check `script/run_db.bat`
- Check connection settings in `.env` file

### "Permission denied" Error
- Make scripts executable: `chmod +x script/*.sh`
- Check MongoDB user permissions if using authentication

### "ModuleNotFoundError: No module named 'pymongo'"
- Install dependencies: `pip install pymongo python-dotenv`

### Backup is too large
- Use MongoDB tools (mongodump) instead of Python method
- Consider archiving old data separately
- Check for unnecessary data in collections

## Security Considerations

1. **Protect Backup Files**: Backups contain sensitive data (API keys, chat history)
2. **Encrypt Backups**: Consider encrypting backups before transferring
3. **Secure Transfer**: Use secure methods (scp, sftp) for transferring backups
4. **Access Control**: Restrict access to backup files
5. **Clean Old Backups**: Regularly remove outdated backups to minimize exposure

## Quick Reference

```bash
# Quick backup (Python)
python script/backup_database.py

# Quick restore (Python)
python script/restore_database.py backups/20250103_123456

# View backup info
cat backups/20250103_123456/backup_info.txt

# List all backups
ls -lh backups/
```
