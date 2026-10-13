@echo off
title Rebuilding HyperPOS V2 Exe After Fix
color 0E
cd /d "D:\Python Desktop\POS_V2"

echo.
echo === Rebuilding HyperPOS V2 Exe (After purchase invoice fix) ===
echo This may take 3-7 minutes...
echo.

"D:\Python Desktop\.venv\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "HyperPOS_V2" ^
  --add-data ".env;." ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "mysql.connector.locales" ^
  --hidden-import "mysql.connector.locales.eng" ^
  main.py > "rebuild_after_fix.log" 2>&1

echo Build process completed.
echo Checking result...
if exist "dist\HyperPOS_V2.exe" (
    echo SUCCESS: Executable rebuilt!
    dir "dist\HyperPOS_V2.exe" /-c
) else (
    echo FAILED - Check rebuild_after_fix.log
)
echo.
pause