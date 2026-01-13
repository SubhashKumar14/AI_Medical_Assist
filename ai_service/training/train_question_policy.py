"""
Question Relevance Policy Trainer
==================================

Calculates the optimal question order using Information Gain (Entropy Reduction).
This ensures the AI asks the most discriminative questions first.

The output is a ranked list of symptoms by their expected entropy reduction,
which guides the 3-5-7 questioning algorithm.

Usage:
    python train_question_policy.py
"""

import pandas as pd
import numpy as np
import math
import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def calculate_entropy(probabilities: list) -> float:
    """Calculate Shannon entropy: H = -Σ p*log2(p)"""
    return -sum(p * math.log2(p) for p in probabilities if p > 0)


def train_question_relevance():
    """
    Calculate Information Gain for each symptom question.
    
    A symptom with ~50% probability across diseases has maximum information gain
    because it best splits the disease space.
    """
    # Load trained knowledge base
    csv_path = KNOWLEDGE_DIR / "disease_symptom_trained.csv"
    if not csv_path.exists():
        csv_path = KNOWLEDGE_DIR / "disease_symptom.csv"
    
    if not csv_path.exists():
        print("❌ No knowledge base found. Run training first.")
        return
    
    print(f"📊 Loading knowledge base: {csv_path.name}")
    df = pd.read_csv(csv_path)
    
    symptoms = df['symptom'].unique()
    diseases = df['disease'].unique()
    n_diseases = len(diseases)
    
    print(f"   Diseases: {n_diseases}, Symptoms: {len(symptoms)}")
    
    relevance_scores = []
    
    print("📉 Calculating Information Gain for each symptom...")
    
    # Baseline entropy (uniform prior over diseases)
    base_entropy = math.log2(n_diseases) if n_diseases > 1 else 0
    
    for symptom in symptoms:
        # Calculate average P(S=yes) across all diseases
        # A balanced split (0.5) gives maximum information
        
        p_yes_sum = 0
        symptom_data = df[df['symptom'] == symptom]
        
        for disease in diseases:
            row = symptom_data[symptom_data['disease'] == disease]
            weight = row['weight'].values[0] if not row.empty else 0.01
            p_yes_sum += weight
        
        p_yes = p_yes_sum / n_diseases
        p_no = 1 - p_yes
        
        # Entropy of the yes/no split
        if p_yes <= 0 or p_yes >= 1:
            split_entropy = 0
        else:
            split_entropy = -(p_yes * math.log2(p_yes) + p_no * math.log2(p_no))
        
        # Information gain = how much this question reduces uncertainty
        info_gain = split_entropy
        
        # Also consider disease specificity (high weight in few diseases)
        disease_coverage = len(symptom_data)
        specificity = 1.0 - (disease_coverage / n_diseases) if n_diseases > 0 else 0
        
        # Combined score: balance between split quality and specificity
        combined_score = 0.7 * split_entropy + 0.3 * specificity
        
        relevance_scores.append({
            "symptom": symptom,
            "information_gain": round(split_entropy, 4),
            "specificity": round(specificity, 4),
            "combined_score": round(combined_score, 4),
            "p_yes_avg": round(p_yes, 4)
        })
    
    # Sort by combined score (best questions first)
    policy_df = pd.DataFrame(relevance_scores)
    policy_df = policy_df.sort_values("combined_score", ascending=False)
    
    # Save CSV
    csv_output = KNOWLEDGE_DIR / "question_relevance_policy.csv"
    policy_df.to_csv(csv_output, index=False)
    
    # Also save as JSON for easy loading
    json_output = KNOWLEDGE_DIR / "question_policy.json"
    policy_dict = {row['symptom']: row['combined_score'] for _, row in policy_df.iterrows()}
    with open(json_output, 'w') as f:
        json.dump(policy_dict, f, indent=2)
    
    print(f"✅ Question policy trained!")
    print(f"   CSV: {csv_output}")
    print(f"   JSON: {json_output}")
    print(f"\n🔝 Top 10 most informative questions:")
    
    for i, row in policy_df.head(10).iterrows():
        print(f"   {row['symptom']}: {row['combined_score']:.3f}")


if __name__ == "__main__":
    train_question_relevance()
