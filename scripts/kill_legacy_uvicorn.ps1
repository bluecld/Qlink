param(
    [switch]$Force,
    [int]$Port = 8000
)

$cfg = Get-Content "config\targets.json" -Raw | ConvertFrom-Json
$HostName = $cfg.host
$User = $cfg.user
$Key = $cfg.key

if (-not (Test-Path $Key)) {
    throw "SSH key not found: $Key"
}

$remoteIdentity = "$User@$HostName"

function Invoke-RemoteCommand {
    param([string]$Command)
    ssh -i "$Key" "$remoteIdentity" "$Command"
}

$processList = Invoke-RemoteCommand "ps -eo pid,cmd --no-headers | grep uvicorn | grep -v grep"
if (-not $processList) {
    Write-Host "No uvicorn processes found on $HostName"
    return
}

$parsed = @()
foreach ($line in $processList) {
    if ($line -match "^\s*(\d+)\s+(.*)$") {
        $parsed += [pscustomobject]@{
            Pid     = [int]$Matches[1]
            Command = $Matches[2]
        }
    }
}

if (-not $parsed) {
    Write-Host "Unable to parse uvicorn process list"
    return
}

$stale = $parsed | Where-Object { $_.Command -notmatch "/home/pi/qlink-bridge" }
if (-not $stale) {
    Write-Host "No legacy uvicorn processes found. All processes originate from /home/pi/qlink-bridge."
    return
}

Write-Host ("Detected legacy uvicorn processes holding port {0}`n" -f $Port)
$stale | ForEach-Object {
    Write-Host ("PID {0}`t{1}" -f $_.Pid, $_.Command)
}

if (-not $Force) {
    Write-Host "\nRun this script again with -Force to terminate the listed processes."
    return
}

foreach ($proc in $stale) {
    Write-Host "Terminating PID $($proc.Pid)..."
    Invoke-RemoteCommand "sudo kill $($proc.Pid)"
}

Write-Host "Legacy uvicorn processes terminated."
