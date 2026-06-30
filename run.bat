@echo off
title SoundShare v1.0
cd /d "%~dp0"
py -m pip install -q -r requirements.txt 2>nul
py launcher.py %*
