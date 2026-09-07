$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
if ($ProjectRoot -notmatch '^([A-Za-z]):\\(.*)$') {
    throw "The project must be on a Windows drive that WSL mounts under /mnt."
}
$Drive = $Matches[1].ToLowerInvariant()
$RelativePath = $Matches[2].Replace('\', '/')
$WslProject = "/mnt/$Drive/$RelativePath"

Write-Host "Starting Digital Wardrobe API at http://127.0.0.1:8011"
wsl.exe -d Ubuntu -- bash -lc "set -e; source `$HOME/miniconda3/etc/profile.d/conda.sh; export PYTHONNOUSERSITE=1; conda activate digital-wardrobe; cd '$WslProject/backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8011"
