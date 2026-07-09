@echo off
REM KASA Guvenlik Test-Duzelt Dongusu — standalone baslatici (SIFIR-TOKEN)
REM Kullanim:
REM   run_loop.bat            -> tum panoyu kosar (guard'li tam-oto)
REM   run_loop.bat --dry-run  -> yalniz test eder, duzenleme yapmaz
REM   run_loop.bat --job authz-c5c7c8
setlocal
set KASA_PY=C:\Users\REDACTED-USER\AppData\Local\Python\pythoncore-3.14-64\python.exe
set VENV=D:\AgentPool\model_factory\venv312\Scripts\python.exe
echo [KASA] Guvenlik dongusu baslatiliyor...
"%VENV%" "%~dp0loop_runner.py" %*
echo.
echo [KASA] Bitti. Journal: %~dp0logs\loop_journal.md
pause
