@echo off
title Final HyperPOS V2 Exe Build After Fix
color 0A
cd /d "D:\Python Desktop\POS_V2"

echo.
echo === Final Exe Build (After purchase invoice fix) ===
echo Building HyperPOS V2.exe (onefile, windowed)...
echo.

"D:\Python Desktop\.venv\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "HyperPOS_V2" ^
  --add-data ".env;." ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "mysql.connector.locales" ^
  --hidden-import "mysql.connector.locales.eng" ^
  main.py > "rebuild_final.log" 2>&1

echo Build process completed.
echo Checking result...
if exist "dist\HyperPOS_V2.exe" (
    echo SUCCESS: Executable built successfully!
    dir "dist\HyperPOS_V2.exe" | findstr "HyperPOS"
) else (
    echo FAILED - Check rebuild_final.log
)
echo.
pause