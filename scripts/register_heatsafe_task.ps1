param(
    [string]$TaskName = "HeatSafe-Daily-Data-Update",
    [datetime]$RunAt = (Get-Date -Hour 3 -Minute 0 -Second 0)
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$runnerPath = Join-Path $projectRoot "scripts\run_scheduled_update.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Virtual-environment interpreter not found: $pythonPath"
}
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "Scheduled update runner not found: $runnerPath"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "`"$runnerPath`"" `
    -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Refresh HeatSafe weather data, models, and PostgreSQL records daily." `
    -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' for daily execution at $($RunAt.ToString('HH:mm'))."
Write-Host "Logs: $(Join-Path $projectRoot 'logs')"
