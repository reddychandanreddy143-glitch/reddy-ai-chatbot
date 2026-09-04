import sqlite3

def view_my_data():
    conn = sqlite3.connect("chatbot.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ensure missing columns are added if viewing an older DB structure
    cursor.execute("PRAGMA table_info(conversation_logs)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "username" not in columns:
        cursor.execute("ALTER TABLE conversation_logs ADD COLUMN username TEXT DEFAULT 'Guest'")
        conn.commit()
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE conversation_logs ADD COLUMN user_id INTEGER")
        conn.commit()

    print("\n" + "="*80)
    print("                      REGISTERED USER ACCOUNTS                      ")
    print("="*80)
    try:
        cursor.execute("SELECT id, username, email, created_at, last_login FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("No registered users found.")
        else:
            for u in users:
                print(f"ID: #{u['id']} | Username: {u['username']} | Email: {u['email']}")
                print(f"Account Created : {u['created_at']}")
                print(f"Last Login Time : {u['last_login']}")
                print("-" * 80)
    except Exception as e:
        print(f"Error reading users: {e}")

    print("\n" + "="*80)
    print("                      MY SEARCH & CHAT ACTIVITY                      ")
    print("="*80)
    try:
        cursor.execute("""
            SELECT id, username, user_query, bot_response, detected_intent, timestamp 
            FROM conversation_logs 
            ORDER BY id DESC LIMIT 20
        """)
        logs = cursor.fetchall()

        if not logs:
            print("No activity logs recorded yet.")
        else:
            for log in reversed(logs):
                username = log['username'] if log['username'] else "Guest"
                print(f"[{log['timestamp']}] User: {username} (Log #{log['id']})")
                print(f"Prompt Sent : {log['user_query']}")
                print(f"Engine/Tag  : {log['detected_intent']}")
                
                resp_snippet = log['bot_response']
                if len(resp_snippet) > 120:
                    resp_snippet = resp_snippet[:120].replace('\n', ' ') + "..."
                print(f"AI Response : {resp_snippet}")
                print("-" * 80)
    except Exception as e:
        print(f"Error reading conversation logs: {e}")

    conn.close()

if __name__ == "__main__":
    view_my_data()