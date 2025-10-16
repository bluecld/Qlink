param()

# Delegate to deploy so packaging/unzip and restart are consistent
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1
