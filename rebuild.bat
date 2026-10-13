@echo off
cd /d "%~dp0"
echo Rebuilding database...
"..\..\venv\Scripts\python.exe" rebuild_database.py
echo Rebuild complete.
pause