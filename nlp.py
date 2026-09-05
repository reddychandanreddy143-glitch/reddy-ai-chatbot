import os
import json
import random
import numpy as np
import google.generativeai as genai

# Use the same environment variable already set on Render
API_KEY = os.environ.get("GEMINI_API_KEY", "")

class IntentClassifier:
    def __init__(self, intents_path: str = "intents.json"):
        self.intents_path = intents_path
        self.intents_data = []
        self.patterns = []
        self.pattern_to_intent = []
        self.embedded_patterns = None
        
        # Configure Gemini API for embeddings
        if API_KEY:
            genai.configure(api_key=API_KEY)
            
        self._load_and_encode_intents()

    def _get_embedding(self, text: str, task_type: str = "retrieval_query") -> np.ndarray:
        """Fetches vector embeddings from Gemini API without running heavy local models."""
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type=task_type
            )
            return np.array(result["embedding"], dtype=np.float32)
        except Exception as e:
            print(f"[!] Embedding error for text '{text}': {e}")
            return None

    def _load_and_encode_intents(self):
        """Loads intents from JSON and generates vector embeddings via Gemini API."""
        if not os.path.exists(self.intents_path):
            raise FileNotFoundError(f"Intents file not found at: {self.intents_path}")

        with open(self.intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.intents_data = data.get("intents", [])

        self.patterns = []
        self.pattern_to_intent = []

        for intent in self.intents_data:
            for pattern in intent.get("patterns", []):
                self.patterns.append(pattern.lower().strip())
                self.pattern_to_intent.append(intent)

        if self.patterns:
            print(f"[*] Pre-computing Gemini embeddings for {len(self.patterns)} intent patterns...")
            embeddings = []
            for pattern in self.patterns:
                emb = self._get_embedding(pattern, task_type="retrieval_document")
                if emb is not None:
                    embeddings.append(emb)
                else:
                    embeddings.append(np.zeros(768, dtype=np.float32))
            
            self.embedded_patterns = np.array(embeddings, dtype=np.float32)
            print("[✓] Intent pattern embeddings cached in memory.")

    def match_intent(self, user_query: str) -> tuple[str, float, str]:
        """Compares user query vectors against local intent clusters using numpy cosine similarity."""
        if not self.patterns or self.embedded_patterns is None or len(self.embedded_patterns) == 0:
            return "unknown", 0.0, ""

        query_emb = self._get_embedding(user_query.lower().strip(), task_type="retrieval_query")
        if query_emb is None:
            return "unknown", 0.0, ""

        # Compute cosine similarity using pure numpy (uses < 1 MB RAM)
        dot_products = np.dot(self.embedded_patterns, query_emb)
        norms = np.linalg.norm(self.embedded_patterns, axis=1) * np.linalg.norm(query_emb)
        cos_scores = np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms != 0)

        best_match_idx = int(np.argmax(cos_scores))
        confidence = float(cos_scores[best_match_idx])

        if confidence >= 0.78:
            matched_intent = self.pattern_to_intent[best_match_idx]
            response = random.choice(matched_intent.get("responses", [""]))
            return matched_intent.get("tag", "unknown"), confidence, response

        return "unknown", confidence, ""