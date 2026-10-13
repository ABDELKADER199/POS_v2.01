@echo off
title POS V2 Database Rebuild - Database Engineer Mode
color 0A
echo.
echo === POS V2 Database Rebuild Script ===
echo Starting rebuild process...
echo.
"D:\Python Desktop\.venv\Scripts\python.exe" "D:\Python Desktop\POS_V2\rebuild_database.py"
echo.
echo === Rebuild Complete ===
pause
