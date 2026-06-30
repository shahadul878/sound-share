#Requires -Version 5.1
<#
.SYNOPSIS
  Build SoundShare executable and Windows installer.

.DESCRIPTION
  Downloads VB-Audio Virtual Cable, builds PyInstaller exe, compiles Inno Setup installer.
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VendorDir = Join-Path $Root "vendor"
$DistDir = Join-Path $Root "dist"
$VbCableZipUrl = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
$VbCableZipFile = Join-Path $VendorDir "VBCABLE_Driver_Pack45.zip"
$VbCableFile = Join-Path $VendorDir "VBCABLE_Setup_x64.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SoundShare Build v1.0" -ForegroundColor Cyan
Write-Host "  by H M Shahadul Islam" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Vendor VB-Cable
if (-not (Test-Path $VendorDir)) {
    New-Item -ItemType Directory -Path $VendorDir | Out-Null
}

if (-not (Test-Path $VbCableFile)) {
    Write-Host "[1/4] Downloading VB-Audio Virtual Cable driver pack..." -ForegroundColor Yellow
    try {
        if (-not (Test-Path $VbCableZipFile)) {
            $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($curl) {
                & curl.exe -L -o $VbCableZipFile $VbCableZipUrl
            } else {
                Invoke-WebRequest -Uri $VbCableZipUrl -OutFile $VbCableZipFile -UseBasicParsing
            }
        }
        $zipSize = (Get-Item $VbCableZipFile).Length
        if ($zipSize -lt 100000) {
            throw "Downloaded file too small ($zipSize bytes) - expected driver pack ZIP."
        }
        Expand-Archive -Path $VbCableZipFile -DestinationPath $VendorDir -Force
        if (-not (Test-Path $VbCableFile)) {
            throw "VBCABLE_Setup_x64.exe not found after extracting ZIP."
        }
        Write-Host "      Ready: $VbCableFile" -ForegroundColor Green
    } catch {
        Write-Host "      FAILED to prepare VB-Cable." -ForegroundColor Red
        Write-Host "      Download from https://vb-audio.com/Cable/" -ForegroundColor Red
        Write-Host "      Extract VBCABLE_Setup_x64.exe to: $VendorDir" -ForegroundColor Red
        Write-Host "      Error: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/4] VB-Cable installer found in vendor/" -ForegroundColor Green
}

# 2. Install Python deps
Write-Host "[2/4] Installing build dependencies..." -ForegroundColor Yellow
py -m pip install -q -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 3. PyInstaller
Write-Host "[3/4] Building SoundShare.exe (PyInstaller)..." -ForegroundColor Yellow
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}
py -m PyInstaller build\soundshare.spec --noconfirm --distpath dist --workpath build\pyi-work
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ExePath = Join-Path $DistDir "SoundShare.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "      Build failed: SoundShare.exe not found" -ForegroundColor Red
    exit 1
}
Write-Host "      Built: $ExePath" -ForegroundColor Green

# 4. Inno Setup installer
Write-Host "[4/4] Compiling Windows installer..." -ForegroundColor Yellow
$InnoPaths = @(
    $env:INNO_SETUP,
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) }

$Iscc = $InnoPaths | Select-Object -First 1
if (-not $Iscc) {
    Write-Host "      Inno Setup not found. Creating portable package instead..." -ForegroundColor Yellow
    $PackageDir = Join-Path $DistDir "SoundShare-Complete"
    if (Test-Path $PackageDir) { Remove-Item -Recurse -Force $PackageDir }
    New-Item -ItemType Directory -Path $PackageDir | Out-Null
    Copy-Item $ExePath (Join-Path $PackageDir "SoundShare.exe")
    Copy-Item $VbCableFile (Join-Path $PackageDir "VBCABLE_Setup_x64.exe")
    Copy-Item (Join-Path $Root "installer\Install-SoundShare.ps1") (Join-Path $PackageDir "Install-SoundShare.ps1")
    Copy-Item (Join-Path $Root "installer\Install-SoundShare.bat") (Join-Path $PackageDir "Install-SoundShare.bat")
    Copy-Item (Join-Path $Root "installer\ABOUT.txt") (Join-Path $PackageDir "ABOUT.txt")
    Copy-Item (Join-Path $Root "installer\WELCOME.txt") (Join-Path $PackageDir "README.txt")
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  BUILD COMPLETE (portable package)" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Portable exe:  $ExePath"
    Write-Host "  Full package:  $PackageDir"
    Write-Host ""
    Write-Host "  End users: Right-click Install-SoundShare.ps1 -> Run with PowerShell (Admin)"
    Write-Host "  Or install Inno Setup and re-run for SoundShare-Setup-1.0.0.exe"
    Write-Host ""
    exit 0
}

& $Iscc "installer\soundshare.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$SetupExe = Join-Path $DistDir "SoundShare-Setup-1.0.0.exe"
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Portable:  $ExePath"
Write-Host "  Installer: $SetupExe"
Write-Host ""
