import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.symptom_elimination import SymptomEliminationEngine

# Configure logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def analyze_specific_loopholes():
    print("🔍 Analyzing Pre-identified Loopholes...")
    
    engine = SymptomEliminationEngine(use_bert_nlp=False)
    
    # CASE 1: Semantic match failure
    # "pain in my belly" -> Should be "abdominal pain"
    input_text = "pain in my belly"
    print(f"\n--- Testing: '{input_text}' ---")
    result = engine.extract_symptoms(input_text)
    print(f"Extracted: {result['symptoms']}")
    
    if "abdominal pain" not in result['symptoms']:
        print("❌ LOOPHOLE FOUND: Failed to map 'belly pain' to 'abdominal pain'")
    else:
        print("✅ FIXED: SapBERT correctly mapped 'pain in my belly' -> 'abdominal pain'")
        print(f"   Extraction Method Used: {result.get('extraction_method')}")

    # CASE 2: Red Flag Detection
    input_text = "I have a severe headache and sudden vision loss"
    print(f"\n--- Testing: '{input_text}' (Red Flag Check) ---")
    result = engine.extract_symptoms(input_text)
    print(f"Red Flags: {result['red_flags']}")
    
    if not result['red_flags']:
         print("❌ LOOPHOLE FOUND: Red flag 'sudden vision loss' missed.")

    # CASE 3: Contradictory inputs
    # Not supported by engine explicitly, but check behavior
    
    print("\nanalysis complete.")

if __name__ == "__main__":
    analyze_specific_loopholes()
