import sys
import time
from PyQt6.QtWidgets import QApplication
sys.path.append(r'd:\Python Desktop\POS_V2')

from controllers.sync_controller import SyncController
from repositories.db_connection import DatabaseConnection

def test_sync():
    app = QApplication(sys.argv)
    
    # Insert a dummy record into sync_queue
    db = DatabaseConnection()
    db.execute("""
        INSERT INTO sync_queue (table_name, action_type, record_id, data_json, status)
        VALUES ('products', 'INSERT', '9999', '{"id": 9999, "product_name": "Test Product"}', 'pending')
    """)
    db.commit()
    print("Inserted dummy record into sync_queue")
    
    ctrl = SyncController()
    print("Cloud configured?", ctrl.is_cloud_configured())
    
    ctrl.sync_started.connect(lambda: print("Sync Started!"))
    ctrl.sync_finished.connect(lambda s, c, m: print(f"Sync Finished! Success={s}, Count={c}, Msg={m}"))
    ctrl.sync_progress.connect(lambda p, m: print(f"Progress: {p}% - {m}"))
    ctrl.status_changed.connect(lambda c, p, m: print(f"Status: cloud={c}, pending={p}, msg={m}"))
    
    # Start background sync with small interval
    ctrl.start_background_sync(interval_seconds=5)
    
    # Wait for a bit
    print("Waiting 10 seconds for sync to process...")
    import threading
    def quit_app():
        time.sleep(10)
        app.quit()
    threading.Thread(target=quit_app).start()
    
    app.exec()

if __name__ == '__main__':
    test_sync()
