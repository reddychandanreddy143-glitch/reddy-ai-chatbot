import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class ChatDatabase:
    def __init__(self, db_path: str = "chatbot.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables with proper foreign keys and indexes."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Users Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_login DATETIME
                    )
                """)

                # 2. Chat Sessions Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)

                # 3. Conversation Logs Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        user_query TEXT NOT NULL,
                        bot_response TEXT NOT NULL,
                        detected_intent TEXT,
                        confidence_score REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON conversation_logs(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions ON chat_sessions(user_id)")
                
                conn.commit()
                print("[✓] Database schema verified with full conversation persistence.")
        except Exception as e:
            print(f"[!] Database initialization error: {e}")

    # --- User Authentication Methods ---
    def register_user(self, username: str, email: str, password: str) -> tuple[bool, str]:
        hashed_password = generate_password_hash(password)
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (?, ?, ?)
                """, (username.strip(), email.strip().lower(), hashed_password))
                conn.commit()
                return True, "Registration successful!"
        except sqlite3.IntegrityError:
            return False, "Username or Email already registered."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    def authenticate_user(self, identifier: str, password: str) -> tuple[bool, dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, email, password_hash 
                    FROM users 
                    WHERE username = ? OR email = ?
                """, (identifier.strip(), identifier.strip().lower()))
                user = cursor.fetchone()

                if user and check_password_hash(user["password_hash"], password):
                    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
                    conn.commit()
                    return True, {"id": int(user["id"]), "username": user["username"], "email": user["email"]}
                return False, {}
        except Exception as e:
            print(f"[!] Auth error: {e}")
            return False, {}

    # --- Session & History Methods ---
    def ensure_session(self, session_id: str, first_message: str, user_id: int):
        """Creates session title if it doesn't exist, otherwise updates the timestamp."""
        if not user_id:
            return
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT session_id FROM chat_sessions WHERE session_id = ? AND user_id = ?", (session_id, int(user_id)))
                if not cursor.fetchone():
                    title = first_message.strip()
                    if len(title) > 35:
                        title = title[:32] + "..."
                    
                    cursor.execute("""
                        INSERT INTO chat_sessions (session_id, user_id, title)
                        VALUES (?, ?, ?)
                    """, (session_id, int(user_id), title))
                else:
                    cursor.execute("""
                        UPDATE chat_sessions 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE session_id = ? AND user_id = ?
                    """, (session_id, int(user_id)))
                conn.commit()
        except Exception as e:
            print(f"[!] Session ensure error: {e}")

    def log_conversation(self, session_id: str, user_query: str, bot_response: str, 
                         intent: str = "unknown", confidence: float = 1.0, 
                         user_id: int = None, username: str = None):
        """Saves message to DB strictly under the session_id and user_id."""
        if not user_id:
            return  # Guest messages are temporary
            
        try:
            self.ensure_session(session_id, user_query, int(user_id))
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_logs 
                    (session_id, user_id, username, user_query, bot_response, detected_intent, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, int(user_id), username, user_query, bot_response, intent, float(confidence)))
                conn.commit()
        except Exception as e:
            print(f"[!] Logging error: {e}")

    def get_user_sessions(self, user_id: int, limit: int = 40):
        """Retrieves list of saved chat titles for the logged-in user."""
        if not user_id:
            return []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, title, updated_at 
                    FROM chat_sessions 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC LIMIT ?
                """, (int(user_id), limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[!] Sessions fetch error: {e}")
            return []

    def get_session_messages(self, session_id: str, user_id: int):
        """Retrieves all past messages belonging to this specific session."""
        if not user_id:
            return []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_query, bot_response, timestamp 
                    FROM conversation_logs 
                    WHERE session_id = ? AND user_id = ? 
                    ORDER BY id ASC
                """, (session_id, int(user_id)))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[!] Messages fetch error: {e}")
            return []