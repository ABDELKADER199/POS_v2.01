import sys
sys.path.insert(0, 'd:/Python Desktop/POS_V2')
from repositories.db_connection import DatabaseConnection
db = DatabaseConnection()

for t in ['suppliers','purchase_invoices','purchase_items','expenses','promotions','financial_ledger','invoices','customers','treasury','product_inventory']:
    db.cursor.execute(f'DESCRIBE {t}')
    cols = db.cursor.fetchall()
    print(f'=== {t} ===')
    for c in cols:
        print(f"  {c['Field']} {c['Type']}")
