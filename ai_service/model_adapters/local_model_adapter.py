"""
Local Model Adapter

Adapter for running local pretrained models:
- Bio_ClinicalBERT for clinical NLP
- DistilBERT as lightweight fallback
"""

import os
from typing import Dict, List, Any, Optional

# Try importing transformers
try:
    from transformers import (
        AutoTokenizer, 
        AutoModel, 
        AutoModelForTokenClassification,
        pipeline
    )
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class LocalModelAdapter:
    """
    Adapter for local Hugging Face models.
    
    Supports:
    - Bio_ClinicalBERT for clinical text understanding
    - Token classification for NER
    - Embeddings for similarity search
    """
    
    # Model configurations
    MODELS = {
        "bio_clinical_bert": "emilyalsentzer/Bio_ClinicalBERT",
        "distilbert": "distilbert-base-uncased",
        "ner_disease": "alvaroalon2/biobert_diseases_ner"
    }
    
    def __init__(self, model_name: str = "distilbert"):
        """
        Initialize adapter with specified model.
        
        Args:
            model_name: Key from MODELS dict or HuggingFace model name
        """
        self.model_name = self.MODELS.get(model_name, model_name)
        self._model = None
        self._tokenizer = None
        self._ner_pipeline = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu" if TRANSFORMERS_AVAILABLE else None
    
    def is_available(self) -> bool:
        """Check if transformers is available."""
        return TRANSFORMERS_AVAILABLE
    
    def load_model(self) -> bool:
        """
        Load the model and tokenizer.
        
        Returns:
            True if successful, False otherwise
        """
        if not TRANSFORMERS_AVAILABLE:
            return False
        
        if self._model is not None:
            return True
        
        try:
            print(f"Loading model: {self.model_name}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            
            if self._device == "cuda":
                self._model = self._model.cuda()
            
            self._model.eval()
            return True
        except Exception as e:
            print(f"Failed to load model {self.model_name}: {e}")
            return False
    
    def get_embeddings(self, text: str) -> Optional[List[float]]:
        """
        Get text embeddings using the model.
        
        Args:
            text: Input text
            
        Returns:
            List of embedding floats or None on error
        """
        if not self.load_model():
            return None
        
        try:
            # Tokenize
            inputs = self._tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512,
                padding=True
            )
            
            if self._device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Get embeddings
            with torch.no_grad():
                outputs = self._model(**inputs)
            
            # Use CLS token embedding
            embeddings = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
            return embeddings.tolist()
            
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of entities with text, label, and scores
        """
        if not TRANSFORMERS_AVAILABLE:
            return []
        
        try:
            # Use NER pipeline
            if self._ner_pipeline is None:
                self._ner_pipeline = pipeline(
                    "ner",
                    model=self.MODELS.get("ner_disease", "distilbert-base-uncased"),
                    aggregation_strategy="simple"
                )
            
            results = self._ner_pipeline(text)
            
            return [
                {
                    "text": r["word"],
                    "label": r["entity_group"],
                    "score": float(r["score"]),
                    "start": r["start"],
                    "end": r["end"]
                }
                for r in results
            ]
        except Exception as e:
            print(f"NER error: {e}")
            return []
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        emb1 = self.get_embeddings(text1)
        emb2 = self.get_embeddings(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        import numpy as np
        
        # Cosine similarity
        dot = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot / (norm1 * norm2))
    
    def classify_symptoms(self, text: str, symptom_list: List[str]) -> Dict[str, float]:
        """
        Classify which symptoms are present in text.
        
        Uses embedding similarity to match symptoms.
        
        Args:
            text: Patient description
            symptom_list: List of canonical symptom names
            
        Returns:
            Dict mapping symptom to confidence score
        """
        text_emb = self.get_embeddings(text)
        if text_emb is None:
            return {}
        
        results = {}
        
        for symptom in symptom_list:
            symptom_emb = self.get_embeddings(symptom)
            if symptom_emb:
                import numpy as np
                
                dot = np.dot(text_emb, symptom_emb)
                norm1 = np.linalg.norm(text_emb)
                norm2 = np.linalg.norm(symptom_emb)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = float(dot / (norm1 * norm2))
                    if similarity > 0.5:  # Threshold
                        results[symptom] = similarity
        
        return results


# Singleton instance
_adapter: Optional[LocalModelAdapter] = None

def get_local_adapter() -> LocalModelAdapter:
    """Get or create local model adapter singleton."""
    global _adapter
    if _adapter is None:
        _adapter = LocalModelAdapter()
    return _adapter
