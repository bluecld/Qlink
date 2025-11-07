# PowerShell script to backup Work NAS to Home NAS
# Run from PC when on work network (or via VPN)

$ErrorActionPreference = "Stop"

$workNAS = "admin@192.168.0.62"
$homeNAS = "admin@192.168.1.129"
$source = "/volume1/Main/Main/"
$dest = "/Main/WorkBackup/"
$rsync = "C:\msys64\usr\bin\rsync.exe"
$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NAS Backup: Work -> Home" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Source: $workNAS`:$source"
Write-Host "Destination: $homeNAS`:$dest"
Write-Host ""

# Check if rsync exists
if (!(Test-Path $rsync)) {
    Write-Host "ERROR: rsync not found at $rsync" -ForegroundColor Red
    exit 1
}

# Dry run or execute
if ($args[0] -ne "--execute") {
    Write-Host "DRY RUN MODE (no files will be copied)" -ForegroundColor Yellow
    Write-Host ""

    & $rsync -avzn --stats `
        --delete `
        --exclude='@eaDir' `
        --exclude='.DS_Store' `
        --exclude='Thumbs.db' `
        --exclude='.*' `
        -e "$ssh" `
        "$workNAS`:$source" `
        "$homeNAS`:$dest"

    Write-Host ""
    Write-Host "DRY RUN COMPLETE" -ForegroundColor Yellow
    Write-Host "To execute the backup, run: .\backup-nas.ps1 --execute" -ForegroundColor Yellow
} else {
    Write-Host "EXECUTING BACKUP..." -ForegroundColor Green
    Write-Host ""

    # Create destination directory
    & $ssh $homeNAS "mkdir -p $dest"

    # Run rsync
    & $rsync -avz --progress --stats `
        --delete `
        --exclude='@eaDir' `
        --exclude='.DS_Store' `
        --exclude='Thumbs.db' `
        --exclude='.*' `
        -e "$ssh" `
        "$workNAS`:$source" `
        "$homeNAS`:$dest"

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "BACKUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
        & $ssh $homeNAS "df -h /Main"
    } else {
        Write-Host ""
        Write-Host "BACKUP FAILED!" -ForegroundColor Red
        exit 1
    }
}
