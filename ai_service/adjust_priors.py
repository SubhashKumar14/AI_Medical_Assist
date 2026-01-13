"""
Safety Prior Adjustment Script
==============================

Adjusts the `disease_priors.json` to dampen severe/scary diseases
and boost common/safe diseases. This ensures the AI doesn't jump
to "Cancer" or "HIV" for simple symptoms.
"""

import json
import shutil
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PRIORS_FILE = Path(__file__).parent / "knowledge" / "disease_priors.json"

# Safety Weights (Multiplier for current prior)
# < 1.0 = Dampen
# > 1.0 = Boost
SAFETY_WEIGHTS = {
    # --- DAMPEN (Scary/Rare/Chronic) ---
    "HIV (initial infection)": 0.1,    # Reduce 10x
    "Pancreatic neoplasm": 0.05,       # cancer
    "Pulmonary neoplasm": 0.05,        # cancer
    "Chagas": 0.1,                     # rare parasite
    "Ebola": 0.01,
    "SLE": 0.2,                        # Lupus
    "Myasthenia gravis": 0.2,
    "Guillain-BarrÃ© syndrome": 0.2,   # Check encoding
    "Guillain-Barré syndrome": 0.2,
    "Tuberculosis": 0.2,
    "Boerhaave": 0.1,                  # Esophageal rupture (rare/critical)
    "Acute pulmonary edema": 0.5,      # Emergency
    "Spontaneous pneumothorax": 0.3,
    "Possible NSTEMI / STEMI": 0.5,    # Heart attack (keep high enough to detect red flags, but not default)
    "Unstable angina": 0.5,
    "Pericarditis": 0.5,
    "Myocarditis": 0.5,
    "Pulmonary embolism": 0.4,
    
    # --- BOOST (Common/Acute/Safe) ---
    "URTI": 2.0,                       # Common Cold
    "Viral pharyngitis": 2.0,
    "Influenza": 2.5,                  # Flu
    "Acute rhinosinusitis": 1.5,
    "Allergic sinusitis": 1.5,
    "Acute laryngitis": 1.5,
    "Bronchitis": 1.5,
    "Acute otitis media": 1.5,
    "GERD": 1.2,
    "Cluster headache": 1.2,
    "Anemia": 0.8,                     # Common but chronic-ish
    "Panic attack": 1.2,
}

def adjust_priors():
    print(f"Loading {PRIORS_FILE}...")
    with open(PRIORS_FILE, 'r', encoding='utf-8') as f:
        priors = json.load(f)
        
    print("Adjusting priors...")
    new_priors = {}
    
    # Apply weights
    for disease, prob in priors.items():
        weight = SAFETY_WEIGHTS.get(disease, 1.0) # Default to 1.0 (no change)
        new_prob = prob * weight
        new_priors[disease] = new_prob
        
        if weight != 1.0:
            print(f"   {disease}: {prob:.5f} -> {new_prob:.5f} (x{weight})")
            
    # Re-normalize to sum to 1.0
    total_prob = sum(new_priors.values())
    print(f"\nTotal Mass before normalization: {total_prob:.4f}")
    
    for d in new_priors:
        new_priors[d] /= total_prob
        
    print(f"Total Mass after normalization: {sum(new_priors.values()):.4f}")
    
    # Check top movers
    sorted_priors = sorted(new_priors.items(), key=lambda x: x[1], reverse=True)
    print("\nNew Top 5 Priors (Baselines):")
    for d, p in sorted_priors[:5]:
        print(f"   - {d}: {p:.4f}")
        
    # Backup
    shutil.copy(PRIORS_FILE, str(PRIORS_FILE) + ".backup")
    
    # Save
    with open(PRIORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_priors, f, indent=2)
        
    print("\n✅ Priors updated successfully.")

if __name__ == "__main__":
    adjust_priors()
