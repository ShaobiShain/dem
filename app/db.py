import mysql.connector
DB_CONFIG = {
 "host": "127.0.0.1",
 "port": 3306,
 "user": "root",
 "password": "",
 "database": "shoe2026_pu",
 "use_unicode": True,
 "charset": "utf8mb4",
 "use_pure": True,
}
def get_connection():
 return mysql.connector.connect(**DB_CONFIG)
