$ErrorActionPreference = 'Stop'
$deskRoot = Split-Path -Parent $PSScriptRoot
$deskPidFile = Join-Path $deskRoot '.private-fx/server.pid'
if (-not (Test-Path -LiteralPath $deskPidFile)) {
    Write-Output 'No recorded private desk process.'
    exit 0
}
$deskProcessId = [int][System.IO.File]::ReadAllText($deskPidFile)
$deskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $deskProcessId"
if (-not $deskProcess) {
    Write-Output 'The recorded private desk process has already stopped.'
    exit 0
}
if ($deskProcess.CommandLine -notmatch 'src\.private_desk\.cli\s+serve') {
    throw 'Process identity changed; refusing to stop a different process.'
}
Stop-Process -Id $deskProcessId
Write-Output 'Private desk stopped.'
