import sqlite3

def display_users():
    conn = sqlite3.connect("chatbot.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, email, password_hash, created_at, last_login 
        FROM users 
        ORDER BY id ASC
    """)
    users = cursor.fetchall()

    if not users:
        print("\n[!] No registered users found in database.")
        conn.close()
        return

    print("\n" + "=" * 95)
    print(f"{'ID':<5} | {'Username':<18} | {'Email':<30} | {'Registered (UTC)':<19} | {'Last Login (UTC)'}")
    print("=" * 95)

    for u in users:
        last_log = u["last_login"] if u["last_login"] else "Never"
        print(f"#{u['id']:<4} | {u['username']:<18} | {u['email']:<30} | {u['created_at']:<19} | {last_log}")

    print("-" * 95)
    print(f"Total Users Registered: {len(users)}\n")
    conn.close()

if __name__ == "__main__":
    display_users()