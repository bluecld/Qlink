# Deploy to Pi script
param()

$cfgPath = "config\targets.json"
if (-not (Test-Path $cfgPath)) {
  Copy-Item "config\targets.example.json" $cfgPath -Force
  Write-Host "Created config\targets.json. Edit it and rerun." -ForegroundColor Yellow
  exit 1
}
$cfg = Get-Content $cfgPath | ConvertFrom-Json

$HostName = $cfg.host
$User = $cfg.user
$Key = $cfg.key
$RemoteDir = $cfg.remote_dir
$EnvMap = $cfg.env

## Expand and validate key path early so ssh/scp won't warn about missing file
if ($Key -like '~*') {
  $Key = $Key -replace '^~', $env:USERPROFILE
}
if (-not (Test-Path $Key)) {
  Write-Host "ERROR: SSH key path '$Key' does not exist. Please update $cfgPath with a valid key path." -ForegroundColor Red
  exit 1
}

## Create remote dir
ssh -i $Key "${User}@${HostName}" "mkdir -p '${RemoteDir}' '${RemoteDir}/app' '${RemoteDir}/scripts'"

$localZip = Join-Path $PWD 'app.zip'
if (Test-Path $localZip) { Remove-Item $localZip -Force }
## Package the 'app' directory and config schemas using a small Python helper so zip entries use '/'
$packScript = @'
import zipfile, os
out = r"{0}"
roots = ['app', 'config/schemas']
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
  for root_dir in roots:
    if not os.path.exists(root_dir):
      continue
    for root, dirs, files in os.walk(root_dir):
      for fn in files:
        path = os.path.join(root, fn)
        arc = os.path.relpath(path, '.') .replace('\\', '/')
        z.write(path, arc)
print('packed')
'@ -f $localZip
$scriptPath = Join-Path $PWD 'pack_app.py'
Set-Content -Path $scriptPath -Value $packScript -Encoding UTF8
python $scriptPath
Remove-Item $scriptPath -Force

# Send package and script
scp -i $Key $localZip "${User}@${HostName}:${RemoteDir}/app.zip"
scp -i $Key scripts/remote-setup.sh "${User}@${HostName}:${RemoteDir}/scripts/"

## Build environment string from JSON object properties
$envPairs = @()
foreach ($p in $EnvMap.PSObject.Properties) {
  $k = $p.Name
  $v = $p.Value -replace '"', '"'  # escape quotes
  $envPairs += "$k=$v"
}
$envStr = $envPairs -join ' '

## Run remote setup: unpack package (using python's zipfile) and run remote-setup.sh with env
$py = "import zipfile,sys; zipfile.ZipFile('app.zip').extractall('.')"
$pyB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
$remoteCmd = "cd ${RemoteDir} && echo ${pyB64} | base64 -d | python3 && ./scripts/remote-setup.sh"
ssh -i $Key "${User}@${HostName}" "${envStr} REMOTE_DIR='${RemoteDir}' bash -lc '${remoteCmd}'"
