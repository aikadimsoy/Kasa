@echo off
REM KASA Guvenlik Test-Duzelt Dongusu — standalone baslatici (SIFIR-TOKEN)
REM Kullanim:
REM   run_loop.bat            -> tum panoyu kosar (guard'li tam-oto)
REM   run_loop.bat --dry-run  -> yalniz test eder, duzenleme yapmaz
REM   run_loop.bat --job authz-c5c7c8
setlocal
REM Yorumlayicilar env ile verilir (sabit kullanici/harici-proje yollari kaldirildi).
if not defined KASA_PY set "KASA_PY=python"
if not defined VENV set "VENV=%KASA_PY%"
echo [KASA] Guvenlik dongusu baslatiliyor...
"%VENV%" "%~dp0loop_runner.py" %*
echo.
echo [KASA] Bitti. Journal: %~dp0logs\loop_journal.md
pause
