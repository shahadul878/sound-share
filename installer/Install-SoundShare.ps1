#Requires -RunAsAdministrator
<#
.SYNOPSIS
  SoundShare one-click installer (VB-Cable + app + shortcuts).

.DESCRIPTION
  Used when Inno Setup is not available on the build machine, or as a
  portable distribution folder. Run as Administrator.
#>

$ErrorActionPreference = "Stop"
$AppName = "SoundShare"
$AppVersion = "1.1.1"
$InstallDir = Join-Path $env:ProgramFiles $AppName
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExeSource = Join-Path $ScriptDir "SoundShare.exe"
$VbCable = Join-Path $ScriptDir "VBCABLE_Driver_Pack45"
$VbCableSetup = Join-Path $VbCable "VBCABLE_Setup_x64.exe"
$Port = 8765

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SoundShare Setup v$AppVersion" -ForegroundColor Cyan
Write-Host "  by H M Shahadul Islam" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ExeSource)) {
    Write-Host "ERROR: SoundShare.exe not found next to this script." -ForegroundColor Red
    exit 1
}

# VB-Cable
$vbInstalled = Test-Path "HKLM:\SOFTWARE\VB-Audio\Cable" -ErrorAction SilentlyContinue
if (-not $vbInstalled) {
    $vbInstalled = Test-Path "HKLM:\SOFTWARE\WOW6432Node\VB-Audio\Cable" -ErrorAction SilentlyContinue
}

if (-not $vbInstalled) {
    if (-not (Test-Path $VbCableSetup)) {
        Write-Host "ERROR: VBCABLE_Driver_Pack45 folder not found (needs VBCABLE_Setup_x64.exe)." -ForegroundColor Red
        exit 1
    }
    Write-Host "[1/4] Installing VB-Audio Virtual Cable..." -ForegroundColor Yellow
    $proc = Start-Process -FilePath $VbCableSetup -WorkingDirectory $VbCable -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-" -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Host "WARNING: VB-Cable installer exit code $($proc.ExitCode)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[1/4] VB-Audio Virtual Cable already installed." -ForegroundColor Green
}

# App files
Write-Host "[2/4] Installing SoundShare..." -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}
Copy-Item -Path $ExeSource -Destination (Join-Path $InstallDir "SoundShare.exe") -Force
$about = Join-Path $ScriptDir "ABOUT.txt"
if (Test-Path $about) {
    Copy-Item -Path $about -Destination (Join-Path $InstallDir "ABOUT.txt") -Force
}

# Firewall
Write-Host "[3/4] Configuring Windows Firewall (port $Port)..." -ForegroundColor Yellow
netsh advfirewall firewall delete rule name="SoundShare" 2>$null | Out-Null
netsh advfirewall firewall add rule name="SoundShare" dir=in action=allow protocol=TCP localport=$Port | Out-Null

# Shortcuts
Write-Host "[4/4] Creating shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("CommonPrograms")) $AppName
if (-not (Test-Path $StartMenu)) {
    New-Item -ItemType Directory -Path $StartMenu | Out-Null
}

$lnkDesktop = $WshShell.CreateShortcut((Join-Path $Desktop "$AppName.lnk"))
$lnkDesktop.TargetPath = Join-Path $InstallDir "SoundShare.exe"
$lnkDesktop.WorkingDirectory = $InstallDir
$lnkDesktop.Description = "Stream PC audio to devices on your network"
$lnkDesktop.Save()

$lnkStart = $WshShell.CreateShortcut((Join-Path $StartMenu "$AppName.lnk"))
$lnkStart.TargetPath = Join-Path $InstallDir "SoundShare.exe"
$lnkStart.WorkingDirectory = $InstallDir
$lnkStart.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Launch SoundShare from your Desktop."
Write-Host "Share the Network URL with phones on your Wi-Fi."
Write-Host ""
$launch = Read-Host "Launch SoundShare now? (Y/n)"
if ($launch -ne "n" -and $launch -ne "N") {
    Start-Process (Join-Path $InstallDir "SoundShare.exe")
}
