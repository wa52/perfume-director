param(
    [string]$Tag = 'perfume15-100refs-20261002',
    [int]$Rounds = 2,
    [ValidateSet(1,2)][int]$Workers = 2,
    [string[]]$Ids = @(),
    [string]$Python = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI\.venv\Scripts\python.exe'
)
$ErrorActionPreference='Stop'
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Tag must contain only letters, numbers, underscores and hyphens' }
if ($Rounds -lt 1 -or $Rounds -gt 12) { throw 'Rounds must be1..12' }
$taskRuntime=Join-Path $PSScriptRoot 'runtime'
$taskPidFile=Join-Path $taskRuntime ('matrix-'+$Tag+'.pid')
if (Test-Path -LiteralPath $taskPidFile) {
    $taskRunnerPid=[int](Get-Content -LiteralPath $taskPidFile)
    $taskExisting=Get-CimInstance Win32_Process -Filter "ProcessId = $taskRunnerPid"
    if ($taskExisting -and $taskExisting.CommandLine.Contains('test_product_matrix.py') -and $taskExisting.CommandLine.Contains($Tag)) {
        throw 'This matrix runner is already active; inspect its saved state instead of submitting twice'
    }
}
$taskConfig=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.local.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskKey=[Environment]::GetEnvironmentVariable($taskConfig.api_key_env,'Process')
if (!$taskKey) { $taskKey=[Environment]::GetEnvironmentVariable($taskConfig.api_key_env,'User') }
if (!$taskKey) { throw 'Configured API key environment variable is missing' }
[Environment]::SetEnvironmentVariable($taskConfig.api_key_env,$taskKey,'Process')
$null=Invoke-RestMethod -Uri ($taskConfig.comfy_url+'/system_stats') -TimeoutSec 5
$taskScript=Join-Path $PSScriptRoot 'test_product_matrix.py'
$taskArgs=@(('"'+$taskScript+'"'),'--tag',$Tag,'--rounds',"$Rounds",'--workers',"$Workers",'--wait-for-100')
if ($Ids.Count) {
    if (@($Ids | Where-Object { $_ -notmatch '^[a-zA-Z0-9_-]+$' }).Count) { throw 'Invalid product ID' }
    $taskArgs+=@('--ids')+$Ids
}
$taskRunner=Start-Process -FilePath $Python -ArgumentList $taskArgs -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskRuntime ('matrix-'+$Tag+'.stdout.log')) `
    -RedirectStandardError (Join-Path $taskRuntime ('matrix-'+$Tag+'.stderr.log'))
$taskRunner.Id | Set-Content -LiteralPath $taskPidFile
Write-Output "Matrix running: $Tag; PID $($taskRunner.Id). Completed directions are reused on resume."
