"""
SapBERT Helper
===============

Adapter for finding the best matching canonical symptom using SapBERT embeddings.
Model: cambridgeltl/SapBERT-from-PubMedBERT-fulltext

This model is fine-tuned for medical entity alignment, making it superior for generic
semantic similarity in the biomedical domain.
"""

import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

class SapBERTHelper:
    """
    Helper to normalize medical terms using SapBERT embeddings.
    """
    
    def __init__(self, use_api: bool = False, hf_token: str = None):
        self.use_api = use_api
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        self.tokenizer = None
        self.model = None
        
        # Cache for candidate embeddings
        self.candidate_embeddings = {}
        
        if not self.use_api:
            self._init_local_model()
            
    def _init_local_model(self):
        try:
            from transformers import AutoTokenizer, AutoModel
            logger.info(f"Loading {MODEL_NAME} locally...")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.model = AutoModel.from_pretrained(MODEL_NAME)
            logger.info("✅ SapBERT loaded successfully")
        except Exception as e:
            logger.warning(f"SapBERT local load failed: {e}. Switching to API/Fallback.")
            self.use_api = True

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for a single text string."""
        if self.use_api and self.hf_token:
            return self._get_embedding_api(text)
        
        if self.model and self.tokenizer:
            return self._get_embedding_local(text)
            
        return None

    def _get_embedding_local(self, text: str) -> Optional[np.ndarray]:
        try:
            import torch
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                outputs = self.model(**inputs)
                # SapBERT uses CLS token as the representation
                cls_embedding = outputs.last_hidden_state[:, 0, :].numpy()
                return cls_embedding.flatten()
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            return None

    def _get_embedding_api(self, text: str) -> Optional[np.ndarray]:
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            payload = {"inputs": text}
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                # The API usually returns a list of lists if multiple inputs, or list of floats for feature extraction
                # But for 'feature-extraction' pipeline defaults, it might return full sequence.
                # Usually simpler to use InferenceClient if available, but let's stick to simple request for now.
                # Warning: The hosted inference API for this model might be 'fill-mask' by default or 'feature-extraction'.
                # We assume feature-extraction is available.
                data = response.json()
                # If data is list of list of list (batch, seq, dim)
                if isinstance(data, list) and isinstance(data[0], list) and isinstance(data[0][0], list):
                     # Take first item, first token (CLS)
                     return np.array(data[0][0])
                # If data is list of list (seq, dim) - simplified
                elif isinstance(data, list) and isinstance(data[0], list):
                     return np.array(data[0]) 
                return np.array(data)
            else:
                logger.warning(f"API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"API embedding failed: {e}")
            return None

    def cache_candidates(self, candidates: List[str]):
        """Pre-compute embeddings for a list of candidate symptoms."""
        self.candidate_embeddings = {}
        for cand in candidates:
            emb = self.get_embedding(cand)
            if emb is not None:
                self.candidate_embeddings[cand] = emb
    
    def normalize(self, text: str, candidates: List[str] = None, threshold: float = 0.65) -> Optional[str]:
        """
        Find best matching candidate for the input text.
        If candidates provided, uses them. Otherwise uses cached candidates.
        """
        query_emb = self.get_embedding(text)
        if query_emb is None:
            return None
        
        best_score = -1
        best_cand = None
        
        # Determine which set of candidates to check
        # If candidates are passed, we might fallback to computing them on fly or checking cache
        # For efficiency, assume candidates are usually the cached ones.
        target_map = self.candidate_embeddings
        if candidates:
            # If candidates provided are different from cache, compute specifically
            # This is slow if list is long. Ideally rely on cache.
            # Check if we have them in cache
            target_map = {}
            for c in candidates:
                if c in self.candidate_embeddings:
                     target_map[c] = self.candidate_embeddings[c]
                else:
                     # Compute on fly (slow)
                     emb = self.get_embedding(c)
                     if emb is not None:
                         target_map[c] = emb

        for cand, cand_emb in target_map.items():
            # Cosine similarity
            score = np.dot(query_emb, cand_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(cand_emb))
            if score > best_score:
                best_score = score
                best_cand = cand
        
        if best_score >= threshold:
            return best_cand
        
        return None
