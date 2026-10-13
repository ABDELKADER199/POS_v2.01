@echo off
title POS V2 Database Rebuild
color 0A
"D:\Python Desktop\.venv\Scripts\python.exe" "D:\Python Desktop\POS_V2\rebuild_database.py" > "D:\Python Desktop\rebuild_output.txt" 2>&1
echo Done. See rebuild_output.txt
pause
