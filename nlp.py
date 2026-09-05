import os
import json
import random
import numpy as np
import google.generativeai as genai

# Check both standard environment variable keys
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

class IntentClassifier:
    def __init__(self, intents_path: str = "intents.json"):
        self.intents_path = intents_path
        self.intents_data = []
        self.patterns = []
        self.pattern_to_intent = []
        self.embedded_patterns = None
        self.api_available = False
        
        # Configure Gemini API if key is present
        if API_KEY:
            try:
                genai.configure(api_key=API_KEY)
                self.api_available = True
            except Exception as e:
                print(f"[!] GenAI configuration error: {e}")
                self.api_available = False
            
        self._load_and_encode_intents()

    def _get_embedding(self, text: str, task_type: str = "retrieval_query") -> np.ndarray:
        """Fetches vector embeddings from Gemini API with graceful fallback."""
        if not self.api_available:
            return None

        # Try supported embedding models in order
        candidate_models = ["text-embedding-004", "models/text-embedding-004", "embedding-001"]
        for m in candidate_models:
            try:
                result = genai.embed_content(
                    model=m,
                    content=text,
                    task_type=task_type
                )
                if "embedding" in result:
                    return np.array(result["embedding"], dtype=np.float32)
            except Exception:
                continue
        return None

    def _load_and_encode_intents(self):
        """Loads intents from JSON and generates vector embeddings or initializes pattern lists."""
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

        if self.patterns and self.api_available:
            print(f"[*] Pre-computing Gemini embeddings for {len(self.patterns)} intent patterns...")
            embeddings = []
            success_count = 0
            for pattern in self.patterns:
                emb = self._get_embedding(pattern, task_type="retrieval_document")
                if emb is not None:
                    embeddings.append(emb)
                    success_count += 1
                else:
                    embeddings.append(np.zeros(768, dtype=np.float32))
            
            if success_count > 0:
                self.embedded_patterns = np.array(embeddings, dtype=np.float32)
                print(f"[✓] Successfully encoded {success_count}/{len(self.patterns)} patterns.")
            else:
                print("[!] Embeddings unavailable; using keyword fallback.")
                self.embedded_patterns = None
        else:
            print("[*] Running intent classifier in keyword fallback mode.")
            self.embedded_patterns = None

    def match_intent(self, user_query: str) -> tuple[str, float, str]:
        """Compares user query against intents via embeddings or substring matching."""
        clean_query = user_query.lower().strip()
        if not clean_query or not self.patterns:
            return "unknown", 0.0, ""

        # 1. Vector similarity search if embeddings are initialized
        if self.embedded_patterns is not None:
            query_emb = self._get_embedding(clean_query, task_type="retrieval_query")
            if query_emb is not None:
                dot_products = np.dot(self.embedded_patterns, query_emb)
                norms = np.linalg.norm(self.embedded_patterns, axis=1) * np.linalg.norm(query_emb)
                cos_scores = np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms != 0)

                best_match_idx = int(np.argmax(cos_scores))
                confidence = float(cos_scores[best_match_idx])

                if confidence >= 0.78:
                    matched_intent = self.pattern_to_intent[best_match_idx]
                    response = random.choice(matched_intent.get("responses", [""]))
                    return matched_intent.get("tag", "unknown"), confidence, response

        # 2. Resilient Keyword/Substring Matching Fallback
        for idx, pattern in enumerate(self.patterns):
            if pattern == clean_query or pattern in clean_query or clean_query in pattern:
                matched_intent = self.pattern_to_intent[idx]
                response = random.choice(matched_intent.get("responses", [""]))
                return matched_intent.get("tag", "unknown"), 0.90, response

        return "unknown", 0.0, ""