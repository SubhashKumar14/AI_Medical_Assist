"""
Knowledge Base Normalizer
=========================

Standardizes symptom names in `disease_symptom_trained.csv` using SapBERT.
Maps noisy terms (e.g., "pain in belly") to canonical ones (e.g., "abdominal pain").

Usage:
    python normalize_kb.py
"""

import pandas as pd
import sys
import os
from pathlib import Path
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model_adapters.sapbert_helper import SapBERTHelper

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
INPUT_CSV = KNOWLEDGE_DIR / "disease_symptom_trained.csv"
OUTPUT_CSV = KNOWLEDGE_DIR / "disease_symptom_normalized.csv"

# Target canonical list (Subset of common terms + clean DDXPlus terms)
# We can also just use the most common term for each cluster, but a fixed list is safer.
# For now, we'll try to map to a curated list if possible, or just cluster.
# A simple curated list for our specific test cases:
CANONICAL_TARGETS = [
    "abdominal pain", "fever", "headache", "cough", "fatigue", "nausea", 
    "vomiting", "diarrhea", "chest pain", "shortness of breath", "dizziness",
    "rash", "joint pain", "muscle pain", "chills", "sweating", "sore throat",
    "runny nose", "sneezing", "loss of taste", "loss of smell", "weight loss",
    "anxiety", "depression", "insomnia", "palpitations", "constipation",
    "back pain", "vision changes", "eye pain", "ear pain", "seizure",
    "confusion", "swelling", "itching", "wheezing"
]

def normalize_kb():
    if not INPUT_CSV.exists():
        print(f"❌ Input file not found: {INPUT_CSV}")
        return

    print(f"Loading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV)
    
    unique_symptoms = df['symptom'].unique()
    print(f"Found {len(unique_symptoms)} unique symptoms.")
    
    print("Initializing SapBERT...")
    sapbert = SapBERTHelper(use_api=False)
    
    # Pre-cache targets
    sapbert.cache_candidates(CANONICAL_TARGETS)
    
    mapping = {}
    
    print("Normalizing symptoms...")
    for sym in tqdm(unique_symptoms):
        # 1. Check direct match
        if sym in CANONICAL_TARGETS:
            mapping[sym] = sym
            continue
            
        # 2. SapBERT match
        normalized = sapbert.normalize(sym, candidates=None, threshold=0.7) # Use cached targets
        
        if normalized:
            mapping[sym] = normalized
        else:
            mapping[sym] = sym # Keep original if no match
            
    # Apply mapping
    print("Applying mapping...")
    df['original_symptom'] = df['symptom']
    df['symptom'] = df['symptom'].map(mapping)
    
    # Aggregating duplicates (e.g. if "pain in belly" and "abdominal pain" both exist for same disease)
    # We sum weights? Or max? Or average? 
    # For probabilistic systems, P(S|D). If we merge S1 and S2 -> S, P(S|D) should roughly be P(S1|D) + P(S2|D) - intersection?
    # Simple approach: Max weight.
    
    print("Aggregating duplicates...")
    df_clean = df.groupby(['disease', 'symptom'])['weight'].max().reset_index()
    
    print(f"Saving to {OUTPUT_CSV}...")
    df_clean.to_csv(OUTPUT_CSV, index=False)
    
    # Replace original? Maybe backup first.
    backup_path = str(INPUT_CSV) + ".backup"
    import shutil
    shutil.copy(INPUT_CSV, backup_path)
    df_clean.to_csv(INPUT_CSV, index=False)
    
    print("✅ Knowledge Base Normalized!")
    
    # Show some changes
    changes = df[df['symptom'] != df['original_symptom']]
    if not changes.empty:
        print("\nSample changes:")
        print(changes[['original_symptom', 'symptom']].drop_duplicates().head(10))

if __name__ == "__main__":
    normalize_kb()
