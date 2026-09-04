import os
import json
import torch
from sentence_transformers import SentenceTransformer, util

class IntentClassifier:
    def __init__(self, intents_path: str = "intents.json"):
        self.intents_path = intents_path
        self.intents_data = []
        self.patterns = []
        self.pattern_to_intent = []
        self.embedded_patterns = None
        
        # Load sentence transformer model safely onto CPU
        print("[*] Loading Transformer model 'all-MiniLM-L6-v2' (CPU-optimized)...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        
        self._load_and_encode_intents()

    def _load_and_encode_intents(self):
        """Loads intents from JSON and generates vector embeddings for local caching."""
        if not os.path.exists(self.intents_path):
            raise FileNotFoundError(f"Intents file not found at: {self.intents_path}")

        with open(self.intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.intents_data = data.get("intents", [])

        self.patterns = []
        self.pattern_to_intent = []

        for intent in self.intents_data:
            for pattern in intent["patterns"]:
                self.patterns.append(pattern.lower().strip())
                self.pattern_to_intent.append(intent)

        if self.patterns:
            print(f"[*] Encoding {len(self.patterns)} intent patterns into vector embeddings...")
            # Compute embeddings matching user queries semantically
            self.embedded_patterns = self.model.encode(self.patterns, convert_to_tensor=True)

    def match_intent(self, user_query: str) -> tuple[str, float, str]:
        """Compares user query vectors against local intent clusters using cosine similarity."""
        if not self.patterns or self.embedded_patterns is None:
            return "unknown", 0.0, ""

        query_embedding = self.model.encode(user_query.lower().strip(), convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, self.embedded_patterns)[0]
        
        # Find highest similarity match index
        best_match_idx = int(torch.argmax(cos_scores).item())
        confidence = float(cos_scores[best_match_idx].item())

        if confidence >= 0.78:
            matched_intent = self.pattern_to_intent[best_match_idx]
            import random
            response = random.choice(matched_intent["responses"])
            return matched_intent["tag"], confidence, response

        return "unknown", confidence, ""