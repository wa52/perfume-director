param(
    [string]$ComfyRoot = 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI',
    [string]$ModelsRoot = 'D:\Comfy-Desktop\ComfyUI-Shared\models',
    [int]$Port = 8190
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot 'runtime'
try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/object_info/PerfumePosterSpecRender" -TimeoutSec 2
    if ($ready.PerfumePosterSpecRender) { Write-Output "Project ComfyUI already ready at port $Port"; exit 0 }
} catch { }
$nodeRoot = Join-Path $runtimeRoot 'custom_nodes\perfume_director'
New-Item -ItemType Directory -Path $nodeRoot -Force | Out-Null
foreach ($folder in @('user','input','output','temp')) {
    New-Item -ItemType Directory -Path (Join-Path $runtimeRoot $folder) -Force | Out-Null
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'comfy_node\__init__.py') -Destination (Join-Path $nodeRoot '__init__.py') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'poster.py') -Destination (Join-Path $nodeRoot 'poster.py') -Force
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
