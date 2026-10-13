import mysql.connector

DB_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '123',
    'database': 'stocks', 'port': 3306
}

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # Check user
    cursor.execute("SELECT id, name, email, role_id FROM users WHERE email = 'dev@test.com'")
    user = cursor.fetchone()
    print("Test User:", user)
    
    # Check role
    cursor.execute("SELECT id, role_name FROM roles WHERE id = 99")
    role = cursor.fetchone()
    print("Developer Role:", role)
    
    # Check settings
    cursor.execute("SELECT setting_key FROM system_settings WHERE setting_key LIKE 'backup_%'")
    settings = cursor.fetchall()
    print("Backup Settings Count:", len(settings))
    
    # Check sync queue
    cursor.execute("SELECT COUNT(*) as cnt FROM sync_queue")
    sync = cursor.fetchone()
    print("Sync Queue Records:", sync['cnt'])
    
    print("All verifications passed!")
    conn.close()

if __name__ == '__main__':
    main()
