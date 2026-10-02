param(
    [string]$Tag = 'perfume15-100refs-20261002',
    [switch]$ReportOnly,
    [string]$Python = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI\.venv\Scripts\python.exe'
)
function Invoke-MatrixCompletion {
$ErrorActionPreference='Stop'
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid tag' }
Set-Location -LiteralPath $PSScriptRoot
$taskRuntime=Join-Path $PSScriptRoot 'runtime'
$taskPidFile=Join-Path $taskRuntime ('matrix-'+$Tag+'.pid')
$taskRunnerPid=[int](Get-Content -LiteralPath $taskPidFile)
$taskDeadline=(Get-Date).AddHours(4)
while ((Get-Process -Id $taskRunnerPid -ErrorAction SilentlyContinue) -and (Get-Date) -lt $taskDeadline) {
    & $Python matrix_report.py --tag $Tag
    Start-Sleep -Seconds 45
}
if (Get-Process -Id $taskRunnerPid -ErrorAction SilentlyContinue) { throw 'Baseline still running at supervisor deadline; no duplicate work submitted' }
& $Python matrix_report.py --tag $Tag
if ($ReportOnly) { Write-Output 'Report export finished; no new generation submitted'; return }
$taskProducts=(Get-Content assets/products/test-products-15.json -Raw -Encoding UTF8 | ConvertFrom-Json).products
$taskRetryIds=@()
foreach ($taskProduct in $taskProducts) {
    $taskResultPath=Join-Path $PSScriptRoot ('runs/matrix/'+$Tag+'/'+$taskProduct.id+'/result.json')
    $taskComplete=$false
    if (Test-Path -LiteralPath $taskResultPath) {
        $taskResult=Get-Content -LiteralPath $taskResultPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $taskComplete=$taskResult.status -eq 'COMPLETED' -and @($taskResult.directions | Where-Object { $_.selected }).Count -eq 4
    }
    if (!$taskComplete) { $taskRetryIds+=$taskProduct.id }
}
if ($taskRetryIds.Count -gt 0) {
    $taskConfig=Get-Content config.local.json -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskKey=[Environment]::GetEnvironmentVariable($taskConfig.api_key_env,'Process')
    if (!$taskKey) { $taskKey=[Environment]::GetEnvironmentVariable($taskConfig.api_key_env,'User') }
    if (!$taskKey) { throw 'API key unavailable; recovery not submitted' }
    [Environment]::SetEnvironmentVariable($taskConfig.api_key_env,$taskKey,'Process')
    $taskRecoveryTag=$Tag+'-recovery'
    $taskRecoveryPidPath=Join-Path $taskRuntime ('matrix-'+$taskRecoveryTag+'.pid')
    if (Test-Path -LiteralPath $taskRecoveryPidPath) {
        $taskRecoveryPid=[int](Get-Content -LiteralPath $taskRecoveryPidPath)
        $taskActiveRecovery=Get-CimInstance Win32_Process -Filter "ProcessId = $taskRecoveryPid"
        if ($taskActiveRecovery -and $taskActiveRecovery.CommandLine.Contains('test_product_matrix.py') -and $taskActiveRecovery.CommandLine.Contains($taskRecoveryTag)) {
            Write-Output 'Recovery already running; no duplicate generation submitted'
            return
        }
    }
    # Check the recovery process before restarting: its queue can be empty
    # while the Director is calling the vision API.
    & (Join-Path $PSScriptRoot 'start_comfy.ps1') -Restart
    & $Python test_product_matrix.py --tag $taskRecoveryTag --rounds 2 --workers 2 --wait-for-100 --ids @taskRetryIds
    if ($LASTEXITCODE -ne 0) { throw 'Recovery runner failed; inspect retained logs' }
    & $Python matrix_report.py --tag $taskRecoveryTag
}
Write-Output 'Baseline and bounded failure-recovery pass finished. Inspect actual statuses; completion is not aesthetic approval.'
}

if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid tag' }
$taskLockPath=Join-Path $PSScriptRoot ('runtime/matrix-completion-'+$Tag+'.lock')
$taskLock=[System.IO.File]::Open($taskLockPath,[System.IO.FileMode]::OpenOrCreate,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
try { Invoke-MatrixCompletion } finally { $taskLock.Dispose() }
