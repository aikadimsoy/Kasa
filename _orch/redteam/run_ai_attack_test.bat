@echo off
chcp 65001 >nul
title AI Atak Test Standardi (yetkili)
cd /d "%~dp0"
REM Yorumlayici: KASA_PY ile gecersiz kilinabilir (sabit kullanici yolu kaldirildi).
if not defined KASA_PY set "KASA_PY=python"
set "PY=%KASA_PY%"

echo ==============================================
echo   KASA - AI Atak Test Standardi (yetki kapisi)
echo ==============================================
echo.
set /p AITEST_USER=Kullanici adi [redteam_user]:
if "%AITEST_USER%"=="" set AITEST_USER=redteam_user
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
