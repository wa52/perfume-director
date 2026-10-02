param(
    [string]$Tag = 'perfume15-100refs-20261002',
    [int]$Rounds = 2,
    [ValidateSet(1,2)][int]$Workers = 1,
    [string[]]$Ids = @(),
    [string]$Python = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI\.venv\Scripts\python.exe'
)
$ErrorActionPreference='Stop'
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid tag' }
if ($Rounds -lt 1 -or $Rounds -gt 12) { throw 'Rounds must be 1..12' }
if (@($Ids | Where-Object { $_ -notmatch '^[a-zA-Z0-9_-]+$' }).Count) { throw 'Invalid product ID' }
$taskRuntime=Join-Path $PSScriptRoot 'runtime'
$null=New-Item -ItemType Directory -Path $taskRuntime -Force
$taskParameters=@{Tag=$Tag;Rounds=$Rounds;Workers=$Workers;Python=$Python}
if ($Ids.Count) { $taskParameters.Ids=$Ids }
$taskParameters | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRuntime ('matrix-launch-'+$Tag+'.json')) -Encoding UTF8
$taskWorker=Join-Path $taskRuntime 'matrix-launch-worker.ps1'
@'
param([string]$Tag)
$ErrorActionPreference='Stop'
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid tag' }
$taskRoot=Split-Path -Parent $PSScriptRoot
try {
    $taskObject=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('matrix-launch-'+$Tag+'.json')) -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskParameters=@{}
    foreach ($taskProperty in $taskObject.PSObject.Properties) { $taskParameters[$taskProperty.Name]=$taskProperty.Value }
    & (Join-Path $taskRoot 'run_matrix.ps1') @taskParameters
} catch {
    $_.Exception.GetType().FullName | Set-Content -LiteralPath (Join-Path $PSScriptRoot ('matrix-launch-'+$Tag+'.error'))
    exit 1
}
'@ | Set-Content -LiteralPath $taskWorker -Encoding UTF8
# WMI launches outside the caller's process tree; closing an interactive task
# therefore does not terminate its already-authorized batch.
$taskStartup=([wmiclass]'Win32_ProcessStartup').CreateInstance()
$taskStartup.ShowWindow=0
$taskCommand='powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$taskWorker+'" -Tag '+$Tag
$taskLaunch=([wmiclass]'Win32_Process').Create($taskCommand,$PSScriptRoot,$taskStartup)
if ($taskLaunch.ReturnValue -ne 0) { throw ('Could not launch batch: '+$taskLaunch.ReturnValue) }
Write-Output "Independent launcher PID $($taskLaunch.ProcessId). Inspect runtime/matrix-$Tag.stdout.log and runs/matrix/$Tag/state files for actual progress."
