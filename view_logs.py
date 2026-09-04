import sqlite3

def display_logs():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, session_id, user_query, bot_response, detected_intent, confidence_score, timestamp 
        FROM conversation_logs 
        ORDER BY id DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print("\n[i] No conversations logged yet.")
        conn.close()
        return

    print("\n" + "="*80)
    print("                      RECENT USER CONVERSATIONS                      ")
    print("="*80)

    for row in reversed(rows):
        log_id, session, query, reply, intent, conf, timestamp = row
        print(f"\n[ID: {log_id}] | Time: {timestamp} | Session: {session}")
        print(f"User Asked : {query}")
        print(f"Bot Replied: {reply[:120]}..." if len(reply) > 120 else f"Bot Replied: {reply}")
        print(f"Intent/Engine: {intent} (Confidence: {conf})")
        print("-" * 80)
        
    conn.close()

if __name__ == "__main__":
    display_logs()