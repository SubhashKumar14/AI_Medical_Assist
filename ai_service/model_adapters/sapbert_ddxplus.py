"""
SapBERT-PubMedBERT-DDXPlus Model Adapter
========================================

This adapter integrates the fine-tuned SapBERT model trained on DDXPlus dataset
for medical diagnosis and symptom understanding tasks.

Model: acharya-jyu/sapbert-pubmedbert-ddxplus-10k
Base: cambridgeltl/SapBERT-from-PubMedBERT-fulltext
Training: DDXPlus dataset (10,000 samples)
Task: Medical diagnosis feature extraction

SapBERT (Self-Alignment Pretraining for BERT) is specifically designed for 
biomedical entity representation and is particularly effective for:
- Medical concept normalization
- Symptom-disease semantic matching
- Clinical entity linking
"""

import os
import logging
from typing import List, Dict, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Model configuration
SAPBERT_MODEL = "acharya-jyu/sapbert-pubmedbert-ddxplus-10k"
FALLBACK_MODEL = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"


class SapBERTDDXPlusAdapter:
    """
    Adapter for SapBERT-PubMedBERT fine-tuned on DDXPlus dataset.
    
    Provides:
    - Medical symptom embeddings
    - Disease-symptom semantic similarity
    - Medical concept normalization
    - Differential diagnosis support
    
    Usage:
        adapter = SapBERTDDXPlusAdapter()
        
        # Get embeddings for symptoms
        embeddings = adapter.get_embeddings(["fever", "cough", "headache"])
        
        # Find similar medical concepts
        similar = adapter.find_similar_concepts("chest pain", top_k=5)
        
        # Calculate symptom-disease similarity
        similarity = adapter.symptom_disease_similarity(
            symptoms=["fever", "cough"],
            diseases=["Pneumonia", "Bronchitis"]
        )
    """
    
    def __init__(self, use_local: bool = True, hf_token: Optional[str] = None):
        """
        Initialize the SapBERT adapter.
        
        Args:
            use_local: Whether to load model locally (vs API)
            hf_token: HuggingFace token for API access
        """
        self.use_local = use_local
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._initialized = False
        
        # Medical concept cache for faster lookups
        self._embedding_cache = {}
        
    def initialize(self) -> bool:
        """
        Initialize the model (lazy loading).
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
            
        try:
            if self.use_local:
                return self._init_local()
            else:
                return self._init_api()
        except Exception as e:
            logger.error(f"Failed to initialize SapBERT: {e}")
            return False
    
    def _init_local(self) -> bool:
        """Initialize model locally using transformers."""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            logger.info(f"Loading SapBERT model: {SAPBERT_MODEL}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(SAPBERT_MODEL)
            self.model = AutoModel.from_pretrained(SAPBERT_MODEL)
            
            # Move to GPU if available
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            
            self._initialized = True
            logger.info(f"✅ SapBERT loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load primary model: {e}")
            logger.info(f"Trying fallback model: {FALLBACK_MODEL}")
            
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
                
                self.tokenizer = AutoTokenizer.from_pretrained(FALLBACK_MODEL)
                self.model = AutoModel.from_pretrained(FALLBACK_MODEL)
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.model.to(self.device)
                self.model.eval()
                
                self._initialized = True
                logger.info(f"✅ Fallback SapBERT loaded on {self.device}")
                return True
                
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                return False
    
    def _init_api(self) -> bool:
        """Initialize using HuggingFace Inference API."""
        try:
            from transformers import pipeline
            
            if not self.hf_token:
                logger.warning("No HF_TOKEN provided for API access")
            
            self.pipeline = pipeline(
                "feature-extraction",
                model=SAPBERT_MODEL,
                token=self.hf_token
            )
            
            self._initialized = True
            logger.info("✅ SapBERT API pipeline initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize API pipeline: {e}")
            return False
    
    def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        batch_size: int = 32,
        use_cache: bool = True
    ) -> np.ndarray:
        """
        Get embeddings for medical text(s).
        
        Args:
            texts: Single text or list of texts
            batch_size: Batch size for processing
            use_cache: Whether to use embedding cache
            
        Returns:
            Numpy array of embeddings [num_texts, embedding_dim]
        """
        if not self.initialize():
            logger.error("Model not initialized")
            return np.array([])
        
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
        
        # Check cache
        if use_cache:
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                if text in self._embedding_cache:
                    cached_embeddings.append((i, self._embedding_cache[text]))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            if not uncached_texts:
                # All cached
                embeddings = np.zeros((len(texts), cached_embeddings[0][1].shape[0]))
                for i, emb in cached_embeddings:
                    embeddings[i] = emb
                return embeddings
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            cached_embeddings = []
        
        # Generate new embeddings
        if self.use_local:
            new_embeddings = self._get_embeddings_local(uncached_texts, batch_size)
        else:
            new_embeddings = self._get_embeddings_api(uncached_texts)
        
        # Update cache
        if use_cache:
            for text, emb in zip(uncached_texts, new_embeddings):
                self._embedding_cache[text] = emb
        
        # Combine cached and new embeddings
        if cached_embeddings:
            embeddings = np.zeros((len(texts), new_embeddings.shape[1]))
            for i, emb in cached_embeddings:
                embeddings[i] = emb
            for idx, emb in zip(uncached_indices, new_embeddings):
                embeddings[idx] = emb
            return embeddings
        
        return new_embeddings
    
    def _get_embeddings_local(self, texts: List[str], batch_size: int) -> np.ndarray:
        """Get embeddings using local model."""
        import torch
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize
            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use CLS token embedding
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings)
    
    def _get_embeddings_api(self, texts: List[str]) -> np.ndarray:
        """Get embeddings using HuggingFace API."""
        embeddings = []
        
        for text in texts:
            result = self.pipeline(text)
            # Extract CLS token embedding
            emb = np.array(result[0][0])
            embeddings.append(emb)
        
        return np.array(embeddings)
    
    def find_similar_concepts(
        self,
        query: str,
        concept_pool: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find similar medical concepts to the query.
        
        Args:
            query: Query medical concept
            concept_pool: Pool of concepts to search (default: common symptoms)
            top_k: Number of top results to return
            
        Returns:
            List of dicts with 'concept' and 'similarity' keys
        """
        if concept_pool is None:
            # Default to common symptoms from DDXPlus
            concept_pool = [
                "fever", "cough", "headache", "fatigue", "nausea",
                "vomiting", "diarrhea", "chest pain", "shortness of breath",
                "abdominal pain", "back pain", "joint pain", "muscle pain",
                "dizziness", "confusion", "weakness", "loss of appetite",
                "weight loss", "night sweats", "rash", "swelling",
                "sore throat", "runny nose", "sneezing", "chills"
            ]
        
        # Get embeddings
        query_emb = self.get_embeddings(query)
        pool_embs = self.get_embeddings(concept_pool)
        
        # Calculate cosine similarities
        similarities = self._cosine_similarity(query_emb, pool_embs)
        
        # Sort and return top_k
        indices = np.argsort(similarities[0])[::-1][:top_k]
        
        return [
            {"concept": concept_pool[i], "similarity": float(similarities[0][i])}
            for i in indices
        ]
    
    def symptom_disease_similarity(
        self,
        symptoms: List[str],
        diseases: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate semantic similarity between symptoms and diseases.
        
        Args:
            symptoms: List of symptom strings
            diseases: List of disease strings
            
        Returns:
            Dict mapping disease -> {symptom: similarity}
        """
        # Get embeddings
        symptom_embs = self.get_embeddings(symptoms)
        disease_embs = self.get_embeddings(diseases)
        
        # Calculate all pairwise similarities
        similarities = self._cosine_similarity(disease_embs, symptom_embs)
        
        result = {}
        for i, disease in enumerate(diseases):
            result[disease] = {
                symptoms[j]: float(similarities[i][j])
                for j in range(len(symptoms))
            }
        
        return result
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between two embedding arrays."""
        # Normalize
        a_norm = a / np.linalg.norm(a, axis=-1, keepdims=True)
        b_norm = b / np.linalg.norm(b, axis=-1, keepdims=True)
        
        # Handle 1D arrays
        if a_norm.ndim == 1:
            a_norm = a_norm.reshape(1, -1)
        if b_norm.ndim == 1:
            b_norm = b_norm.reshape(1, -1)
        
        return np.dot(a_norm, b_norm.T)
    
    def encode_differential_diagnosis(
        self,
        patient_symptoms: List[str],
        candidate_diseases: List[str]
    ) -> List[Dict]:
        """
        Encode symptoms and rank candidate diseases by semantic similarity.
        
        This is useful for differential diagnosis ranking based on
        semantic understanding from SapBERT's medical knowledge.
        
        Args:
            patient_symptoms: List of patient symptoms
            candidate_diseases: List of potential diagnoses
            
        Returns:
            Ranked list of diseases with scores
        """
        # Create symptom profile embedding (mean of symptom embeddings)
        symptom_embs = self.get_embeddings(patient_symptoms)
        profile_emb = np.mean(symptom_embs, axis=0, keepdims=True)
        
        # Get disease embeddings
        disease_embs = self.get_embeddings(candidate_diseases)
        
        # Calculate similarities
        similarities = self._cosine_similarity(profile_emb, disease_embs)[0]
        
        # Rank diseases
        ranked = sorted(
            zip(candidate_diseases, similarities),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"disease": disease, "score": float(score)}
            for disease, score in ranked
        ]
    
    def normalize_symptom(self, symptom: str, canonical_symptoms: List[str]) -> Dict:
        """
        Normalize a symptom to its canonical form using semantic matching.
        
        Args:
            symptom: Input symptom (possibly misspelled or colloquial)
            canonical_symptoms: List of canonical symptom names
            
        Returns:
            Dict with 'canonical', 'similarity', and 'original'
        """
        similar = self.find_similar_concepts(symptom, canonical_symptoms, top_k=1)
        
        if similar:
            return {
                "original": symptom,
                "canonical": similar[0]["concept"],
                "similarity": similar[0]["similarity"]
            }
        
        return {
            "original": symptom,
            "canonical": symptom,
            "similarity": 1.0
        }
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")


# Singleton instance for easy access
_sapbert_instance: Optional[SapBERTDDXPlusAdapter] = None


def get_sapbert_adapter(use_local: bool = True) -> SapBERTDDXPlusAdapter:
    """
    Get or create the SapBERT adapter singleton.
    
    Args:
        use_local: Whether to use local model
        
    Returns:
        SapBERTDDXPlusAdapter instance
    """
    global _sapbert_instance
    
    if _sapbert_instance is None:
        _sapbert_instance = SapBERTDDXPlusAdapter(use_local=use_local)
    
    return _sapbert_instance


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize adapter
    adapter = SapBERTDDXPlusAdapter(use_local=True)
    
    if adapter.initialize():
        # Test embeddings
        symptoms = ["fever", "cough", "headache"]
        embeddings = adapter.get_embeddings(symptoms)
        print(f"Embedding shape: {embeddings.shape}")
        
        # Test similar concepts
        similar = adapter.find_similar_concepts("chest discomfort")
        print(f"\nSimilar to 'chest discomfort':")
        for item in similar:
            print(f"  {item['concept']}: {item['similarity']:.4f}")
        
        # Test differential diagnosis
        diagnoses = adapter.encode_differential_diagnosis(
            patient_symptoms=["fever", "cough", "shortness of breath"],
            candidate_diseases=["Pneumonia", "Bronchitis", "COVID-19", "Common Cold"]
        )
        print(f"\nDifferential diagnosis ranking:")
        for dx in diagnoses:
            print(f"  {dx['disease']}: {dx['score']:.4f}")
    else:
        print("Failed to initialize SapBERT adapter")
