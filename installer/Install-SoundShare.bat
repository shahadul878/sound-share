@echo off
title SoundShare Complete Package Installer
echo.
echo ========================================
echo   SoundShare Setup
echo   by H M Shahadul Islam
echo ========================================
echo.
echo This will install VB-Audio Virtual Cable and SoundShare.
echo Administrator permission is required.
echo.
pause
powershell -ExecutionPolicy Bypass -File "%~dp0Install-SoundShare.ps1"
pause
