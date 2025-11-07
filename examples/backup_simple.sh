#!/bin/bash
# Simple 2-step backup via local temp
export PATH="/c/msys64/usr/bin:$PATH"

WORK_NAS="admin@192.168.0.62"
HOME_NAS="admin@192.168.1.129"
SOURCE="/volume1/Main/Main/"
DEST="/Main/WorkBackup/"
TEMP="/c/temp/nas_backup"

echo "======================================"
echo "2-Step Backup: Work NAS -> Home NAS"
echo "======================================"
echo ""
echo "Step 1: Work NAS -> Local temp"
echo "Step 2: Local temp -> Home NAS"
echo ""

if [ "$1" != "--execute" ]; then
    echo "DRY RUN MODE"
    echo ""
    echo "Step 1: Pulling from work NAS..."
    /c/msys64/usr/bin/rsync -avzn --stats \
        --exclude='@eaDir' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='.*' \
        -e "/c/Windows/System32/OpenSSH/ssh.exe" \
        $WORK_NAS:$SOURCE \
        $TEMP/

    echo ""
    echo "Step 2: Pushing to home NAS..."
    /c/msys64/usr/bin/rsync -avzn --stats \
        --delete \
        -e "/c/Windows/System32/OpenSSH/ssh.exe" \
        $TEMP/ \
        $HOME_NAS:$DEST

    echo ""
    echo "DRY RUN COMPLETE - no files copied"
    echo "To execute: $0 --execute"
else
    echo "EXECUTING BACKUP"
    mkdir -p "$TEMP"

    echo ""
    echo "Step 1: Pulling from work NAS..."
    /c/msys64/usr/bin/rsync -avz --progress --stats \
        --exclude='@eaDir' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='.*' \
        -e "/c/Windows/System32/OpenSSH/ssh.exe" \
        $WORK_NAS:$SOURCE \
        $TEMP/

    echo ""
    echo "Step 2: Pushing to home NAS..."
    /c/msys64/usr/bin/rsync -avz --progress --stats \
        --delete \
        -e "/c/Windows/System32/OpenSSH/ssh.exe" \
        $TEMP/ \
        $HOME_NAS:$DEST

    echo ""
    echo "BACKUP COMPLETE!"
fi
