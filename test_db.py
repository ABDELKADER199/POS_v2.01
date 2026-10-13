import sys
sys.path.insert(0, '.')
from repositories.db_connection import DatabaseConnection

db = DatabaseConnection()
try:
    result = db.fetch_all("SHOW TABLES LIKE 'schema_migrations'")
    print('schema_migrations table exists:', len(result) > 0)
    if result:
        print(result)
except Exception as e:
    print('Error:', e)

result = db.fetch_all("SHOW TABLES LIKE 'sync_queue'")
print('sync_queue table exists:', len(result) > 0)