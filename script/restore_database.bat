@echo off
REM MongoDB Restore Script for MaiMBot (Windows - mongorestore BSON format)
REM Usage: restore_database.bat <backup_directory_or_tar_gz>
REM Restores backups created by mongodump (like mongodb_backup)

if "%~1"=="" (
    echo Error: Please provide backup directory or tar.gz file
    echo.
    echo Usage: restore_database.bat ^<backup_directory_or_tar_gz^>
    echo.
    echo Examples:
    echo   restore_database.bat mongodb_backup
    echo   restore_database.bat backups\20251103_230402
    echo   restore_database.bat backups\20251103_230402.tar.gz
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0.."

echo ========================================
echo MaiMBot Database Restore (mongorestore)
echo ========================================

REM Check if mongorestore exists
where mongorestore >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: mongorestore not found!
    echo.
    echo Please install MongoDB Database Tools from:
    echo   https://www.mongodb.com/try/download/database-tools
    echo.
    echo Or use the Python restore script instead:
    echo   python script\restore_database.py "%~1"
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

set BACKUP_PATH=%~1
set EXTRACT_DIR=temp_restore_%RANDOM%

REM Check if input is a tar.gz file
echo %BACKUP_PATH% | findstr /i "\.tar\.gz$" >nul
if %errorlevel% equ 0 (
    echo Extracting backup archive...
    mkdir %EXTRACT_DIR%
    tar -xzf "%BACKUP_PATH%" -C %EXTRACT_DIR%
    for /d %%i in (%EXTRACT_DIR%\*) do set BACKUP_DIR=%%i
) else (
    set BACKUP_DIR=%BACKUP_PATH%
)

REM Check if backup directory exists
if not exist "%BACKUP_DIR%" (
    echo ERROR: Backup directory not found: %BACKUP_DIR%
    pause
    exit /b 1
)

REM Detect database directory in backup
if exist "%BACKUP_DIR%\%DATABASE_NAME%" (
    set RESTORE_PATH=%BACKUP_DIR%\%DATABASE_NAME%
) else if exist "%BACKUP_DIR%\MegBot" (
    set RESTORE_PATH=%BACKUP_DIR%\MegBot
    echo Note: Backup contains 'MegBot' database, will restore to '%DATABASE_NAME%'
) else (
    set RESTORE_PATH=%BACKUP_DIR%
)

echo Database: %DATABASE_NAME%
echo Host: %MONGODB_HOST%:%MONGODB_PORT%
echo Backup: %BACKUP_DIR%
echo Restore path: %RESTORE_PATH%
echo Format: BSON (mongodump)
echo ========================================

REM Show backup info if available
if exist "%BACKUP_DIR%\backup_info.txt" (
    echo Backup Information:
    echo.
    type "%BACKUP_DIR%\backup_info.txt"
    echo.
    echo ========================================
)

REM List collections in backup
if exist "%RESTORE_PATH%\*.bson" (
    echo Collections to restore:
    for %%f in ("%RESTORE_PATH%\*.bson") do (
        set filename=%%~nf
        set size=%%~zf
        echo   !filename! ^(%%~zf bytes^)
    )
    echo ========================================
)

REM Ask for confirmation
echo.
echo WARNING: This will DROP and replace existing collections!
set /p confirm="Continue? Type 'yes' to confirm: "
if /i not "%confirm%"=="yes" (
    echo Restore cancelled
    if exist %EXTRACT_DIR% rmdir /s /q %EXTRACT_DIR%
    pause
    exit /b 0
)

echo.
echo Starting restore...

REM Perform restore
mongorestore --host=%MONGODB_HOST% --port=%MONGODB_PORT% --db=%DATABASE_NAME% --drop "%RESTORE_PATH%"
if %errorlevel% neq 0 goto :error

REM Clean up temporary extraction directory
if exist %EXTRACT_DIR% (
    echo.
    echo Cleaning up temporary files...
    rmdir /s /q %EXTRACT_DIR%
)

echo.
echo ========================================
echo Restore completed successfully!
echo Database: %DATABASE_NAME% on %MONGODB_HOST%:%MONGODB_PORT%
echo ========================================
pause
exit /b 0

:error
if exist %EXTRACT_DIR% rmdir /s /q %EXTRACT_DIR%
echo ========================================
echo Restore failed!
echo Make sure MongoDB is running and accessible
echo ========================================
pause
exit /b 1
