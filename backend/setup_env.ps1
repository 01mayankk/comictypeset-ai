# ComicTypeset AI - Backend Virtual Environment Setup
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "=== Setting up ComicTypeset AI Backend Environment ===" -ForegroundColor Cyan

$venvPath = Join-Path $scriptDir ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath..."
    python -m venv .venv
}

$pipExe = Join-Path $venvPath "Scripts\pip.exe"
if (-not (Test-Path $pipExe)) {
    $pipExe = "pip"
}

Write-Host "Upgrading pip and installing requirements..."
& $pipExe install --upgrade pip setuptools wheel
& $pipExe install -r requirements.txt

Write-Host "=== Backend Environment Setup Complete ===" -ForegroundColor Green
Write-Host "Activate with: .\backend\.venv\Scripts\Activate.ps1"
