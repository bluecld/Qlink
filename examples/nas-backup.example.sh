#!/bin/bash
# NAS Backup Script - Sync between two NAS devices via Raspberry Pi bridge
#
# This script connects to a remote NAS via VPN (OpenVPN), and syncs
# data to a local NAS via SSHFS. It's designed to run on a Raspberry Pi
# that acts as a bridge between networks.
#
# REQUIREMENTS:
# - OpenVPN client configured and running
# - SSH keys set up for both NAS devices
# - SSHFS installed (apt install sshfs)
# - rsync installed
#
# SETUP:
# 1. Copy this file: cp nas-backup.example.sh nas-backup.sh
# 2. Edit the variables below with your actual values
# 3. Make executable: chmod +x nas-backup.sh
# 4. Test manually: ./nas-backup.sh --execute
# 5. Add to crontab: 0 2 * * * /home/pi/nas-backup.sh --execute

# ============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================================

# Remote NAS (via VPN) - SOURCE
WORK_NAS="admin@REMOTE_NAS_IP"           # e.g., admin@192.168.0.62
SOURCE="/volume1/Main/Main/"             # Path on remote NAS to backup

# Local NAS - DESTINATION
HOME_NAS="admin@LOCAL_NAS_IP"            # e.g., admin@192.168.1.129
MOUNT_POINT="/home/pi/mnt/home_nas"      # Local mount point for SSHFS
DEST="$MOUNT_POINT/backup/destination/"  # Destination path within mounted NAS

# Logging
LOGFILE="/home/pi/nas-backup.log"        # Main log file
CRON_LOG="/home/pi/nas-backup-cron.log"  # Cron-specific log

# VPN Interface (if using OpenVPN)
VPN_INTERFACE="tun0"                     # OpenVPN tunnel interface

# ============================================================================
# SCRIPT - DO NOT EDIT BELOW UNLESS YOU KNOW WHAT YOU'RE DOING
# ============================================================================

# Function to log messages
log() {
    echo "$1" | tee -a "$LOGFILE"
}

# Function to check if script should execute
should_execute() {
    if [[ "$1" == "--execute" ]]; then
        return 0
    fi

    echo "Dry run mode. Use --execute to actually run the backup."
    echo "This would sync: $WORK_NAS:$SOURCE -> $DEST"
    return 1
}

# Main backup function
main() {
    log "======================================"
    log "NAS Backup: $(date)"
    log "======================================"

    # Check if we should execute
    if ! should_execute "$1"; then
        return 0
    fi

    # Check OpenVPN connection (if using VPN)
    if ! ip addr show "$VPN_INTERFACE" &>/dev/null; then
        log "ERROR: VPN interface $VPN_INTERFACE not found!"
        log "Make sure OpenVPN is running: sudo systemctl status openvpn-client@yourconfig"
        return 1
    fi
    log "VPN connected on $VPN_INTERFACE"

    # Check if work NAS is reachable
    log "Testing connectivity to remote NAS..."
    if ! ssh -o ConnectTimeout=10 "$WORK_NAS" 'echo OK' &>/dev/null; then
        log "ERROR: Cannot reach remote NAS at $WORK_NAS"
        log "Check: 1) VPN is connected 2) SSH keys are set up 3) Remote NAS is online"
        return 1
    fi
    log "Remote NAS connectivity verified"

    # Mount home NAS via SSHFS if not already mounted
    if ! mountpoint -q "$MOUNT_POINT"; then
        log "Mounting local NAS via SSHFS..."
        mkdir -p "$MOUNT_POINT"

        if ! sshfs "$HOME_NAS:/" "$MOUNT_POINT" -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3; then
            log "ERROR: Failed to mount local NAS"
            log "Check: 1) SSHFS is installed 2) SSH keys are set up 3) Mount point exists"
            return 1
        fi
        log "Local NAS mounted successfully"
    else
        log "Home NAS already mounted"
    fi

    # Create destination directory if it doesn't exist
    mkdir -p "$DEST"

    # Run rsync backup
    log ""
    log "EXECUTING BACKUP"
    log "Work NAS -> Pi (via SSHFS) -> Home NAS: $DEST"
    log ""

    # rsync options:
    # -a: archive mode (recursive, preserve permissions, times, etc.)
    # -v: verbose
    # -z: compress during transfer
    # --progress: show progress
    # --stats: show statistics
    # --exclude: exclude patterns
    # --delete: delete files in dest that don't exist in source
    rsync -avz \
        --progress \
        --stats \
        --exclude='@eaDir' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='.*' \
        --delete \
        "$WORK_NAS:$SOURCE" \
        "$DEST" \
        2>&1 | tee -a "$LOGFILE"

    RSYNC_EXIT=$?

    log ""
    log "======================================"
    if [ $RSYNC_EXIT -eq 0 ]; then
        log "Backup completed successfully at $(date)"
    else
        log "Backup completed with errors (exit code: $RSYNC_EXIT) at $(date)"
    fi
    log "======================================"
    log ""

    return $RSYNC_EXIT
}

# Run main function
main "$@"
