"""
Symptom Elimination Engine

Core AI logic for iterative disease narrowing using Bayesian inference.

Workflow:
1. Start with all diseases (uniform or weighted prior)
2. Extract symptoms from user input
3. Apply symptom weights using P(D|S) ∝ P(S|D) × P(D)
4. Ask best next question (highest information gain)
5. Update probabilities based on answers
6. Repeat until confidence threshold or max questions

NOT a diagnostic system - provides assistive insights only.
"""

import os
import re
import csv
import json
import math
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Path to knowledge base
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class SymptomEliminationEngine:
    """
    Bayesian symptom elimination engine for disease probability estimation.
    
    Uses P(D|S) ∝ P(S|D) × P(D) for probability updates.
    """
    
    def __init__(self):
        """Initialize engine with knowledge base."""
        self.disease_symptoms = self._load_disease_symptoms()
        self.red_flags = self._load_red_flags()
        self.symptom_questions = self._load_symptom_questions()
        self.diseases = list(set(d["disease"] for d in self.disease_symptoms))
        self.symptoms = list(set(d["symptom"] for d in self.disease_symptoms))
        
        # Build likelihood matrix P(S|D)
        self.likelihood_matrix = self._build_likelihood_matrix()
        
        # Symptom synonyms for extraction
        self.symptom_synonyms = self._load_symptom_synonyms()
    
    def _load_disease_symptoms(self) -> List[Dict]:
        """Load disease-symptom relationships from CSV."""
        data = []
        csv_path = KNOWLEDGE_DIR / "disease_symptom.csv"
        
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append({
                        "disease": row["disease"],
                        "symptom": row["symptom"].lower(),
                        "weight": float(row.get("weight", 0.5))
                    })
        else:
            # Default data if CSV not found
            data = self._get_default_disease_symptoms()
        
        return data
    
    def _get_default_disease_symptoms(self) -> List[Dict]:
        """Default disease-symptom data for demo."""
        return [
            # Dengue
            {"disease": "Dengue", "symptom": "fever", "weight": 0.95},
            {"disease": "Dengue", "symptom": "headache", "weight": 0.85},
            {"disease": "Dengue", "symptom": "body ache", "weight": 0.80},
            {"disease": "Dengue", "symptom": "joint pain", "weight": 0.75},
            {"disease": "Dengue", "symptom": "rash", "weight": 0.50},
            {"disease": "Dengue", "symptom": "nausea", "weight": 0.45},
            
            # Malaria
            {"disease": "Malaria", "symptom": "fever", "weight": 0.95},
            {"disease": "Malaria", "symptom": "chills", "weight": 0.90},
            {"disease": "Malaria", "symptom": "sweating", "weight": 0.75},
            {"disease": "Malaria", "symptom": "headache", "weight": 0.70},
            {"disease": "Malaria", "symptom": "fatigue", "weight": 0.65},
            
            # Common Cold
            {"disease": "Common Cold", "symptom": "runny nose", "weight": 0.90},
            {"disease": "Common Cold", "symptom": "sneezing", "weight": 0.85},
            {"disease": "Common Cold", "symptom": "sore throat", "weight": 0.80},
            {"disease": "Common Cold", "symptom": "cough", "weight": 0.70},
            {"disease": "Common Cold", "symptom": "mild fever", "weight": 0.40},
            
            # Flu (Influenza)
            {"disease": "Influenza", "symptom": "fever", "weight": 0.90},
            {"disease": "Influenza", "symptom": "body ache", "weight": 0.85},
            {"disease": "Influenza", "symptom": "fatigue", "weight": 0.80},
            {"disease": "Influenza", "symptom": "cough", "weight": 0.75},
            {"disease": "Influenza", "symptom": "headache", "weight": 0.70},
            
            # COVID-19
            {"disease": "COVID-19", "symptom": "fever", "weight": 0.85},
            {"disease": "COVID-19", "symptom": "cough", "weight": 0.80},
            {"disease": "COVID-19", "symptom": "loss of taste", "weight": 0.75},
            {"disease": "COVID-19", "symptom": "loss of smell", "weight": 0.75},
            {"disease": "COVID-19", "symptom": "fatigue", "weight": 0.70},
            {"disease": "COVID-19", "symptom": "shortness of breath", "weight": 0.60},
            
            # Typhoid
            {"disease": "Typhoid", "symptom": "fever", "weight": 0.95},
            {"disease": "Typhoid", "symptom": "abdominal pain", "weight": 0.80},
            {"disease": "Typhoid", "symptom": "headache", "weight": 0.70},
            {"disease": "Typhoid", "symptom": "weakness", "weight": 0.65},
            {"disease": "Typhoid", "symptom": "constipation", "weight": 0.50},
            
            # Gastroenteritis
            {"disease": "Gastroenteritis", "symptom": "diarrhea", "weight": 0.90},
            {"disease": "Gastroenteritis", "symptom": "vomiting", "weight": 0.85},
            {"disease": "Gastroenteritis", "symptom": "abdominal pain", "weight": 0.80},
            {"disease": "Gastroenteritis", "symptom": "nausea", "weight": 0.75},
            {"disease": "Gastroenteritis", "symptom": "fever", "weight": 0.50},
            
            # Migraine
            {"disease": "Migraine", "symptom": "severe headache", "weight": 0.95},
            {"disease": "Migraine", "symptom": "nausea", "weight": 0.70},
            {"disease": "Migraine", "symptom": "light sensitivity", "weight": 0.75},
            {"disease": "Migraine", "symptom": "vision changes", "weight": 0.50},
        ]
    
    def _load_red_flags(self) -> List[Dict]:
        """Load red flag symptoms that require immediate attention."""
        json_path = KNOWLEDGE_DIR / "red_flags.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Default red flags
        return [
            {"symptom": "chest pain", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "difficulty breathing", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "shortness of breath", "severity": "high", "action": "Consult doctor urgently"},
            {"symptom": "severe headache", "severity": "high", "action": "Consult doctor urgently"},
            {"symptom": "confusion", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "loss of consciousness", "severity": "critical", "action": "Call emergency services"},
            {"symptom": "severe bleeding", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "high fever", "severity": "high", "action": "Consult doctor within 24 hours"},
            {"symptom": "persistent vomiting", "severity": "high", "action": "Consult doctor urgently"},
        ]
    
    def _load_symptom_questions(self) -> Dict[str, Dict]:
        """Load follow-up questions for symptoms."""
        json_path = KNOWLEDGE_DIR / "symptom_questions.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Default questions
        return {
            "fever": {
                "text": "How high is your fever?",
                "options": ["Mild (99-100°F)", "Moderate (100-102°F)", "High (>102°F)", "Not sure"]
            },
            "headache": {
                "text": "How would you describe your headache?",
                "options": ["Mild", "Throbbing/Pulsating", "Severe", "With nausea"]
            },
            "cough": {
                "text": "What type of cough do you have?",
                "options": ["Dry cough", "Wet/productive cough", "With blood", "Persistent"]
            },
            "body ache": {
                "text": "Where do you feel the body aches most?",
                "options": ["Joints", "Muscles", "All over", "Back"]
            },
            "fatigue": {
                "text": "How severe is your fatigue?",
                "options": ["Mild tiredness", "Moderate - affecting daily activities", "Severe - bed-bound", "With dizziness"]
            },
            "rash": {
                "text": "Describe the rash:",
                "options": ["Red spots", "Itchy", "Spreading", "With fever"]
            },
            "nausea": {
                "text": "Is the nausea accompanied by:",
                "options": ["Vomiting", "Abdominal pain", "Loss of appetite", "None of these"]
            },
            "duration": {
                "text": "How long have you had these symptoms?",
                "options": ["Less than 24 hours", "1-3 days", "4-7 days", "More than a week"]
            }
        }
    
    def _load_symptom_synonyms(self) -> Dict[str, List[str]]:
        """Load symptom synonyms for better extraction."""
        return {
            "fever": ["fever", "temperature", "hot", "feverish", "pyrexia", "febrile"],
            "headache": ["headache", "head pain", "head ache", "migraine", "head hurts"],
            "cough": ["cough", "coughing", "dry cough", "wet cough"],
            "body ache": ["body ache", "body pain", "muscle pain", "aching", "soreness"],
            "fatigue": ["fatigue", "tired", "exhausted", "weakness", "weak", "lethargy"],
            "fever": ["fever", "high temperature", "pyrexia"],
            "chills": ["chills", "shivering", "cold sweats", "rigors"],
            "nausea": ["nausea", "nauseous", "queasy", "sick feeling"],
            "vomiting": ["vomiting", "vomit", "throwing up", "puking"],
            "diarrhea": ["diarrhea", "loose stools", "watery stools", "loose motion"],
            "rash": ["rash", "skin rash", "spots", "eruption"],
            "sore throat": ["sore throat", "throat pain", "painful throat"],
            "runny nose": ["runny nose", "nasal discharge", "stuffy nose", "blocked nose"],
            "joint pain": ["joint pain", "joint ache", "arthralgia"],
            "chest pain": ["chest pain", "chest tightness", "chest discomfort"],
            "shortness of breath": ["shortness of breath", "breathless", "difficulty breathing", "dyspnea"],
            "loss of taste": ["loss of taste", "can't taste", "ageusia"],
            "loss of smell": ["loss of smell", "can't smell", "anosmia"],
            "abdominal pain": ["abdominal pain", "stomach pain", "belly pain", "stomach ache"],
        }
    
    def _build_likelihood_matrix(self) -> Dict[str, Dict[str, float]]:
        """Build P(S|D) matrix from disease-symptom data."""
        matrix = {}
        
        for disease in self.diseases:
            matrix[disease] = {}
            disease_symptoms = [d for d in self.disease_symptoms if d["disease"] == disease]
            
            for symptom in self.symptoms:
                # Find weight for this symptom-disease pair
                match = next((d for d in disease_symptoms if d["symptom"] == symptom), None)
                matrix[disease][symptom] = match["weight"] if match else 0.01  # Small prior for unknown
        
        return matrix
    
    def extract_symptoms(self, text: str) -> Dict[str, Any]:
        """
        Extract symptoms from free-text input.
        
        Uses synonym matching and basic NLP patterns.
        In production, would use Bio_ClinicalBERT.
        """
        text_lower = text.lower()
        found_symptoms = []
        entities = []
        
        for canonical, synonyms in self.symptom_synonyms.items():
            for synonym in synonyms:
                if synonym in text_lower:
                    if canonical not in found_symptoms:
                        found_symptoms.append(canonical)
                        entities.append({
                            "text": synonym,
                            "label": canonical,
                            "start": text_lower.find(synonym),
                            "end": text_lower.find(synonym) + len(synonym)
                        })
                    break
        
        # Extract duration patterns
        duration_patterns = [
            r"(\d+)\s*days?",
            r"(\d+)\s*weeks?",
            r"since\s+(\w+)",
            r"for\s+(\d+\s*\w+)"
        ]
        
        duration = None
        for pattern in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                duration = match.group(0)
                break
        
        return {
            "symptoms": found_symptoms,
            "entities": entities,
            "duration": duration,
            "original_text": text
        }
    
    def check_red_flags(self, symptoms: List[str]) -> List[str]:
        """Check for critical/red flag symptoms."""
        warnings = []
        
        for flag in self.red_flags:
            if flag["symptom"] in symptoms:
                warnings.append(f"⚠️ {flag['symptom'].upper()}: {flag['action']}")
        
        return warnings
    
    def start(self, symptoms: List[str]) -> Dict[str, Any]:
        """
        Initialize triage session with extracted symptoms.
        
        Returns initial state with disease probabilities.
        """
        # Initialize uniform prior P(D)
        num_diseases = len(self.diseases)
        prior = {d: 1.0 / num_diseases for d in self.diseases}
        
        # Update with initial symptoms
        posterior = self._compute_posterior(prior, symptoms)
        
        # Sort by probability
        sorted_probs = sorted(
            [{"disease": d, "probability": p} for d, p in posterior.items()],
            key=lambda x: x["probability"],
            reverse=True
        )
        
        return {
            "probabilities": sorted_probs,
            "posterior": posterior,
            "observed_symptoms": symptoms,
            "asked_questions": [],
            "answers": {},
            "candidate_questions": self._get_candidate_questions(symptoms)
        }
    
    def _compute_posterior(
        self, 
        prior: Dict[str, float], 
        symptoms: List[str],
        negative_symptoms: List[str] = None
    ) -> Dict[str, float]:
        """
        Compute posterior P(D|S) using Bayes' rule.
        
        P(D|S) ∝ P(S|D) × P(D)
        """
        negative_symptoms = negative_symptoms or []
        posterior = {}
        
        for disease in self.diseases:
            # Start with prior
            prob = prior[disease]
            
            # Multiply by likelihood for each observed symptom
            for symptom in symptoms:
                likelihood = self.likelihood_matrix.get(disease, {}).get(symptom, 0.01)
                prob *= likelihood
            
            # Reduce probability for negative symptoms (user said "no")
            for neg_symptom in negative_symptoms:
                likelihood = self.likelihood_matrix.get(disease, {}).get(neg_symptom, 0.01)
                prob *= (1 - likelihood * 0.5)  # Partial reduction
            
            posterior[disease] = prob
        
        # Normalize
        total = sum(posterior.values())
        if total > 0:
            posterior = {d: p / total for d, p in posterior.items()}
        
        return posterior
    
    def _get_candidate_questions(self, observed: List[str]) -> List[str]:
        """Get symptoms we haven't asked about yet."""
        all_symptoms = set(self.symptoms)
        observed_set = set(observed)
        return list(all_symptoms - observed_set)
    
    def next_question(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Select next question based on expected information gain.
        
        Returns question that maximizes entropy reduction.
        """
        candidates = state.get("candidate_questions", [])
        asked = state.get("asked_questions", [])
        
        # Filter out already asked
        remaining = [q for q in candidates if q not in asked]
        
        if not remaining:
            return None
        
        # Calculate information gain for each candidate
        best_question = None
        best_gain = -1
        
        posterior = state["posterior"]
        
        for symptom in remaining[:10]:  # Limit computation
            gain = self._expected_information_gain(posterior, symptom)
            if gain > best_gain:
                best_gain = gain
                best_question = symptom
        
        if best_question is None:
            return None
        
        # Get question template
        question_data = self.symptom_questions.get(best_question, {
            "text": f"Do you have {best_question}?",
            "options": ["Yes", "No", "Not sure"]
        })
        
        return {
            "symptom": best_question,
            "text": question_data["text"],
            "options": question_data["options"]
        }
    
    def _expected_information_gain(
        self, 
        posterior: Dict[str, float], 
        symptom: str
    ) -> float:
        """
        Calculate expected information gain for asking about a symptom.
        
        Uses entropy reduction as the metric.
        """
        # Current entropy
        current_entropy = self._entropy(list(posterior.values()))
        
        # Estimate P(symptom = yes) across diseases
        p_yes = sum(
            posterior[d] * self.likelihood_matrix.get(d, {}).get(symptom, 0.1)
            for d in self.diseases
        )
        p_no = 1 - p_yes
        
        # Clamp probabilities
        p_yes = max(0.01, min(0.99, p_yes))
        p_no = max(0.01, min(0.99, p_no))
        
        # Expected entropy after asking
        # If answer is yes
        posterior_yes = {
            d: posterior[d] * self.likelihood_matrix.get(d, {}).get(symptom, 0.1)
            for d in self.diseases
        }
        total_yes = sum(posterior_yes.values())
        if total_yes > 0:
            posterior_yes = {d: p / total_yes for d, p in posterior_yes.items()}
        entropy_yes = self._entropy(list(posterior_yes.values()))
        
        # If answer is no
        posterior_no = {
            d: posterior[d] * (1 - self.likelihood_matrix.get(d, {}).get(symptom, 0.1) * 0.5)
            for d in self.diseases
        }
        total_no = sum(posterior_no.values())
        if total_no > 0:
            posterior_no = {d: p / total_no for d, p in posterior_no.items()}
        entropy_no = self._entropy(list(posterior_no.values()))
        
        # Expected entropy
        expected_entropy = p_yes * entropy_yes + p_no * entropy_no
        
        # Information gain
        return current_entropy - expected_entropy
    
    def _entropy(self, probs: List[float]) -> float:
        """Calculate entropy of probability distribution."""
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
    
    def update(self, state: Dict[str, Any], answer: str) -> Dict[str, Any]:
        """
        Update probabilities based on user's answer.
        """
        # Get current question
        candidates = state.get("candidate_questions", [])
        asked = state.get("asked_questions", [])
        remaining = [q for q in candidates if q not in asked]
        
        if not remaining:
            return state
        
        # Find which symptom was asked
        current_symptom = None
        for symptom in remaining[:10]:
            gain = self._expected_information_gain(state["posterior"], symptom)
            if current_symptom is None:
                current_symptom = symptom
                break
        
        if current_symptom is None:
            return state
        
        # Interpret answer
        answer_lower = answer.lower()
        observed = state.get("observed_symptoms", [])
        negative = state.get("negative_symptoms", [])
        
        if "yes" in answer_lower or answer_lower in ["mild", "moderate", "severe"]:
            observed = observed + [current_symptom]
        elif "no" in answer_lower:
            negative = negative + [current_symptom]
        # "Not sure" doesn't update
        
        # Recompute posterior
        prior = {d: 1.0 / len(self.diseases) for d in self.diseases}
        posterior = self._compute_posterior(prior, observed, negative)
        
        # Sort by probability
        sorted_probs = sorted(
            [{"disease": d, "probability": p} for d, p in posterior.items()],
            key=lambda x: x["probability"],
            reverse=True
        )
        
        # Update state
        new_state = {
            "probabilities": sorted_probs,
            "posterior": posterior,
            "observed_symptoms": observed,
            "negative_symptoms": negative,
            "asked_questions": asked + [current_symptom],
            "answers": {**state.get("answers", {}), current_symptom: answer},
            "candidate_questions": candidates,
            "last_question": current_symptom
        }
        
        return new_state
