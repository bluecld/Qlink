# Install Tailscale on the Raspberry Pi defined in config\targets.json
param(
    [string]$AuthKey
)

$cfgPath = "config\targets.json"
if (-not (Test-Path $cfgPath)) {
    Write-Error "Missing $cfgPath. Create it (or copy config\targets.example.json) and rerun."
    exit 1
}

$cfg = Get-Content $cfgPath | ConvertFrom-Json
$HostName = $cfg.host
$User = $cfg.user
$Key = $cfg.key

if (-not $HostName -or -not $User -or -not $Key) {
    Write-Error "config\targets.json must include host, user, and key entries."
    exit 1
}

function Invoke-Remote {
    param(
        [string]$Command,
        [string]$Description
    )

    if ($Description) {
        Write-Host ""
        Write-Host $Description
    }

    & ssh -i $Key "$User@$HostName" $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Remote command failed. See output above."
        exit $LASTEXITCODE
    }
}

Invoke-Remote "bash -lc 'curl -fsSL https://tailscale.com/install.sh | sh'" "Installing Tailscale package..."
Invoke-Remote "sudo systemctl enable --now tailscaled" "Ensuring tailscaled service is enabled and running..."

$tailscaleUpCommand = $null
if ($AuthKey) {
    $tailscaleUpCommand = "sudo tailscale up --authkey='$AuthKey'"
    Invoke-Remote $tailscaleUpCommand "Bringing Tailscale online with supplied auth key..."
    Invoke-Remote "sudo tailscale status" "Tailscale status:"
    Write-Host ""
    Write-Host "Tailscale installation and login complete."
} else {
    Write-Host ""
    Write-Host "Tailscale package is installed."
    Write-Host "To authenticate, run the following command and complete the login flow:"
    Write-Host ""
    Write-Host "  ssh -i $Key $User@$HostName 'sudo tailscale up'"
    Write-Host ""
    Write-Host "Add any tailscale up flags you need (for example --ssh, --advertise-routes, or --accept-routes)."
    Write-Host "After login, confirm status with:"
    Write-Host ""
    Write-Host "  ssh -i $Key $User@$HostName 'sudo tailscale status'"
}
