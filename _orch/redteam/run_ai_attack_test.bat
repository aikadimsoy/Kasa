@echo off
chcp 65001 >nul
title AI Atak Test Standardi (yetkili)
cd /d "D:\kasa\_orch\redteam"
set "PY=C:\Users\REDACTED-USER\AppData\Local\Python\pythoncore-3.14-64\python.exe"

echo ==============================================
echo   KASA - AI Atak Test Standardi (yetki kapisi)
echo ==============================================
echo.
set /p AITEST_USER=Kullanici adi [erhan_redteam]:
if "%AITEST_USER%"=="" set AITEST_USER=erhan_redteam
set /p AITEST_PASS=Parola:
echo.

"%PY%" ai_attack_test.py --config ai_test_config.json --report ai_test_report.md

echo.
echo ----------------------------------------------
echo  Rapor  : ai_test_report.md
echo  Sonuc  : ai_test_results.json
echo ----------------------------------------------
set AITEST_PASS=
pause
