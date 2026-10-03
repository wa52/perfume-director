# Run clothing only after the already submitted category tests and watch recovery.
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskDeadline=(Get-Date).AddHours(8)
do {
    $taskSummary=Get-Content 'samples/categories/categories-recovery-20261003/summary.json' -Raw -Encoding UTF8|ConvertFrom-Json
    $taskOther=@($taskSummary|Where-Object {$_.product_category -in @('footwear','beverage','skincare')})
    $taskWatchRecovery=Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'powershell' -and $_.CommandLine -like '*resume_watch_after_categories.ps1*'}
    $taskBusy=$false
    foreach($taskFile in Get-ChildItem runtime/director-jobs -Filter state.json -Recurse -File){
        if((Get-Content $taskFile.FullName -Raw -Encoding UTF8|ConvertFrom-Json).status -eq 'RUNNING'){$taskBusy=$true}
    }
    if($taskOther.Count -eq 3 -and !@($taskOther|Where-Object {$_.status -in @('RUNNING','QUEUED')}).Count -and !$taskWatchRecovery -and !$taskBusy){break}
    if((Get-Date) -gt $taskDeadline){throw 'Previous category tests still active; clothing deployment not performed'}
    Start-Sleep -Seconds 10
} while($true)
& '.\start_comfy.ps1' -Port 8191 -Restart *> runtime/clothing-deploy.log
if($LASTEXITCODE){throw 'Clothing deployment failed'}
$taskReady=$false
for($taskTry=0;$taskTry -lt 60;$taskTry++){
    try{$taskInfo=Invoke-RestMethod 'http://127.0.0.1:8191/object_info/ClothingDirectorLoop' -TimeoutSec 2;if($taskInfo.ClothingDirectorLoop){$taskReady=$true;break}}catch{}
    Start-Sleep -Seconds 2
}
if(!$taskReady){throw 'Clothing node did not become ready'}
$taskWorkflowFolder='runtime/user/default/workflows/服装海报'
New-Item -ItemType Directory -Path $taskWorkflowFolder -Force|Out-Null
Copy-Item workflows/clothing/*.ui.json -Destination $taskWorkflowFolder -Force
& 'D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI (1)\ComfyUI\.venv\Scripts\python.exe' -u run_category_matrix.py --tag clothing-pilot-20261003 --categories menswear womenswear *> runtime/clothing-matrix.log
if($LASTEXITCODE){throw 'Clothing matrix runner failed; inspect runtime/clothing-matrix.log'}
