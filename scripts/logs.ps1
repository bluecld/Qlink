param(
    [int]$Lines = 200,
    [int]$SinceMinutes = 5,
    [switch]$NoFollow
)

$cfg = Get-Content "config\targets.json" -Raw | ConvertFrom-Json
$HostName = $cfg.host
$User = $cfg.user
$Key = $cfg.key

Get-Service ssh-agent | Set-Service -StartupType Automatic | Out-Null
Start-Service ssh-agent | Out-Null
ssh-add $Key | Out-Null

$journalArgs = "-u qlink-bridge --no-pager -n $Lines"
if ($SinceMinutes -gt 0) {
    $journalArgs += " --since '$SinceMinutes min ago'"
}
if (-not $NoFollow) {
    $journalArgs += " -f"
}

$remoteCmd = "journalctl $journalArgs"
ssh -t -i "$Key" "$User@$HostName" "$remoteCmd"
