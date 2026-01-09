# Viva Questions & Answers - AI Telemedicine CDSS

## 🎯 Core Architecture Questions

### ❓ Why not ML-based diagnosis?

> "Diagnosis requires large, validated clinical datasets and regulatory approval (FDA, CE marking). This project focuses on **clinical decision support and triage**, not diagnosis. We assist doctors, not replace them."

### ❓ Why Bayesian inference instead of deep learning?

> "Bayesian reasoning is **interpretable**, works with **small datasets**, and **mirrors how clinicians reason** under uncertainty. Deep learning requires millions of samples and produces black-box outputs that are risky in healthcare."

### ❓ How is this Explainable AI without SHAP/LIME?

> "Each probability is derived from **explicit symptom likelihoods**. We show exactly which symptoms contributed to each prediction using our own contribution scoring:
> ```
> P(Disease | Symptoms) ∝ P(Symptoms | Disease) × P(Disease)
> ```
> No black-box. No paid libraries."

---

## 🔒 Safety & Ethics Questions

### ❓ How do you handle critical symptoms?

> "We have a **deterministic rule-based safety layer** (`red_flags.json`) that detects 15 critical symptoms like chest pain, difficulty breathing, or confusion. These trigger immediate escalation regardless of Bayesian scores."

### ❓ What if the AI is wrong?

> "The system is designed as **assistive**, not diagnostic. Every output states 'This is not a medical diagnosis. Please consult a licensed doctor.' We also require doctor validation before any treatment recommendation."

### ❓ How do you handle consent?

> "We have a **consent middleware** that blocks all AI requests without explicit user consent. The timestamp is logged for audit purposes. No medical data is processed without informed consent."

---

## 🧠 Technical Questions

### ❓ How does the symptom elimination engine work?

> "We use **iterative Bayesian elimination**:
> 1. User enters symptoms → Extract keywords
> 2. Calculate P(Disease | Symptoms) for all diseases
> 3. Select follow-up question with **maximum information gain** (entropy reduction)
> 4. Update probabilities based on answer
> 5. Repeat until confidence threshold reached or max questions asked"

### ❓ Why Bio_ClinicalBERT?

> "It's **pretrained on clinical notes** (MIMIC-III), understands medical terminology, and is free. We use it for:
> - Symptom extraction from free text
> - Semantic similarity matching
> - Report text understanding"

### ❓ How do you handle API failures?

> "Multi-level fallback:
> 1. **Local engine** for core symptom logic (always works)
> 2. **Gemini Pro** for summaries/explanations
> 3. **OpenRouter** as secondary API fallback
> 4. **Template-based** responses if all APIs fail
> 
> The core CDSS never depends on external APIs."

### ❓ What if rate limits are exceeded?

> "We implement:
> - **Exponential backoff** with 3 retry attempts
> - **Request throttling** at the backend
> - **Graceful degradation** to template responses
> - **Local processing** for core logic"

---

## 📊 Data Questions

### ❓ Where does your disease-symptom data come from?

> "We built a **curated knowledge base** from medical literature and clinical guidelines. It's small (~90 entries), explainable, and editable. We avoided noisy Kaggle datasets that would compromise explainability."

### ❓ Why synthetic reports?

> "Real patient data has **legal and privacy issues** (HIPAA, GDPR). Synthetic data:
> - Is legally safe
> - Demonstrates the same functionality
> - Can be validated by medical professionals
> - Is sufficient for academic evaluation"

### ❓ How do you evaluate accuracy?

> "We compute:
> - **Top-1 Accuracy**: Is the correct disease the top prediction?
> - **Top-3 Accuracy**: Is the correct disease in top 3?
> - **Mean Reciprocal Rank (MRR)**: Average inverse rank of correct answer
> 
> Using `evaluation/synthetic_cases.csv` with 30+ test cases."

---

## 🏗️ Architecture Questions

### ❓ Why microservices (Node.js + Python)?

> "**Separation of concerns**:
> - Node.js/Express: API gateway, auth, file handling
> - Python/FastAPI: AI/ML processing, NLP, OCR
> 
> This allows independent scaling and technology flexibility."

### ❓ Why Redis for sessions?

> "Symptom elimination is **stateful** (multi-turn conversation). Redis provides:
> - Fast in-memory access
> - TTL for automatic cleanup
> - Scalability across instances"

### ❓ How does the AI router work?

> ```python
> if task == "symptom_logic":
>     return local_engine(text)  # Always local
> if task == "report_summary":
>     try: return gemini(text)
>     except: return template(text)
> ```
> Core logic is always local. APIs are for enhancement only."

---

## 🩺 Medical Questions

### ❓ How do you handle overlapping symptoms?

> "Bayesian inference naturally handles this. If fever appears in Dengue, Malaria, and Typhoid, the system asks **discriminating questions** (e.g., 'Do you have chills?') to differentiate. Information gain calculation ensures we ask the most useful question."

### ❓ What lab values do you parse?

> "30+ common tests including:
> - CBC: Hemoglobin, WBC, Platelets
> - Metabolic: Glucose, Creatinine, BUN
> - Lipid: Cholesterol, LDL, HDL, Triglycerides
> - Liver: ALT, AST, Bilirubin
> - Thyroid: TSH, T3, T4
> - Electrolytes: Sodium, Potassium, Calcium"

### ❓ How do you detect abnormal values?

> "We maintain a `lab_reference_ranges.json` with normal ranges by gender/age. Values outside range are flagged with severity (LOW/HIGH/CRITICAL)."

---

## 💡 Innovation Questions

### ❓ What makes this different from symptom checkers online?

> "1. **Iterative questioning** (not one-shot prediction)
> 2. **Explainable** (shows which symptoms matter)
> 3. **Medical report analysis** (OCR + parsing)
> 4. **Doctor-in-the-loop** architecture
> 5. **Red-flag safety layer**
> 6. **Model-agnostic** (works with/without APIs)"

### ❓ What's the innovation in your XAI approach?

> "We achieve explainability **without expensive libraries** by:
> 1. Tracking probability changes per symptom
> 2. Computing contribution scores
> 3. Maintaining a trace log of all updates
> 4. Showing 'why' alongside 'what'"

---

## 📝 Quick Reference Card

| Question | Key Answer |
|----------|------------|
| Why not ML diagnosis? | Needs FDA approval, large data, risky |
| Why Bayesian? | Interpretable, works with small data |
| XAI without SHAP? | Explicit symptom contributions |
| API failures? | Local engine always works, fallbacks |
| Why synthetic data? | Legal safety, same functionality |
| Why microservices? | Separation of concerns, scalability |
| Core innovation? | Iterative elimination + explainability |
