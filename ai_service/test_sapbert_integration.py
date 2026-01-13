import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.symptom_elimination import SymptomEliminationEngine

logging.basicConfig(level=logging.INFO)

def test_sapbert_normalization():
    print("Initializing Engine with SapBERT...")
    # Initialize engine
    # Note: SapBERT is lazy loaded when needed
    engine = SymptomEliminationEngine(use_bert_nlp=False) 
    
    # Test cases: Non-canonical -> Canonical
    test_cases = [
        ("my head hurts", "headache"),
        ("high temp", "fever"),
        ("feeling throwing up", "nausea"), # or vomiting
        ("can't sleep at all", "insomnia"),
        ("pain in my belly", "abdominal pain") 
    ]
    
    print("\nStarting Normalization Tests...")
    print("-" * 50)
    
    for input_text, expected_partial in test_cases:
        print(f"\nInput: '{input_text}'")
        
        # We use extract_symptoms which calls _map_to_canonical_symptoms
        result = engine.extract_symptoms(input_text)
        extracted = result["symptoms"]
        
        print(f"Extracted: {extracted}")
        
        # Check if expected is in extracted (or semantically close)
        # Note: 'feeling throwing up' might map to 'nausea' or 'vomiting'
        # 'high temp' might be mapped via synonyms dict too, but SapBERT covers what synonyms miss.
        
        found = False
        for s in extracted:
            if expected_partial in s:
                found = True
                break
        
        if found:
            print("✅ MATCH")
        else:
            print(f"❌ MISMATCH (Expected '{expected_partial}')")
            
    print("\nDone.")

if __name__ == "__main__":
    test_sapbert_normalization()
