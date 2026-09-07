$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "frontend")
Write-Host "Starting Digital Wardrobe at http://localhost:3000"
npm run dev
