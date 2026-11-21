$ErrorActionPreference = 'Stop'
$deskRoot = Split-Path -Parent $PSScriptRoot
$deskState = Join-Path $deskRoot '.private-fx'
$deskPipeline = Join-Path $deskRoot 'pipeline'
New-Item -ItemType Directory -Path $deskState -Force | Out-Null
$deskListening = Get-NetTCPConnection -State Listen -LocalPort 8765 -ErrorAction SilentlyContinue
if ($deskListening) {
    Write-Output 'Port 8765 already has a listener. Check the private desk before starting another.'
    exit 0
}
$deskPython = (Get-Command python).Source
$deskProc = Start-Process -FilePath $deskPython -ArgumentList '-m','src.private_desk.cli','serve' -WorkingDirectory $deskPipeline -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $deskState 'server.log') -RedirectStandardError (Join-Path $deskState 'server.err')
[System.IO.File]::WriteAllText((Join-Path $deskState 'server.pid'), [string]$deskProc.Id)
for ($deskAttempt = 0; $deskAttempt -lt 15; $deskAttempt++) {
    if ($deskProc.HasExited) { throw 'Private desk failed to start. Inspect .private-fx/server.err.' }
    try {
        $deskResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8765/' -TimeoutSec 2
        if ($deskResponse.StatusCode -eq 200 -and $deskResponse.Content.Contains('Private desk')) {
            Write-Output 'Private desk is ready: http://127.0.0.1:8765. Login password: .private-fx/access.txt.'
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 1
}
throw 'Private desk health check failed. Inspect .private-fx/server.err.'
