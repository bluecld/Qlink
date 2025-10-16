param(
    [Parameter(Mandatory = $true, Position = 0)]
    [int]$DeviceId,
    [switch]$On,
    [switch]$Off,
    [int]$Level,
    [string]$BridgeHost = "qlinkpi.local",
    [int]$Port = 8000,
    [int]$Timeout = 5
)

function _usage {
    Write-Host "Usage: .\\scripts\\test_device.ps1 -DeviceId <id> (-On | -Off | -Level <n>) [-Host <host>]" -ForegroundColor Yellow
    exit 1
}

if (-not ($On -or $Off -or ($PSBoundParameters.ContainsKey('Level')))) {
    _usage
}

$url = "http://$BridgeHost`:$Port/device/$DeviceId/set"

if ($On) {
    $body = @{ switch = 'on' } | ConvertTo-Json
}
elseif ($Off) {
    $body = @{ switch = 'off' } | ConvertTo-Json
}
else {
    $lvl = [int]$Level
    if ($lvl -lt 0 -or $lvl -gt 100) { Write-Host "Level must be 0-100" -ForegroundColor Red; exit 2 }
    $body = @{ level = $lvl } | ConvertTo-Json
}

Write-Host "POST $url`nPayload: $body"

try {
    $r = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType 'application/json' -TimeoutSec $Timeout -ErrorAction Stop
    Write-Host "Response:" -ForegroundColor Green
    $r | ConvertTo-Json -Depth 5 | Write-Host
}
catch {
    Write-Host "Request failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 3
}
