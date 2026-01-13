"""
MIMIC Dataset Preprocessor
===========================

Converts raw MIMIC-III clinical notes into training data format for the symptom engine.
Extracts symptoms using SciSpacy NLP and maps them to diagnoses.

Requirements:
    pip install spacy scispacy
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz

Usage:
    python preprocess_mimic.py --notes NOTEEVENTS.csv --diagnoses DIAGNOSES_ICD.csv
"""

import pandas as pd
import re
import argparse
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm

# Try to load SciSpacy
try:
    import spacy
    nlp = spacy.load("en_core_sci_sm")
    print("✅ SciSpacy loaded successfully")
except OSError:
    print("⚠️ SciSpacy model not found. Install with:")
    print("pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz")
    nlp = None
except ImportError:
    print("⚠️ spacy not installed. Using regex fallback.")
    nlp = None


# Common symptom patterns for regex fallback
COMMON_SYMPTOMS = [
    'fever', 'cough', 'headache', 'nausea', 'vomiting', 'diarrhea',
    'fatigue', 'weakness', 'dizziness', 'chest pain', 'shortness of breath',
    'abdominal pain', 'back pain', 'joint pain', 'muscle pain', 'rash',
    'chills', 'sweating', 'loss of appetite', 'weight loss', 'constipation',
    'confusion', 'anxiety', 'depression', 'insomnia', 'palpitations'
]


def extract_symptoms_nlp(text: str) -> list:
    """Extract symptoms using SciSpacy NER."""
    if nlp is None:
        return extract_symptoms_regex(text)
    
    doc = nlp(text.lower())
    symptoms = set()
    
    # Extract named entities
    for ent in doc.ents:
        symptoms.add(ent.text)
    
    # Also check common symptoms via regex
    for sym in COMMON_SYMPTOMS:
        if sym in text.lower():
            symptoms.add(sym)
    
    return list(symptoms)


def extract_symptoms_regex(text: str) -> list:
    """Fallback regex-based symptom extraction."""
    text_lower = text.lower()
    found = []
    
    for sym in COMMON_SYMPTOMS:
        if sym in text_lower:
            found.append(sym)
    
    return found


def preprocess_mimic(notes_path: str, diagnoses_path: str, output_path: str = None, max_rows: int = 5000):
    """
    Process MIMIC-III data to generate disease_symptom.csv.
    
    Args:
        notes_path: Path to NOTEEVENTS.csv
        diagnoses_path: Path to DIAGNOSES_ICD.csv (with LONG_TITLE column)
        output_path: Output CSV path
        max_rows: Maximum rows to process (for speed)
    """
    output_path = output_path or str(Path(__file__).parent.parent / "knowledge" / "disease_symptom_mimic.csv")
    
    print(f"⏳ Loading MIMIC data (max {max_rows} rows)...")
    
    try:
        notes_df = pd.read_csv(notes_path, nrows=max_rows)
        diag_df = pd.read_csv(diagnoses_path, nrows=max_rows)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("Please provide valid paths to MIMIC NOTEEVENTS.csv and DIAGNOSES_ICD.csv")
        return
    
    # Check required columns
    if 'HADM_ID' not in notes_df.columns:
        print("❌ NOTEEVENTS.csv must contain HADM_ID column")
        return
    if 'TEXT' not in notes_df.columns:
        print("❌ NOTEEVENTS.csv must contain TEXT column")
        return
    
    # Merge on admission ID
    print("🔗 Merging notes with diagnoses...")
    merged = pd.merge(notes_df, diag_df, on="HADM_ID", how="inner")
    
    if merged.empty:
        print("❌ No matching records found between notes and diagnoses")
        return
    
    print(f"📊 Processing {len(merged)} records...")
    
    # Count symptom-disease co-occurrences
    knowledge_map = defaultdict(lambda: defaultdict(int))
    disease_counts = defaultdict(int)
    
    # Determine diagnosis column
    diag_col = 'LONG_TITLE' if 'LONG_TITLE' in merged.columns else 'ICD9_CODE'
    
    for _, row in tqdm(merged.iterrows(), total=len(merged), desc="Extracting symptoms"):
        text = str(row.get('TEXT', ''))
        disease = str(row.get(diag_col, 'Unknown'))
        
        if not text or disease == 'Unknown':
            continue
        
        disease_counts[disease] += 1
        
        # Extract symptoms
        symptoms = extract_symptoms_nlp(text)
        
        # Update counts (unique per note)
        for sym in set(symptoms):
            knowledge_map[disease][sym] += 1
    
    # Calculate weights: P(Symptom | Disease)
    print("⚗️ Calculating probability matrix...")
    output_rows = []
    
    for disease, symptoms in knowledge_map.items():
        total_cases = disease_counts[disease]
        if total_cases < 3:  # Skip rare diseases
            continue
        
        for symptom, count in symptoms.items():
            weight = count / total_cases
            # Filter noise (very rare symptoms)
            if weight > 0.05 and len(symptom) > 2:
                output_rows.append({
                    "disease": disease[:100],  # Truncate long names
                    "symptom": symptom,
                    "weight": round(weight, 3)
                })
    
    # Save output
    df_out = pd.DataFrame(output_rows)
    df_out = df_out.sort_values(['disease', 'weight'], ascending=[True, False])
    df_out.to_csv(output_path, index=False)
    
    print(f"✅ Preprocessing complete!")
    print(f"   Output: {output_path}")
    print(f"   Diseases: {len(set(df_out['disease']))}")
    print(f"   Symptom-disease pairs: {len(df_out)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess MIMIC data for symptom engine")
    parser.add_argument("--notes", required=True, help="Path to NOTEEVENTS.csv")
    parser.add_argument("--diagnoses", required=True, help="Path to DIAGNOSES_ICD.csv")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--max-rows", type=int, default=5000, help="Max rows to process")
    
    args = parser.parse_args()
    preprocess_mimic(args.notes, args.diagnoses, args.output, args.max_rows)
