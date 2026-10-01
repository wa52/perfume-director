param(
    [string]$ComfyRoot = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI',
    [string]$ModelsRoot = 'D:\Comfy-Desktop\ComfyUI-Shared\models',
    [int]$Port = 8190,
    [switch]$Restart
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot 'runtime'
$taskConfigPath = Join-Path $projectRoot 'config.local.json'
if (Test-Path -LiteralPath $taskConfigPath) {
    $taskKeyName = (Get-Content -LiteralPath $taskConfigPath -Raw | ConvertFrom-Json).api_key_env
    if ($taskKeyName -and ![Environment]::GetEnvironmentVariable($taskKeyName, 'Process')) {
        $taskSavedKey = [Environment]::GetEnvironmentVariable($taskKeyName, 'User')
        if ($taskSavedKey) { [Environment]::SetEnvironmentVariable($taskKeyName, $taskSavedKey, 'Process') }
    }
}
if ($Restart -and (Test-Path -LiteralPath (Join-Path $runtimeRoot 'comfy.pid'))) {
    $taskPid = [int](Get-Content -LiteralPath (Join-Path $runtimeRoot 'comfy.pid'))
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $taskPid"
    if ($taskProcess) {
        if (!$taskProcess.CommandLine.Contains($runtimeRoot) -or !$taskProcess.CommandLine.Contains((Join-Path $ComfyRoot 'main.py'))) {
            throw 'Saved PID does not belong to this project ComfyUI; refusing to stop it'
        }
        $queue = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/queue" -TimeoutSec 3
        if ($queue.queue_running.Count -or $queue.queue_pending.Count) { throw 'ComfyUI queue is busy; wait before restarting' }
        if ($queue -and (Test-Path -LiteralPath (Join-Path $runtimeRoot 'director-jobs'))) {
            foreach ($stateFile in (Get-ChildItem -LiteralPath (Join-Path $runtimeRoot 'director-jobs') -Filter state.json -Recurse -File)) {
                $jobState = Get-Content -LiteralPath $stateFile.FullName -Raw | ConvertFrom-Json
                if ($jobState.status -eq 'RUNNING') { throw 'A director loop is running; wait before restarting' }
            }
        }
        Stop-Process -Id $taskPid -Force
        Wait-Process -Id $taskPid -Timeout 10 -ErrorAction SilentlyContinue
        $taskStopDeadline = (Get-Date).AddSeconds(10)
        do {
            $taskStillServing = $false
            try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 1; $taskStillServing = $true } catch { }
            if ($taskStillServing) { Start-Sleep -Milliseconds 250 }
        } while ($taskStillServing -and (Get-Date) -lt $taskStopDeadline)
        if ($taskStillServing) { throw 'Project ComfyUI has not stopped; refusing to reuse the old service' }
    }
}
try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/PerfumeDirectorLoop" -TimeoutSec 2
    if ($ready.PerfumeDirectorLoop) { Write-Output "Project ComfyUI already ready at port $Port"; exit 0 }
} catch { }
$portInUse = $false
try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/system_stats" -TimeoutSec 2; $portInUse = $true } catch { }
if ($portInUse) { throw 'ComfyUI is running without the new loop node; use start_comfy.ps1 -Restart when the queue is idle' }
$nodeRoot = Join-Path $runtimeRoot 'custom_nodes\perfume_director'
New-Item -ItemType Directory -Path $nodeRoot -Force | Out-Null
foreach ($folder in @('user','input','output','temp')) {
    New-Item -ItemType Directory -Path (Join-Path $runtimeRoot $folder) -Force | Out-Null
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'comfy_node\__init__.py') -Destination (Join-Path $nodeRoot '__init__.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'poster.py') -Destination (Join-Path $nodeRoot 'poster.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'reference_store.py') -Destination (Join-Path $nodeRoot 'reference_store.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'check_background.py') -Destination (Join-Path $nodeRoot 'check_background.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'quality.py') -Destination (Join-Path $nodeRoot 'quality.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'concepts.py') -Destination (Join-Path $nodeRoot 'concepts.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'comfy_node\jobs.py') -Destination (Join-Path $nodeRoot 'jobs.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'comfy_node\web') -Destination $nodeRoot -Recurse -Force
@{project_root = $projectRoot} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $nodeRoot 'project.json') -Encoding utf8
$pythonPath = Join-Path $ComfyRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'ComfyUI Python environment missing' }
$arguments = @('"' + (Join-Path $ComfyRoot 'main.py') + '"',
    '--base-directory', '"' + $runtimeRoot + '"',
    '--models-directory', '"' + $ModelsRoot + '"',
    '--extra-model-paths-config', '"' + (Join-Path $projectRoot 'extra_model_paths.local.yaml') + '"',
    '--database-url', '"sqlite:///' + (Join-Path $runtimeRoot 'user\comfyui.db').Replace('\','/') + '"',
    '--listen', '127.0.0.1', '--port', "$Port", '--disable-api-nodes', '--lowvram', '--bf16-text-enc',
    '--disable-all-custom-nodes', '--whitelist-custom-nodes', 'perfume_director', 'ComfyUI-GGUF')
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $runtimeRoot 'comfy.stdout.log') -RedirectStandardError (Join-Path $runtimeRoot 'comfy.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $runtimeRoot 'comfy.pid')
Write-Output "ComfyUI started: PID $($process.Id), http://127.0.0.1:$Port (logs in runtime)"
