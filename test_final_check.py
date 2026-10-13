#!/usr/bin/env python3
import sys
sys.path.insert(0, 'D:\\Python Desktop\\POS_V2')

try:
    from controllers.sync_worker import SyncWorker, SyncWorkerSignals, SyncManager
    print("SyncWorker: OK")
except Exception as e:
    print(f"SyncWorker error: {e}")

try:
    from controllers.sync_controller import SyncController
    print("SyncController: OK")
except Exception as e:
    print(f"SyncController error: {e}")

try:
    from application.services.sync_service_facade import SyncServiceFacade
    print("SyncServiceFacade: OK")
except Exception as e:
    print(f"SyncServiceFacade error: {e}")

try:
    from controllers.backup_controller import BackupController
    print("BackupController: OK")
except Exception as e:
    print(f"BackupController error: {e}")

try:
    from controllers.print_controller import PrintController
    print("PrintController: OK")
except Exception as e:
    print(f"PrintController error: {e}")

print("All imports completed!")
