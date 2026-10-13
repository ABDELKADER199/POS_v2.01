@echo off
title Building HyperPOS V2 Executable
color 0A
cd /d "D:\Python Desktop\POS_V2"

echo.
echo === Building HyperPOS V2 Exe ===
echo This may take 5-15 minutes...
echo.

"D:\Python Desktop\.venv\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "HyperPOS_V2" ^
  --add-data ".env;." ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "mysql.connector.locales" ^
  --hidden-import "mysql.connector.locales.eng" ^
  main.py > "D:\Python Desktop\build_output.txt" 2>&1

if exist "dist\HyperPOS_V2.exe" (
    echo.
    echo === BUILD SUCCESSFUL ===
    echo Executable: dist\HyperPOS_V2.exe
    echo Size: 
    dir "dist\HyperPOS_V2.exe" | findstr "HyperPOS"
) else (
    echo.
    echo === BUILD FAILED - Check build_output.txt ===
)
pause