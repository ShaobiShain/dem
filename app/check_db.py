from db import get_connection


def main():
    conn = None
    cur = None
    try:
        conn = get_connection()  # Проверяем, что параметры подключения корректны
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"OK: подключение успешно, SELECT 1 -> {result[0]}")
    except Exception as e:
        print("ERROR:", e)
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    main()
