@echo off
cd /d "D:\Python Desktop\POS_V2"
echo Starting build in background...
start /b "" "D:\Python Desktop\.venv\Scripts\python.exe" -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "HyperPOS_V2" ^
  --add-data ".env;." ^
  --hidden-import "PyQt6.sip" ^
  --hidden-import "mysql.connector.locales" ^
  --hidden-import "mysql.connector.locales.eng" ^
  main.py > "build_full.log" 2>&1
echo Build started in background, check build_full.log for progress
exit