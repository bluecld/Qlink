\
param([int]$Lines = 200)

$cfg = Get-Content "config\targets.json" | ConvertFrom-Json
$HostName = $cfg.host
$User = $cfg.user
$Key = $cfg.key

Get-Service ssh-agent | Set-Service -StartupType Automatic | Out-Null
Start-Service ssh-agent | Out-Null
ssh-add $Key | Out-Null

ssh -t -i $Key "$User@$HostName" "journalctl -u qlink-bridge -f -n $Lines --no-pager"
