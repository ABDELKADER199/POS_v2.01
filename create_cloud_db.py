import sys
sys.path.append(r'd:\Python Desktop\POS_V2')
from repositories.db_connection import DatabaseConnection

# Connect without database first
db = DatabaseConnection()
db.database = "" 
db._connect()

try:
    db.execute("CREATE DATABASE IF NOT EXISTS stocks_cloud CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("Created database stocks_cloud")
except Exception as e:
    print("Error creating database:", e)
