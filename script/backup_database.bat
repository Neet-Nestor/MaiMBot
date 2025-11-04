@echo off
REM MongoDB Backup Script for MaiMBot (Windows - mongodump BSON format)
REM Usage: backup_database.bat
REM Creates backups in the same format as mongodb_backup

cd /d "%~dp0.."

echo ========================================
echo MaiMBot Database Backup (mongodump)
echo ========================================

REM Generate timestamp
for /f "tokens=*" %%i in ('powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do set timestamp=%%i
set BACKUP_DIR=backups\%timestamp%

REM Check if mongodump exists
where mongodump >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: mongodump not found!
    echo.
    echo Please install MongoDB Database Tools from:
    echo   https://www.mongodb.com/try/download/database-tools
    echo.
    echo Or use the Python backup script instead:
    echo   python script\backup_database.py
    echo.
    pause
    exit /b 1
)

REM Load environment variables (if .env exists)
if exist .env (
    for /f "usebackq tokens=1* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
)

REM Set defaults
if "%MONGODB_HOST%"=="" set MONGODB_HOST=127.0.0.1
if "%MONGODB_PORT%"=="" set MONGODB_PORT=27017
if "%DATABASE_NAME%"=="" set DATABASE_NAME=MegBot

echo Database: %DATABASE_NAME%
echo Host: %MONGODB_HOST%:%MONGODB_PORT%
echo Output: %BACKUP_DIR%
echo Format: BSON (Binary JSON)
echo ========================================

REM Perform backup
echo Creating backup with mongodump...
mongodump --host=%MONGODB_HOST% --port=%MONGODB_PORT% --db=%DATABASE_NAME% --out=%BACKUP_DIR%
if %errorlevel% neq 0 goto :error

REM Create backup info file
echo MaiMBot Database Backup > %BACKUP_DIR%\backup_info.txt
echo ======================= >> %BACKUP_DIR%\backup_info.txt
echo Backup Date: %date% %time% >> %BACKUP_DIR%\backup_info.txt
echo Database Name: %DATABASE_NAME% >> %BACKUP_DIR%\backup_info.txt
echo Host: %MONGODB_HOST%:%MONGODB_PORT% >> %BACKUP_DIR%\backup_info.txt
echo Format: BSON (mongodump) >> %BACKUP_DIR%\backup_info.txt
echo. >> %BACKUP_DIR%\backup_info.txt
echo Restore Command: >> %BACKUP_DIR%\backup_info.txt
echo   mongorestore --host=%MONGODB_HOST% --port=%MONGODB_PORT% --db=%DATABASE_NAME% --drop %BACKUP_DIR%\%DATABASE_NAME%\ >> %BACKUP_DIR%\backup_info.txt

REM List backed up collections
echo.
echo Collections backed up:
dir /b %BACKUP_DIR%\%DATABASE_NAME%\*.bson

REM Calculate size
for /f %%i in ('powershell -Command "(Get-ChildItem -Path '%BACKUP_DIR%' -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB"') do set SIZE_MB=%%i
echo.
echo Backup directory size: %SIZE_MB% MB

REM Ask about compression
set /p COMPRESS="Compress backup to tar.gz? (Y/n): "
if /i "%COMPRESS%"=="n" goto :skip_compress
if "%COMPRESS%"=="" goto :do_compress
if /i "%COMPRESS%"=="y" goto :do_compress
goto :skip_compress

:do_compress
echo Compressing backup...
tar -czf %BACKUP_DIR%.tar.gz -C backups %timestamp%
if %errorlevel% equ 0 (
    for %%i in (%BACKUP_DIR%.tar.gz) do set COMPRESSED_SIZE=%%~zi
    powershell -Command "[math]::Round(%COMPRESSED_SIZE% / 1MB, 2)" > temp_size.txt
    set /p COMPRESSED_MB=<temp_size.txt
    del temp_size.txt
    echo Backup compressed to: %BACKUP_DIR%.tar.gz (!COMPRESSED_MB! MB^)
)

:skip_compress
echo ========================================
echo Backup completed successfully!
echo Location: %BACKUP_DIR%
echo ========================================
pause
exit /b 0

:error
echo ========================================
echo Backup failed!
echo Make sure MongoDB is running and accessible
echo ========================================
pause
exit /b 1
