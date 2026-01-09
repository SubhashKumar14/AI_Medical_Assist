"""Quick test of the Symptom Elimination Engine with all integrations."""

from engines.symptom_elimination import SymptomEliminationEngine

def test_engine():
    print("=" * 60)
    print("Testing Symptom Elimination Engine (SOTA)")
    print("=" * 60)
    
    engine = SymptomEliminationEngine()
    
    # Test 1: Symptom extraction
    print("\n1. Testing symptom extraction...")
    result = engine.extract_symptoms("I have fever, cough, and shortness of breath for 3 days")
    print(f"   Symptoms found: {result['symptoms']}")
    print(f"   Duration: {result.get('duration')}")
    print(f"   Red flags: {[r['symptom'] for r in result['red_flags']]}")
    
    # Test 2: Start triage session
    print("\n2. Starting triage session...")
    symptoms = result['symptoms']
    state = engine.start(symptoms)
    print(f"   Session ID: {state['session_id'][:8]}...")
    print(f"   Status: {state['status']}")
    print(f"   Initial symptoms: {state.get('observed_symptoms', [])}")
    
    # Test 3: Generate predictions
    print("\n3. Generating predictions...")
    preds = engine._generate_predictions(state['posterior'])
    print("   Top 5 Predictions:")
    for p in preds[:5]:
        print(f"      {p['rank']}. {p['disease']}: {p['percentage']} ({p['confidence']})")
    
    # Test 4: Enhanced predictions with SapBERT
    print("\n4. Enhancing with SapBERT semantic similarity...")
    observed_symptoms = state.get('observed_symptoms', [])
    enhanced = engine.enhance_predictions_with_sapbert(observed_symptoms, preds[:5])
    
    if enhanced != preds[:5]:
        print("   Enhanced Predictions:")
        for p in enhanced[:5]:
            bayesian = p.get('bayesian_score', p['probability'])
            sapbert = p.get('sapbert_score', 'N/A')
            print(f"      {p['rank']}. {p['disease']}: {p['percentage']} (Bayesian: {bayesian:.3f}, SapBERT: {sapbert})")
    else:
        print("   SapBERT not available, using Bayesian predictions only")
    
    # Test 5: Question generation
    print("\n5. Next question (information gain based)...")
    if state.get('next_question'):
        q = state['next_question']
        print(f"   Q: {q.get('question', q.get('text', 'N/A'))}")
        print(f"   Symptom: {q.get('symptom', 'N/A')}")
        print(f"   Info Gain: {q.get('info_gain', 0):.4f}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_engine()
