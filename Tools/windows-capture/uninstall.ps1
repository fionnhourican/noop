# ==============================================================================
# NOOP Windows Collector — Uninstallation Script
# Stops running process, removes Task Scheduler job, and deletes stored credentials.
# ==============================================================================

[CmdletBinding()]
param (
    [string]$TaskName = "NOOP_HomeLab_Collector",
    [switch]$RemoveData
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "NOOP Windows 11 Collector — Uninstallation" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Stop and remove scheduled task
try {
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($Task) {
        Write-Host "Stopping task '$TaskName'..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed task '$TaskName'." -ForegroundColor Green
    }
} catch {
    Write-Warning "Could not unregister scheduled task: $_"
}

# 2. Kill running python processes named noop_agent.main
Get-Process | Where-Object { $_.CommandLine -like "*noop_agent.main*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. Remove Windows Credential Manager entry
try {
    cmdkey /delete:NOOP_HomeLab_Ingestion 2>$null | Out-Null
    Write-Host "Removed credentials from Windows Credential Manager." -ForegroundColor Green
} catch {}

# 4. Optional data removal
if ($RemoveData) {
    $AppDataNoop = Join-Path $env:LOCALAPPDATA "NOOP"
    if (Test-Path $AppDataNoop) {
        Remove-Item -Recurse -Force $AppDataNoop
        Write-Host "Deleted data directory: $AppDataNoop" -ForegroundColor Green
    }
} else {
    Write-Host "Local SQLite database preserved in %LOCALAPPDATA%\NOOP. (Use -RemoveData to wipe)." -ForegroundColor Yellow
}

Write-Host "Uninstallation complete!" -ForegroundColor Cyan
