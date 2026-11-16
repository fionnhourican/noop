# ===================================================
# NOOP Windows Collector — One-Click Launcher
# ===================================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting NOOP Windows 11 WHOOP Collector..." -ForegroundColor Cyan
Write-Host "Connecting to Home Lab at https://acer-homelab.tail614bb9.ts.net" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verifying Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting NOOP Collector Agent..." -ForegroundColor Green
Write-Host "(Make sure your WHOOP 4.0 is double-tapped and pulsing blue!)" -ForegroundColor Yellow
Write-Host ""

python -m noop_agent.main
