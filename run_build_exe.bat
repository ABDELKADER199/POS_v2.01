@echo off
title HyperPOS V2 - Exe Builder
color 0A
cd /d "D:\Python Desktop\POS_V2"
echo.
echo === Step 1: Installing PyInstaller ===
"D:\Python Desktop\.venv\Scripts\python.exe" -m pip install pyinstaller
echo.
echo === Step 2: Building HyperPOS V2 Exe (onefile, windowed) ===
echo This may take several minutes...
"D:\Python Desktop\.venv\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "HyperPOS_V2" ^
  --add-data ".env;." ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "mysql.connector.locales.eng" ^
  main.py
echo.
echo === Build Complete ===
if exist "dist\HyperPOS_V2.exe" (
    echo Executable built successfully!
    echo Location: D:\Python Desktop\POS_V2\dist\HyperPOS_V2.exe
) else (
    echo Executable build may have failed. Check build output above.
)
echo.
pause