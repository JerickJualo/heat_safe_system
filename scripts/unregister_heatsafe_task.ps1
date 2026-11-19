param([string]$TaskName = "HeatSafe-Daily-Data-Update")

$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
Write-Host "Unregistered scheduled task '$TaskName'."
