@echo off
REM KASA egitim delta-gozcusu — zamanlanmis gorev sarmali (makine-nazik: gunde 1x, hafif).
cd /d d:\kasa
py d:\kasa\_orch\training\watch_delta.py >> d:\kasa\_orch\training\logs\watch.log 2>&1
