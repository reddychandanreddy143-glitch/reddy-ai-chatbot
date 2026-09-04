import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session
from chatbot import ChatbotEngine
from database import ChatDatabase

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database and chatbot engine
db = ChatDatabase()
bot_engine = ChatbotEngine()

@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)

# --- Authentication Routes ---
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    success, message = db.register_user(username, email, password)
    if success:
        return jsonify({"status": "success", "message": message}), 201
    return jsonify({"status": "error", "message": message}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"status": "error", "message": "Identifier and password required."}), 400

    success, user_data = db.authenticate_user(identifier, password)
    if success:
        session["user"] = user_data
        return jsonify({"status": "success", "user": user_data}), 200
    return jsonify({"status": "error", "message": "Invalid username or password."}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

# --- Admin Monitoring Route ---
@app.route("/admin")
def admin_dashboard():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, session_id, user_query, bot_response, detected_intent, confidence_score, timestamp 
        FROM conversation_logs 
        ORDER BY id DESC LIMIT 50
    """)
    logs = cursor.fetchall()

    cursor.execute("SELECT id, username, email, created_at, last_login FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    return render_template("admin.html", logs=logs, users=users)

# --- Chat API Endpoint ---
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "response": "Invalid request format."}), 400

        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", "default_session")

        if not user_message:
            return jsonify({"status": "warning", "response": "Please enter a valid message."}), 200

        current_user = session.get("user")
        user_id = current_user["id"] if current_user else None
        username = current_user["username"] if current_user else None

        # Generate response using native multi-turn Gemini reasoning engine
        result = bot_engine.get_response(user_message, session_id=session_id)
        bot_reply = result.get("response", "I could not process your query.")
        intent = result.get("intent", "unknown")
        confidence = result.get("confidence", 1.0)

        # Silent server audit logging (retains logs for the admin dashboard without showing a sidebar)
        try:
            db.log_conversation(session_id, user_message, bot_reply, intent, confidence, user_id=user_id, username=username)
        except Exception as log_err:
            print(f"[*] Audit log notice: {log_err}")

        return jsonify({
            "status": "success",
            "response": bot_reply,
            "intent": intent,
            "confidence": confidence,
            "is_logged_in": bool(user_id)
        }), 200

    except Exception as e:
        print(f"[!] Server Error in /chat: {e}")
        return jsonify({"status": "error", "response": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)