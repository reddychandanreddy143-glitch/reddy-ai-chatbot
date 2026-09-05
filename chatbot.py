import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import google.generativeai as genai
from nlp import IntentClassifier

# Check both environment variable names so either one works
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

class ChatbotEngine:
    def __init__(self, intents_path: str = "intents.json"):
        self.classifier = IntentClassifier(intents_path)
        # Store native Gemini chat sessions per session/user
        self.active_chats = {}
        self.api_key = API_KEY
        self.model = None
        self._setup_gemini()

    def _setup_gemini(self):
        # Refresh key in case it was loaded after import
        if not self.api_key:
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

        if not self.api_key:
            print("[!] GEMINI_API_KEY or GOOGLE_API_KEY environment variable not found.")
            return
        try:
            genai.configure(api_key=self.api_key)
            
            system_instruction = (
                "You are Reddy AI, an intelligent, helpful academic and reasoning assistant. "
                "Provide detailed, comprehensive, and well-explained answers using markdown, "
                "bold headers, and bullet points. Never cut off your responses mid-sentence. "
                "Always understand follow-up questions in the context of the conversation."
            )
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            print("[✓] Native Gemini Chat Engine connected.")
        except Exception as e:
            print(f"[!] Gemini Setup Error: {e}")
            self.model = None

    def _get_chat_session(self, session_id: str):
        """Returns the native Gemini chat session, creating one if it doesn't exist."""
        if session_id not in self.active_chats:
            self.active_chats[session_id] = self.model.start_chat(history=[])
        return self.active_chats[session_id]

    def get_response(self, user_query: str, session_id: str = "default_session") -> dict:
        clean_query = user_query.strip()
        if not clean_query:
            return {"response": "Please enter a message.", "intent": "empty", "confidence": 1.0}

        query_lower = clean_query.lower()
        words = query_lower.split()

        # Follow-up trigger words that should go straight to the AI
        follow_up_words = {"it", "this", "that", "them", "these", "roles", "who", "more", "why", "how", "what", "when", "where"}
        is_general_or_followup = any(w in follow_up_words for w in words) or len(words) > 5

        # 1. Check local intents for short specific queries
        if not is_general_or_followup:
            intent, confidence, local_response = self.classifier.match_intent(clean_query)
            if local_response and confidence >= 0.80:
                return {"response": local_response, "intent": intent, "confidence": float(confidence)}

        # 2. Native Gemini Multi-Turn Reasoning
        if not self.model:
            self._setup_gemini()
            if not self.model:
                return {"response": "⚠️ AI Engine offline. Please check API key configuration.", "intent": "error", "confidence": 0.0}

        try:
            chat = self._get_chat_session(session_id)
            response = chat.send_message(clean_query)
            
            if response and response.text:
                return {
                    "response": response.text.strip(),
                    "intent": "gemini_native_chat",
                    "confidence": 0.99
                }
        except Exception as e:
            self.active_chats.pop(session_id, None)
            return {"response": f"⚠️ API Error: {str(e)}", "intent": "error", "confidence": 0.0}

        return {"response": "Could not generate a response. Please try again.", "intent": "unknown", "confidence": 0.0}