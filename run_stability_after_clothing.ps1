$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskDeadline=(Get-Date).AddHours(16)
do {
    $taskSummary=Get-Content 'samples/categories/clothing-pilot-20261003/summary.json' -Raw -Encoding UTF8|ConvertFrom-Json
    $taskClothing=@($taskSummary|Where-Object {$_.product_category -in @('menswear','womenswear')})
    $taskBusy=$false
    foreach($taskFile in Get-ChildItem runtime/director-jobs -Filter state.json -Recurse -File){
        if((Get-Content $taskFile.FullName -Raw -Encoding UTF8|ConvertFrom-Json).status -eq 'RUNNING'){$taskBusy=$true}
    }
    if($taskClothing.Count -eq 2 -and !@($taskClothing|Where-Object {$_.status -in @('RUNNING','QUEUED')}).Count -and !$taskBusy){break}
    if((Get-Date) -gt $taskDeadline){throw 'Earlier tests still active; stability retest not started'}
    Start-Sleep -Seconds 10
} while($true)
& '.\start_comfy.ps1' -Port 8191 -Restart *> runtime/stability-deploy.log
if($LASTEXITCODE){throw 'Stability deployment failed'}
$taskReady=$false
for($taskTry=0;$taskTry -lt 60;$taskTry++){
    try{$taskInfo=Invoke-RestMethod 'http://127.0.0.1:8191/object_info/ClothingDirectorLoop' -TimeoutSec 2;if($taskInfo.ClothingDirectorLoop){$taskReady=$true;break}}catch{}
    Start-Sleep -Seconds 2
}
if(!$taskReady){throw 'Stability service not ready'}
& 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI\.venv\Scripts\python.exe' -u run_category_matrix.py --tag categories-stability-retest-20261003 --manifest assets/products/stability-products.json *> runtime/stability-matrix.log
if($LASTEXITCODE){throw 'Stability runner failed; inspect runtime/stability-matrix.log'}
