$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$BackendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$FrontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

Write-Host "Starting the Digital Wardrobe backend..."
$BackendArguments = "-NoExit -ExecutionPolicy Bypass -File `"$BackendScript`""
Start-Process -FilePath "powershell.exe" -ArgumentList $BackendArguments -WorkingDirectory $ProjectRoot

$ApiReady = $false
for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8011/api/health" -TimeoutSec 2
        if ($Health.status -eq "ok") {
            $ApiReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ApiReady) {
    throw "The backend did not become healthy. Read the backend PowerShell window for the exact error."
}

Write-Host "API is healthy. Starting the frontend..."
$FrontendArguments = "-NoExit -ExecutionPolicy Bypass -File `"$FrontendScript`""
Start-Process -FilePath "powershell.exe" -ArgumentList $FrontendArguments -WorkingDirectory $ProjectRoot
Write-Host "Digital Wardrobe is ready at http://localhost:3000"
