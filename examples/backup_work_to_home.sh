#!/bin/bash
#
# Rsync backup script: Work NAS -> Home NAS
# Backs up /volume1/Main/Main from work to /Main/WorkBackup on home NAS
#

WORK_NAS="admin@192.168.0.62"
HOME_NAS="admin@192.168.1.129"
SOURCE="/volume1/Main/Main/"
DEST="/Main/WorkBackup/"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Work NAS to Home NAS Backup Script"
echo "========================================="
echo "Source: $WORK_NAS:$SOURCE"
echo "Destination: $HOME_NAS:$DEST"
echo ""

# Check connectivity
echo -e "${YELLOW}Testing connectivity...${NC}"
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $WORK_NAS "echo 'Work NAS OK'" 2>/dev/null; then
    echo -e "${RED}ERROR: Cannot connect to work NAS${NC}"
    exit 1
fi

if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $HOME_NAS "echo 'Home NAS OK'" 2>/dev/null; then
    echo -e "${RED}ERROR: Cannot connect to home NAS${NC}"
    exit 1
fi
echo -e "${GREEN}Connectivity check passed${NC}"
echo ""

# Check available space on home NAS
echo -e "${YELLOW}Checking available space on home NAS...${NC}"
HOME_AVAIL=$(ssh $HOME_NAS "df -h /Main | tail -1 | awk '{print \$4}'")
echo "Available space on home NAS: $HOME_AVAIL"
echo ""

# Dry run first
if [ "$1" != "--execute" ]; then
    echo -e "${YELLOW}Running DRY RUN (no files will be copied)...${NC}"
    echo "To actually perform the backup, run: $0 --execute"
    echo ""

    rsync -avzn --stats \
        --delete \
        --exclude='@eaDir' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='.*' \
        -e "ssh -o ConnectTimeout=30" \
        $WORK_NAS:$SOURCE \
        $HOME_NAS:$DEST

    echo ""
    echo -e "${YELLOW}This was a DRY RUN - no files were copied${NC}"
    echo "To execute the backup, run: $0 --execute"
else
    echo -e "${GREEN}Executing actual backup...${NC}"
    echo ""

    # Create destination directory if it doesn't exist
    ssh $HOME_NAS "mkdir -p $DEST"

    # Run actual rsync
    rsync -avz --progress --stats \
        --delete \
        --exclude='@eaDir' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='.*' \
        -e "ssh -o ConnectTimeout=30" \
        $WORK_NAS:$SOURCE \
        $HOME_NAS:$DEST

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}Backup completed successfully!${NC}"

        # Show final space usage
        echo ""
        echo "Space usage on home NAS after backup:"
        ssh $HOME_NAS "df -h /Main"
    else
        echo ""
        echo -e "${RED}Backup failed!${NC}"
        exit 1
    fi
fi
