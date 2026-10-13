#!/usr/bin/env python3
# Test running the app with venv python
import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    import PyQt6
    print(f"PyQt6: {PyQt6.__version__}")
except Exception as e:
    print(f"PyQt6 error: {e}")

try:
    import mysql.connector
    print("mysql.connector: OK")
except Exception as e:
    print(f"mysql.connector error: {e}")

try:
    import bcrypt
    print("bcrypt: OK")
except Exception as e:
    print(f"bcrypt error: {e}")

# Check main imports
sys.path.insert(0, '.')
try:
    from controllers.sync_controller import SyncController
    print("SyncController: OK")
except Exception as e:
    print(f"SyncController error: {e}")

try:
    from controllers.backup_controller import BackupController
    print("BackupController: OK")
except Exception as e:
    print(f"BackupController error: {e}")
