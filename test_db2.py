import sys
sys.path.insert(0, '.')
from repositories.db_connection import DatabaseConnection

db = DatabaseConnection()
print(f"Connection: {db.conn}")
print(f"Host: {db.host}, DB: {db.database}")

# Test creating the table directly
try:
    db.execute("""
        CREATE TABLE IF NOT EXISTS `schema_migrations` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            version VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64),
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    db.commit()
    print("Table created and committed")
except Exception as e:
    print(f"Error creating table: {e}")
    db.rollback()

# Check if it exists now
result = db.fetch_all("SHOW TABLES LIKE 'schema_migrations'")
print('schema_migrations table exists:', len(result) > 0)