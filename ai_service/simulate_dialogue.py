"""
Dialogue Simulation: Fever + Headache
=====================================

Simulates a user interaction to audit the "Safety/Morale" of the AI.
Checks if the AI jumps to scary conclusions too early.
"""

import sys
import os
import logging

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engines.symptom_elimination import SymptomEliminationEngine

# Configure logging
logging.basicConfig(level=logging.INFO)

def simulate():
    print("🤖 Initializing Engine...")
    engine = SymptomEliminationEngine()
    
    # 1. Start with common symptoms
    initial_text = "I have a fever and a bad headache."
    print(f"\n👤 User: '{initial_text}'")
    
    extracted = engine.extract_symptoms(initial_text)
    symptoms = extracted['symptoms']
    print(f"   Extracted: {symptoms}")
    
    state = engine.start(symptoms)
    
    # Trace the flow for 5 turns
    for turn in range(5):
        print(f"\n--- Turn {turn + 1} ---")
        
        # Show Top 5 diseases considered
        probs = state['probabilities'][:5]
        print("   Thinking (Top 5):")
        for p in probs:
            print(f"   - {p['disease']} ({p['probability']:.4f})")
            
        # Show Question
        question = engine.next_question(state)
        if not question:
            print("   (No more questions)")
            break
            
        q_text = question['text']
        print(f"🤖 AI Question: '{q_text}'")
        print(f"   (Type details: {question.get('type', 'binary')})")
        
        # Check for scary words in question
        scary_terms = ["cancer", "tumor", "death", "failure", "chronic", "permanent"]
        for term in scary_terms:
            if term in q_text.lower():
                 print(f"   ⚠️ WARNING: Question contains potentially alarming term '{term}'")

        # Simulate "No" to everything to see where it goes (common baseline)
        # unless it's a very common symptom for fever/headache?
        # Let's say "No" to specifics to see if it defaults to safe stuff.
        print("👤 User: No")
        state = engine.update(state, "no")

if __name__ == "__main__":
    simulate()
