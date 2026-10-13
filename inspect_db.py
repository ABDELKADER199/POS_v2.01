import sys
sys.path.append(r'd:\Python Desktop\POS_V2')
from repositories.db_connection import DatabaseConnection
db = DatabaseConnection()

tables_to_check = ['schema_migrations', 'authorized_devices', 'financial_ledger', 'orders']
for tbl in tables_to_check:
    print(f'=== {tbl} ===')
    try:
        cols = db.fetch_all(f'SHOW COLUMNS FROM {tbl}')
        for c in cols:
            field = c['Field']
            typ = c['Type']
            null = c['Null']
            default = c['Default']
            print(f"  {field:25s} {typ:30s} Null={null:3s} Default={default}")
    except Exception as e:
        print(f'  ERROR: {e}')
    print()
