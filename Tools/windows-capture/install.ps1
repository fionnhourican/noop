# ==============================================================================
# NOOP Windows Collector — Automatic Startup Installer
# Creates a Task Scheduler job running under the user's interactive session at logon.
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ServerUrl = "https://your-server-name.your-tailnet.ts.net/api/v1",
    [string]$IngestionToken = "",
    [string]$TaskName = "NOOP_HomeLab_Collector"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "NOOP Windows 11 Collector — Automatic Startup Installer" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Validate environment
$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python 3.12+ was not found on PATH. Please install Python first."
    exit 1
}

$PythonwExe = Join-Path (Split-Path $PythonExe) "pythonw.exe"
if (-not (Test-Path $PythonwExe)) {
    $PythonwExe = $PythonExe
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDataNoop = Join-Path $env:LOCALAPPDATA "NOOP"
$LogsDir = Join-Path $AppDataNoop "logs"

# 2. Create secure AppData directory
if (-not (Test-Path $AppDataNoop)) {
    New-Item -ItemType Directory -Path $AppDataNoop -Force | Out-Null
    Write-Host "Created $AppDataNoop" -ForegroundColor Green
}
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Restrict folder access to current user and Administrators (DACL security)
try {
    $Acl = Get-Acl $AppDataNoop
    $Acl.SetAccessRuleProtection($true, $false)
    $CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $RuleUser = New-Object System.Security.AccessControl.FileSystemAccessRule($CurrentUser, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $RuleAdmin = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $Acl.AddAccessRule($RuleUser)
    $Acl.AddAccessRule($RuleAdmin)
    Set-Acl -Path $AppDataNoop -AclObject $Acl
    Write-Host "Secured $AppDataNoop permissions to current user only." -ForegroundColor Green
} catch {
    Write-Warning "Could not tighten ACL on $AppDataNoop: $_"
}

# 3. Store API credentials securely in Windows Credential Manager
if ($IngestionToken) {
    Write-Host "Saving Ingestion Token into Windows Credential Manager..." -ForegroundColor Yellow
    cmdkey /generic:NOOP_HomeLab_Ingestion /user:collector /pass:$IngestionToken | Out-Null
    Write-Host "Credentials secured under target: NOOP_HomeLab_Ingestion" -ForegroundColor Green
}

# 4. Copy configuration
$ConfigFile = Join-Path $AppDataNoop "config.yaml"
$LocalConfig = Join-Path $ScriptDir "config.yaml"
if (Test-Path $LocalConfig) {
    Copy-Item -Path $LocalConfig -Destination $ConfigFile -Force
    Write-Host "Copied existing config to $ConfigFile" -ForegroundColor Green
} elseif (-not (Test-Path $ConfigFile)) {
    $DefaultConfig = Join-Path $ScriptDir "config.example.yaml"
    if (Test-Path $DefaultConfig) {
        Copy-Item -Path $DefaultConfig -Destination $ConfigFile
        (Get-Content $ConfigFile) -replace "https://your-server-name.your-tailnet.ts.net/api/v1", $ServerUrl | Set-Content $ConfigFile
        Write-Host "Generated config: $ConfigFile" -ForegroundColor Green
    }
}

# 5. Register Task Scheduler job for interactive logon
Write-Host "Registering scheduled task '$TaskName' for logon..." -ForegroundColor Yellow

$Action = New-ScheduledTaskAction -Execute $PythonwExe -Argument "-m noop_agent.main" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "NOOP Home Lab Windows 11 WHOOP 4.0 BLE Collector" | Out-Null

Write-Host "Successfully registered scheduled task '$TaskName'." -ForegroundColor Green
Write-Host "The collector will start automatically when you log on, or run now with:" -ForegroundColor Cyan
Write-Host "Start-ScheduledTask -TaskName $TaskName" -ForegroundColor White
