param([string]$Tag='perfume15-100refs-20261002-recovery')
$ErrorActionPreference='Stop'
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid tag' }
Set-Location -LiteralPath $PSScriptRoot
$taskStatePath=Join-Path $PSScriptRoot ('runtime/resume-'+$Tag+'.json')
try {
    @{status='STARTING';tag=$Tag} | ConvertTo-Json | Set-Content -LiteralPath $taskStatePath -Encoding UTF8
    $taskReady=$false
    try { $null=Invoke-RestMethod 'http://127.0.0.1:8190/system_stats' -TimeoutSec 2; $taskReady=$true } catch {}
    if (!$taskReady) { & (Join-Path $PSScriptRoot 'start_comfy.ps1') }
    $taskDeadline=(Get-Date).AddSeconds(90)
    while (!$taskReady -and (Get-Date) -lt $taskDeadline) {
        try { $null=Invoke-RestMethod 'http://127.0.0.1:8190/system_stats' -TimeoutSec 2; $taskReady=$true } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$taskReady) { throw 'ComfyUI did not become ready; inspect its retained logs' }
    & (Join-Path $PSScriptRoot 'run_matrix.ps1') -Tag $Tag -Rounds 2 -Workers 2
    @{status='RUNNING';tag=$Tag} | ConvertTo-Json | Set-Content -LiteralPath $taskStatePath -Encoding UTF8
} catch {
    @{status='ERROR';tag=$Tag;error_type=$_.Exception.GetType().FullName} | ConvertTo-Json | Set-Content -LiteralPath $taskStatePath -Encoding UTF8
    throw
}
