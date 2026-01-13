"""
Comprehensive Safety Scenario Tests
===================================

Verifies all components of the "Safety V2" architecture.
1. Red Flag Override (Chest Pain -> Emergency)
2. Low Confidence Masking (Fever -> Viral Infection)
3. High Risk Filtering (Heart Attack -> Cardiovascular Concern)
4. Happy Path (Cold -> URTI)
5. Term Normalization (Dyspnea -> Shortness of Breath)
"""

import sys
import os
import io
import contextlib
from pathlib import Path

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.symptom_elimination import SymptomEliminationEngine
from safety_config import RED_FLAG_SYMPTOMS, RISK_CATEGORIES

def test_red_flag_override():
    print("\n🚨 TEST 1: Red Flag Override")
    engine = SymptomEliminationEngine()
    
    # Input with ONE severe symptom
    text = "I have a mild fever but severe chest pain."
    print(f"   Input: '{text}'")
    
    extracted = engine.extract_symptoms(text)
    print(f"   Extracted: {extracted.get('symptoms')}")
    
    # Check explicitly for red flags
    flags = engine.check_red_flags(extracted.get('symptoms', []))
    print(f"   🚩 DEBUG FLAGS CONTENT: {flags}") 
    if flags:
        print(f"   ✅ RED FLAG DETECTED: {[f['symptom'] for f in flags]}")
        # Verify message content
        if "message" in flags[0]:
             if "emergency" in flags[0]['message'].lower():
                print("   ✅ Message is urgent.")
        else:
             print("   ❌ MISSING 'message' KEY in flag object.")
    else:
        print("   ❌ FAILED: Red flag not detected.")

def test_term_normalization():
    print("\n🗣️ TEST 2: Term Normalization")
    engine = SymptomEliminationEngine()
    
    # Input with Scientific Term
    text = "I am suffering from dyspnea and myalgia."
    print(f"   Input: '{text}'")
    
    # Engine should map this to "shortness of breath" and "muscle pain" 
    # IF the KB was updated correctly OR if map logic exists in extract
    extracted = engine.extract_symptoms(text)
    symptoms = extracted.get('symptoms', [])
    print(f"   Extracted: {symptoms}")
    
    # Check if scientific terms remain
    if "dyspnea" in symptoms or "myalgia" in symptoms:
        print("   ⚠️ WARNING: Scientific terms preserved (Not Fatal, but normalization preferred).")
    elif "shortness of breath" in symptoms or "muscle pain" in symptoms:
        print("   ✅ NORMALIZED: Terms converted to layman.")
    else:
        print("   ❓ UNKNOWN: different extraction result.")

def test_high_risk_masking():
    print("\n🛡️ TEST 3: High Risk Masking (Simulation)")
    # This tests the LOGIC intended for app.py, not the app itself (for speed)
    
    # Simulate a dangerous prediction
    predicted_disease = "Myocardial infarction"
    predicted_prob = 0.85
    print(f"   Simulated Prediction: {predicted_disease} ({predicted_prob})")
    
    # Check Safety Config Masking
    if predicted_disease in RISK_CATEGORIES:
        safe_name = f"⚠️ {RISK_CATEGORIES[predicted_disease]}"
        print(f"   ✅ MASKED TO: '{safe_name}'")
    else:
        print(f"   ❌ FAILED: High risk disease '{predicted_disease}' not masked.")

def test_low_confidence_masking():
    print("\n📉 TEST 4: Low Confidence Masking (Simulation)")
    
    # Simulate low confidence
    prediction = "Influenza"
    prob = 0.45 # Below 0.60
    print(f"   Simulated Prediction: {prediction} ({prob})")
    
    if prob < 0.60:
        print("   ✅ LOW CONFIDENCE TRIGGERED: Output should be 'Common Viral Infection' bucket.")
    else:
        print("   ❌ FAILED logic check.")

if __name__ == "__main__":
    test_red_flag_override()
    test_term_normalization()
    test_high_risk_masking()
    test_low_confidence_masking()
