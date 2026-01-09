# SOTA AI Medical Diagnosis System - Upgrade Documentation

## Overview

This document describes the State-of-the-Art (SOTA) upgrades implemented for the AI Medical Assist system to achieve near-perfect accuracy for the B.Tech Major Project.

---

## 🎯 Key Improvements

### 1. **3-5-7 Question Rule**
The symptom elimination engine now implements an adaptive questioning strategy:

| Questions | Condition | Action |
|-----------|-----------|--------|
| 0-2 | Always | Continue asking |
| 3-5 | Confidence ≥ 85% | Stop (high confidence) |
| 3-5 | Confidence < 85% | Continue asking |
| 5-7 | Confidence ≥ 60% | Stop (sufficient confidence) |
| 5-7 | Confidence < 60% | Continue (low confidence) |
| 7+ | Always | Hard stop |

### 2. **Bayesian Inference Engine**
- Proper posterior calculation: `P(D|S+,S-) ∝ P(D) × Π P(s+|D) × Π (1 - P(s-|D))`
- Laplace smoothing for unseen symptom-disease pairs
- Information gain-based question selection using entropy reduction

### 3. **Expanded Disease Coverage**
Now covers 17+ common diseases with epidemiologically-informed probabilities:
- **Vector-borne**: Dengue, Malaria
- **Respiratory**: Common Cold, Influenza, COVID-19, Pneumonia, TB, Asthma
- **GI**: Typhoid, Gastroenteritis, Appendicitis
- **Neurological**: Migraine
- **Urological**: UTI
- **Cardiovascular**: Hypertension
- **Endocrine**: Diabetes Type 2
- **Allergic**: Allergic Rhinitis
- **Mental Health**: Anxiety, Depression

### 4. **Red Flag Detection**
Critical symptoms that trigger emergency warnings:
- Chest pain, difficulty breathing
- Severe headache, confusion
- Loss of consciousness, seizures
- Coughing blood, severe bleeding
- Suicidal thoughts

---

## 📁 File Structure

```
ai_service/
├── engines/
│   └── symptom_elimination.py   # SOTA Bayesian engine with 3-5-7 rule
├── training/
│   ├── __init__.py
│   └── train_knowledge_base.py  # DDXPlus training script
├── knowledge/
│   ├── disease_symptom.csv      # Original (fallback)
│   ├── disease_symptom_trained.csv    # Generated from DDXPlus
│   ├── symptom_questions_trained.json # Trained question bank
│   └── disease_priors.json      # P(D) from epidemiology
└── requirements.txt             # Updated with SOTA dependencies
```

---

## 🚀 Training the Knowledge Base

### Option 1: Using HuggingFace DDXPlus
```bash
cd ai_service
pip install datasets huggingface_hub
python -m training.train_knowledge_base
```

### Option 2: Using Local DDXPlus Files
1. Download from: https://huggingface.co/datasets/mila-iqia/ddxplus
2. Place in: `ai_service/training/raw_data/ddxplus/`
3. Run: `python -m training.train_knowledge_base`

### Option 3: Medical Literature Fallback
If no dataset is available, the system auto-generates probabilities from medical literature sources (already included as defaults).

---

## 📊 Configuration Constants

```python
# Question limits (3-5-7 Rule)
MIN_QUESTIONS = 3           # Always ask at least 3
SOFT_MAX_QUESTIONS = 5      # Stop if confidence > 85%
HARD_MAX_QUESTIONS = 7      # Absolute maximum

# Confidence thresholds
HIGH_CONFIDENCE = 0.85      # Early stop threshold
MEDIUM_CONFIDENCE = 0.70    # Good confidence
LOW_CONFIDENCE = 0.60       # Continue if below

# Probability smoothing
SMOOTHING_FACTOR = 0.01     # Laplace smoothing
```

---

## 🔬 Algorithm Details

### Information Gain Calculation
```
IG(D,S) = H(D) - E[H(D|S)]
        = H(D) - [P(S) × H(D|S=yes) + P(¬S) × H(D|S=no)]

where H(D) = -Σ P(d) × log₂(P(d))  # Shannon Entropy
```

### Posterior Update (Bayes' Rule)
```
P(D|S⁺,S⁻) ∝ P(D) × ∏ P(sᵢ|D) × ∏ (1 - P(sⱼ|D))
                   sᵢ∈S⁺       sⱼ∈S⁻

where:
- S⁺ = confirmed symptoms
- S⁻ = denied symptoms  
- P(D) = disease prior
- P(s|D) = symptom likelihood
```

---

## 📦 New Dependencies

```txt
# SOTA NLP
transformers>=4.35.0
torch>=2.0.0

# HuggingFace Data
datasets>=2.14.0
huggingface_hub>=0.19.0

# Medical Images
torchvision>=0.15.0
timm>=0.9.0  # Pre-trained medical models

# OCR
pytesseract>=0.3.10
PyMuPDF>=1.23.0
```

---

## 🧪 Testing

### Quick Validation
```python
from engines.symptom_elimination import SymptomEliminationEngine

engine = SymptomEliminationEngine()
state = engine.start(["fever", "headache", "body ache"])
print(f"Initial predictions: {state['probabilities'][:3]}")

# Answer questions
state = engine.update(state, "yes", "chills")
state = engine.update(state, "no", "cough")
state = engine.update(state, "yes", "sweating")

print(f"Status: {state['status']}")
if state['status'] == 'FINISHED':
    print(f"Predictions: {state['final_predictions']}")
```

### Expected Behavior
- 3 minimum questions always asked
- Stops at 5 if top confidence ≥ 85%
- Continues to 7 if confidence < 60%
- Never exceeds 7 questions

---

## 📚 References

1. **DDXPlus Dataset**: https://huggingface.co/datasets/mila-iqia/ddxplus
   - 1.3M synthetic patient cases
   - 49 pathologies, 223 symptoms
   - NeurIPS 2022

2. **Bio_ClinicalBERT**: https://huggingface.co/emilyalsentzer/Bio_ClinicalBERT
   - Pre-trained on MIMIC-III clinical notes
   - Fine-tuned from BioBERT

3. **DenseNet121 for Medical Imaging**:
   - CheXNet-style X-ray analysis
   - Pre-trained on NIH Chest X-ray dataset

---

## ⚠️ Disclaimer

This system is for **educational purposes** and **assistive insights only**. It is NOT a replacement for professional medical diagnosis, advice, or treatment. Always consult qualified healthcare providers.

---

*Last Updated: AI Medical Assist Team - B.Tech IT Major Project*
