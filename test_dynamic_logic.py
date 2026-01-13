
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'ai_service'))

from engines.symptom_elimination import SymptomEliminationEngine

def print_top_questions(engine, posterior, asked_symptoms, label):
    print(f"\n[{label}] Top 3 Questions by Information Gain:")
    
    # Get top 10 diseases to narrow search (optimization in engine)
    top_diseases = [d for d, p in sorted(posterior.items(), key=lambda x: x[1], reverse=True)[:10] if p > 0.01]
    
    candidate_symptoms = set()
    for disease in top_diseases:
        if disease in engine.likelihood_matrix:
            candidate_symptoms.update(engine.likelihood_matrix[disease].keys())
            
    candidates = []
    for s in candidate_symptoms:
        if s in asked_symptoms: continue
        ig = engine._expected_information_gain(posterior, s)
        candidates.append((s, ig))
        
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    for i, (sym, ig) in enumerate(candidates[:3]):
        print(f"   {i+1}. {sym:<20} IG: {ig:.4f}")
    
    return candidates[0][0] if candidates else None

def test_dynamic_flow():
    print("="*60)
    print("DEMONSTRATION: Dynamic Question Selection Logic")
    print("="*60)
    
    engine = SymptomEliminationEngine()
    
    # Scenario: User starts with "Fever"
    initial_symptoms = ["fever"]


    # Initial State
    state = engine.start(initial_symptoms)
    posterior = state['posterior']
    top_preds = sorted(posterior.items(), key=lambda x: x[1], reverse=True)[:3]

    # 1. Get Best Question for Step 1
    # We need to capture the return value, so we modify print_top_questions to validly return it
    # But since print_top_questions prints to stdout (which we ignore), we need to replicate the logic or just call it 
    # to get the return value. 
    # Actually, let's just use the engine method directly for the best question to be clean.
    best_q_obj = engine._get_best_question(posterior, initial_symptoms)
    best_q1 = best_q_obj['symptom'] if best_q_obj else "None"
    
    # BRANCH A: Answer YES to Q1
    state_a = engine.update(state.copy(), "yes", best_q1)
    top_preds_a = sorted(state_a['posterior'].items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Next question for A
    next_q_obj_a = engine._get_best_question(state_a['posterior'], state_a['asked_questions'])
    next_q_a = next_q_obj_a['symptom'] if next_q_obj_a else "None"
    
    # BRANCH B: Answer NO to Q1
    state_b = engine.update(state.copy(), "no", best_q1)
    top_preds_b = sorted(state_b['posterior'].items(), key=lambda x: x[1], reverse=True)[:3]

    # Next question for B
    next_q_obj_b = engine._get_best_question(state_b['posterior'], state_b['asked_questions'])
    next_q_b = next_q_obj_b['symptom'] if next_q_obj_b else "None"

    # Write results to file
    with open("results.log", "w", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write("DEMONSTRATION: Dynamic Question Selection Logic\n")
        f.write("="*60 + "\n")
        
        f.write(f"\nStep 0: Initial Symptom -> {initial_symptoms}\n")
        f.write("\n   Initial Probability Distribution (Top 3):\n")
        for d, p in top_preds:
            f.write(f"   - {d}: {p:.1%}\n")

        f.write(f"\n[Step 1] Top Question: {best_q1}\n")
        
        # BRANCH A
        f.write(f"\n--- BRANCH A: User answers YES to '{best_q1}' ---\n")
        f.write("   Updated Probabilities:\n")
        for d, p in top_preds_a:
            f.write(f"   - {d}: {p:.1%}\n")
            
        f.write(f"   [Branch A] Next Best Question: {next_q_a}\n")

        # BRANCH B
        f.write(f"\n--- BRANCH B: User answers NO to '{best_q1}' ---\n")
        f.write("   Updated Probabilities:\n")
        for d, p in top_preds_b:
            f.write(f"   - {d}: {p:.1%}\n")
            
        f.write(f"   [Branch B] Next Best Question: {next_q_b}\n")
        
        f.write("\n" + "="*60 + "\n")
        if next_q_a != next_q_b:
            f.write("✅ SUCCESS: The next question CHANGED based on the answer!\n")
        else:
            f.write("❌ FAILURE: The next question was the same.\n")
        f.write("="*60 + "\n")

if __name__ == "__main__":
    test_dynamic_flow()

