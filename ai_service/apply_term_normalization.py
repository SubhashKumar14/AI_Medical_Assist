"""
Apply Term Normalization
========================

Updates the Knowledge Base files to use Layman Terms instead of Scientific Terms.
Ref: map_medical_terms.py

Targets:
1. knowledge/disease_symptom_trained.csv
2. knowledge/symptom_questions_trained.json
"""

import json
import csv
import shutil
import os
import sys
from pathlib import Path

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from map_medical_terms import SCIENTIFIC_TO_LAYMAN

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CSV_FILE = KNOWLEDGE_DIR / "disease_symptom_trained.csv"
JSON_FILE = KNOWLEDGE_DIR / "symptom_questions_trained.json"

def normalize_text(text: str) -> str:
    """
    Replaces scientific terms with layman terms in a string.
    Case-insensitive replacement.
    """
    if not text:
        return text
        
    # Sort by length (descending) to prevent partial replacements of longer terms
    # e.g. "pain in eye" vs "pain in eyelid"
    sorted_terms = sorted(SCIENTIFIC_TO_LAYMAN.keys(), key=len, reverse=True)
    
    text_lower = text.lower()
    
    for sci in sorted_terms:
        if sci in text_lower:
            # We construct a case-insensitive replacement
            # But simplest is just to lowercase everything for the symptom ID
            # For display text, we might want to preserve case, but for keys, lowercase is safer.
            layman = SCIENTIFIC_TO_LAYMAN[sci]
            text_lower = text_lower.replace(sci, layman)
            
    # Fix awkward phrasings often found in dataset
    replacements = [
        ("pain in palace", "pain in roof of mouth"),
        ("thyroid cartilage", "adam's apple"),
        ("do you have finding of", "do you have"),
        ("do you have do you have", "do you have"),
        ("do you have are you", "are you"),
        ("do you have is your", "is your"),
        ("do you have does your", "does your"),
        ("do you have have you", "have you"),
        ("pain in the breast", "breast pain"),
        ("pain in the eye", "eye pain"),
        ("pain in the ear", "ear pain"),
    ]
    
    for old, new in replacements:
        text_lower = text_lower.replace(old, new)
        
    return text_lower

def process_csv():
    print(f"Processing {CSV_FILE}...")
    if not CSV_FILE.exists():
        print("CSV file not found!")
        return

    # Read
    rows = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            # Normalize Symptom Name
            old_symptom = row['symptom']
            new_symptom = normalize_text(old_symptom)
            
            if old_symptom != new_symptom:
                # print(f"  CSV: '{old_symptom}' -> '{new_symptom}'")
                pass
                
            row['symptom'] = new_symptom
            rows.append(row)
            
    # Backup
    shutil.copy(CSV_FILE, str(CSV_FILE) + ".backup_norm")
    
    # Write
    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("✅ CSV normalized.")

def process_json():
    print(f"Processing {JSON_FILE}...")
    if not JSON_FILE.exists():
        print("JSON file not found!")
        return
        
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    new_data = {}
    
    for symptom, info in data.items():
        # Normalize Key (Symptom)
        new_symptom = normalize_text(symptom)
        
        # Normalize Question Text
        old_q = info['question']
        new_q = normalize_text(old_q)
        
        # Capitalize first letter of question
        new_q = new_q[0].upper() + new_q[1:] if new_q else new_q
        
        info['question'] = new_q
        new_data[new_symptom] = info
        
    # Backup
    shutil.copy(JSON_FILE, str(JSON_FILE) + ".backup_norm")
    
    # Write
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2)
    print("✅ JSON normalized.")

if __name__ == "__main__":
    process_csv()
    process_json()
