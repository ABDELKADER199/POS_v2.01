import sys
import threading
import time
sys.path.append(r'd:\Python Desktop\POS_V2')
from repositories.db_connection import DatabaseConnection

db = DatabaseConnection()

def worker(worker_id):
    try:
        print(f"Worker {worker_id} starting...")
        res = db.fetch_all("SELECT 1 as val")
        print(f"Worker {worker_id} fetched: {res}")
        time.sleep(1)
        res2 = db.fetch_all("SELECT 2 as val")
        print(f"Worker {worker_id} fetched again: {res2}")
    except Exception as e:
        print(f"Worker {worker_id} Error:", e)

# Test single thread first
print("Main thread:")
print(db.fetch_all("SELECT 'main' as val"))

# Test threads
threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
for t in threads: t.start()
for t in threads: t.join()

print("All done.")
