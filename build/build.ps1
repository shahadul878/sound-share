#Requires -Version 5.1
<#
.SYNOPSIS
  Build SoundShare executable and single-file Windows installer.

.PARAMETER VbCablePath
  Path to extracted VBCABLE_Driver_Pack45 folder (default: vendor\VBCABLE_Driver_Pack45).
#>

param(
    [string]$VbCablePath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$VendorDir = Join-Path $Root "vendor"
$VbCablePackDir = Join-Path $VendorDir "VBCABLE_Driver_Pack45"
$VbCableSetup = Join-Path $VbCablePackDir "VBCABLE_Setup_x64.exe"
$DistDir = Join-Path $Root "dist"
$VbCableZipUrl = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
$VbCableZipFile = Join-Path $VendorDir "VBCABLE_Driver_Pack45.zip"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SoundShare Build v1.1" -ForegroundColor Cyan
Write-Host "  by H M Shahadul Islam" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $VendorDir)) {
    New-Item -ItemType Directory -Path $VendorDir | Out-Null
}

# 1. Vendor full VB-Cable driver pack
if ($VbCablePath -and (Test-Path $VbCablePath)) {
    Write-Host "[1/4] Copying VB-Cable driver pack from: $VbCablePath" -ForegroundColor Yellow
    if (Test-Path $VbCablePackDir) { Remove-Item -Recurse -Force $VbCablePackDir }
    Copy-Item -Path $VbCablePath -Destination $VbCablePackDir -Recurse
}

if (-not (Test-Path $VbCableSetup)) {
    Write-Host "[1/4] Preparing VB-Audio Virtual Cable driver pack..." -ForegroundColor Yellow
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
            throw "Downloaded file too small ($zipSize bytes)."
        }
        if (Test-Path $VbCablePackDir) { Remove-Item -Recurse -Force $VbCablePackDir }
        New-Item -ItemType Directory -Path $VbCablePackDir | Out-Null
        Expand-Archive -Path $VbCableZipFile -DestinationPath $VbCablePackDir -Force
        if (-not (Test-Path $VbCableSetup)) {
            throw "VBCABLE_Setup_x64.exe not found in driver pack."
        }
        Write-Host "      Ready: $VbCablePackDir" -ForegroundColor Green
    } catch {
        Write-Host "      FAILED to prepare VB-Cable driver pack." -ForegroundColor Red
        Write-Host "      Copy VBCABLE_Driver_Pack45 to: $VbCablePackDir" -ForegroundColor Red
        Write-Host "      Or run: .\build\build.ps1 -VbCablePath 'C:\path\to\VBCABLE_Driver_Pack45'" -ForegroundColor Red
        Write-Host "      Error: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/4] VB-Cable driver pack found: $VbCablePackDir" -ForegroundColor Green
}

# 2. Install Python deps
Write-Host "[2/4] Installing build dependencies..." -ForegroundColor Yellow
py -m pip install -q -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 3. PyInstaller
Write-Host "[3/4] Building SoundShare.exe (PyInstaller)..." -ForegroundColor Yellow
$keepSetup = Join-Path $DistDir "SoundShare-Setup-1.1.2.exe"
$hadSetup = Test-Path $keepSetup
if (Test-Path $DistDir) {
    Get-ChildItem $DistDir -Exclude "SoundShare-Setup-1.1.2.exe" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
py -m PyInstaller build\soundshare.spec --noconfirm --distpath dist --workpath build\pyi-work
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$ExePath = Join-Path $DistDir "SoundShare.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "      Build failed: SoundShare.exe not found" -ForegroundColor Red
    exit 1
}
Write-Host "      Built: $ExePath" -ForegroundColor Green

# 4. Inno Setup - single-file installer
Write-Host "[4/4] Compiling single-file installer (SoundShare-Setup-1.1.2.exe)..." -ForegroundColor Yellow
$InnoPaths = @(
    $env:INNO_SETUP,
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) }

$Iscc = $InnoPaths | Select-Object -First 1
if (-not $Iscc) {
    Write-Host "      Inno Setup not found. Installing..." -ForegroundColor Yellow
    winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    $InnoPaths = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ }
    $Iscc = $InnoPaths | Select-Object -First 1
}

if (-not $Iscc) {
    Write-Host "      ERROR: Inno Setup required for single .exe installer." -ForegroundColor Red
    Write-Host "      Install from https://jrsoftware.org/isinfo.php then re-run build.ps1" -ForegroundColor Red
    exit 1
}

& $Iscc "installer\soundshare.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$SetupExe = Join-Path $DistDir "SoundShare-Setup-1.1.2.exe"
if (-not (Test-Path $SetupExe)) {
    Write-Host "      ERROR: Installer not created." -ForegroundColor Red
    exit 1
}

$setupSize = [math]::Round((Get-Item $SetupExe).Length / 1MB, 1)
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Single installer: $SetupExe ($setupSize MB)"
Write-Host "  Includes: SoundShare + full VB-Cable driver pack"
Write-Host ""
