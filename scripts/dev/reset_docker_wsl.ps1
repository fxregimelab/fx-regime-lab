#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Uninstall Docker Desktop, remove WSL distributions, reset WSL optional features, then reinstall WSL + Docker Desktop.

.DESCRIPTION
  DESTRUCTIVE: Removes all local WSL distro data and Docker containers/images/volumes.
  Run from an elevated PowerShell (Run as administrator).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\dev\reset_docker_wsl.ps1 -Yes

.EXAMPLE
  # Cleanup only (no reinstall):
  powershell -ExecutionPolicy Bypass -File .\scripts\dev\reset_docker_wsl.ps1 -Yes -NoReinstall
#>
param(
    [Parameter(Mandatory = $false)]
    [switch]$Yes,

    [switch]$NoReinstall
)

$ErrorActionPreference = 'Continue'

if (-not $Yes) {
    Write-Host @"

This script will:
  - Uninstall Docker Desktop (winget)
  - Shut down WSL and unregister ALL distributions (data loss)
  - Disable and re-enable Windows optional features: WSL + VirtualMachinePlatform
  - Unless -NoReinstall: install WSL kernel/update, then Docker Desktop via winget

Re-run with -Yes to proceed.

"@ -ForegroundColor Yellow
    exit 1
}

function Invoke-Step {
    param([string]$Message, [scriptblock]$Action)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
    & $Action
    # Ignore winget "package not installed" and DISM reboot-pending
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 3010 -and $LASTEXITCODE -ne -1978335212) {
        Write-Host "Step exited with code $LASTEXITCODE (3010 = reboot required is OK)" -ForegroundColor DarkYellow
    }
}

# wsl.exe -l often hangs when the subsystem is wedged; never block forever
function Invoke-WslTimed {
    param(
        [string]$Arguments,
        [int]$TimeoutSec = 25
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "wsl.exe"
    $psi.Arguments = $Arguments
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    try {
        $p = [System.Diagnostics.Process]::Start($psi)
        if (-not $p.WaitForExit($TimeoutSec * 1000)) {
            try { $p.Kill() } catch { }
            Write-Host "wsl $Arguments timed out after ${TimeoutSec}s (subsystem may be stuck)." -ForegroundColor DarkYellow
            return $null
        }
        $out = $p.StandardOutput.ReadToEnd()
        $err = $p.StandardError.ReadToEnd()
        if ($err) { $err | Write-Host }
        return $out
    } catch {
        Write-Host "wsl $Arguments failed: $_" -ForegroundColor DarkYellow
        return $null
    }
}

# --- Stop Docker ---
Invoke-Step "Stopping Docker processes and services" {
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(Docker Desktop|DockerDesktop|com\.docker|vpnkit)' } | Stop-Process -Force -ErrorAction SilentlyContinue
    @("com.docker.service", "docker") | ForEach-Object {
        $s = Get-Service -Name $_ -ErrorAction SilentlyContinue
        if ($s) { Stop-Service -Name $_ -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep -Seconds 2
}

# --- Uninstall Docker Desktop ---
Invoke-Step "Uninstalling Docker Desktop (winget)" {
    winget uninstall -e --id Docker.DockerDesktop --silent --accept-source-agreements 2>&1 | Write-Host
    if ($LASTEXITCODE -eq -1978335212) { Write-Host "Docker Desktop package not found via winget (may already be removed)." }
}

# --- WSL shutdown + unregister all (must run while WSL is still installed) ---
Invoke-Step "WSL shutdown" {
    wsl.exe --shutdown 2>&1 | Write-Host
    Start-Sleep -Seconds 3
}

Invoke-Step "Unregister all WSL distributions" {
    $names = @()
    $listOut = Invoke-WslTimed -Arguments "-l -q" -TimeoutSec 25
    if ($listOut) {
        $names = @(
            $listOut -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
        )
    }
    foreach ($n in $names) {
        if ($n -match '^(Windows Subsystem|Copyright|Usage)') { continue }
        Write-Host "Unregistering: $n"
        $null = Invoke-WslTimed -Arguments "--unregister `"$n`"" -TimeoutSec 120
    }
    if (-not $names -or $names.Count -eq 0) {
        Write-Host "No distributions listed or wsl -l timed out. REBOOT, then run dism/ reinstall steps or re-run this script." -ForegroundColor Yellow
    }
}

# --- Remove Store WSL app after distros are gone ---
Invoke-Step "Uninstalling Windows Subsystem for Linux (Store package) if present" {
    winget uninstall -e --id Microsoft.WindowsSubsystemLinux --silent --accept-source-agreements 2>&1 | Write-Host
    if ($LASTEXITCODE -eq -1978335212) { Write-Host "WSL Store package not listed in winget (OK)." }
}

# --- Optional features: disable then enable (clean slate) ---
Invoke-Step "Disable WSL + VirtualMachinePlatform optional features" {
    dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart 2>&1 | Write-Host
    dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart 2>&1 | Write-Host
}

Invoke-Step "Enable WSL + VirtualMachinePlatform optional features" {
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart 2>&1 | Write-Host
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart 2>&1 | Write-Host
}

if ($NoReinstall) {
    Write-Host @"

NoReinstall specified. Done with cleanup.
REBOOT Windows now, then (optional) run again without -NoReinstall to install Docker + WSL.

"@ -ForegroundColor Green
    exit 0
}

# --- Reinstall WSL (kernel + default distro prompt handled by Microsoft installer) ---
Invoke-Step "WSL install / update" {
    wsl.exe --update 2>&1 | Write-Host
    # Install default Ubuntu if no distro; --no-distribution only updates kernel
    $hasDistro = $false
    try {
        $chk = & wsl.exe -l -q 2>&1
        $hasDistro = $chk -and ($chk | Where-Object { $_.Trim() })
    } catch { }
    if (-not $hasDistro) {
        Write-Host "Installing default WSL distribution (Ubuntu). This can take several minutes." -ForegroundColor Yellow
        wsl.exe --install -d Ubuntu --no-launch 2>&1 | Write-Host
    }
}

# --- Reinstall Docker Desktop ---
Invoke-Step "Installing Docker Desktop (winget)" {
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements 2>&1 | Write-Host
}

Write-Host @"

Done.
1) RESTART Windows if DISM or installers asked for a reboot (check messages above).
2) After reboot: open Docker Desktop once and finish setup (WSL 2 backend).
3) In PowerShell:  wsl -l -v   should list your distro; Docker should show Engine running.

"@ -ForegroundColor Green
