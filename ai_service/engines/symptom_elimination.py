"""
Symptom Elimination Engine (SOTA Version)
==========================================

Advanced Bayesian inference engine for medical symptom analysis.
Implements the 3-5-7 Question Rule for optimal diagnosis.

Features:
- Probabilistic reasoning using Bayes' theorem
- Information gain-based question selection
- Adaptive questioning (3 min, 5 soft max, 7 hard max)
- Red flag detection for emergency symptoms
- Trained on DDXPlus dataset probabilities
- Optional Bio_ClinicalBERT for NLP extraction

Question Logic (3-5-7 Rule):
- Min 3 questions: Always ask minimum 3 questions
- 3-5 questions: Stop if confidence > 85%
- 5-7 questions: Continue if confidence < 60%
- Max 7 questions: Hard stop

NOT a diagnostic system - provides assistive insights only.

Author: AI Medical Assist Team
Version: 2.0.0 (SOTA)
"""

import os
import re
import csv
import json
import math
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to knowledge base
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# Optional Bio_ClinicalBERT NLP
_nlp_extractor = None

# Optional SapBERT for symptom normalization
_sapbert_adapter = None

def get_nlp_extractor():
    """Lazy-load Bio_ClinicalBERT extractor."""
    global _nlp_extractor
    if _nlp_extractor is None:
        try:
            from model_adapters.bio_clinicalbert import BioClinicalBERT
            _nlp_extractor = BioClinicalBERT(use_api=False)
            logger.info("Bio_ClinicalBERT NLP extractor loaded")
        except Exception as e:
            logger.info(f"Bio_ClinicalBERT not available, using rule-based: {e}")
            _nlp_extractor = False  # Mark as unavailable
    return _nlp_extractor if _nlp_extractor else None


def get_sapbert_adapter():
    """Lazy-load SapBERT adapter for symptom normalization."""
    global _sapbert_adapter
    if _sapbert_adapter is None:
        try:
            from model_adapters.sapbert_ddxplus import SapBERTDDXPlusAdapter
            _sapbert_adapter = SapBERTDDXPlusAdapter(use_local=True)
            if _sapbert_adapter.initialize():
                logger.info("SapBERT-DDXPlus adapter loaded for symptom normalization")
            else:
                _sapbert_adapter = False
        except Exception as e:
            logger.info(f"SapBERT not available: {e}")
            _sapbert_adapter = False
    return _sapbert_adapter if _sapbert_adapter else None


class SessionStatus(Enum):
    """Triage session status."""
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    EMERGENCY = "EMERGENCY"


class SymptomEliminationEngine:
    """
    Advanced Bayesian Symptom Elimination Engine (SOTA).
    
    Implements adaptive questioning with the 3-5-7 rule:
    - Minimum 3 questions always
    - Stop at 5 if high confidence (>85%)
    - Extend to 7 if low confidence (<60%)
    - Hard stop at 7 questions
    
    Uses P(D|S) ∝ P(S|D) × P(D) for probability updates.
    
    Optional: Bio_ClinicalBERT for NLP symptom extraction (~90% accuracy)
    """
    
    # ===== 3-5-7 QUESTION RULE CONSTANTS =====
    MIN_QUESTIONS = 3           # Minimum questions to always ask
    SOFT_MAX_QUESTIONS = 5      # Stop here if confidence > 85%
    HARD_MAX_QUESTIONS = 7      # Absolute maximum questions
    
    # ===== CONFIDENCE THRESHOLDS =====
    HIGH_CONFIDENCE = 0.85      # Stop early if above this
    MEDIUM_CONFIDENCE = 0.70    # Good confidence level
    LOW_CONFIDENCE = 0.60       # Must continue if below this
    
    # ===== PROBABILITY CONSTANTS =====
    SMOOTHING_FACTOR = 0.01     # Laplace smoothing
    
    def __init__(self, use_bert_nlp: bool = False):
        """
        Initialize engine with knowledge base.
        
        Args:
            use_bert_nlp: Use Bio_ClinicalBERT for symptom extraction (requires GPU/API)
        """
        self.use_bert_nlp = use_bert_nlp
        # Initialize caches first (before loading data)
        self.info_gain_cache = {}
        
        # Load data
        self.disease_symptoms = self._load_disease_symptoms()
        self.red_flags = self._load_red_flags()
        self.symptom_questions = self._load_symptom_questions()
        self.diseases = list(set(d["disease"] for d in self.disease_symptoms))
        self.symptoms = list(set(d["symptom"] for d in self.disease_symptoms))
        
        # Build likelihood matrix P(S|D)
        self.likelihood_matrix = self._build_likelihood_matrix()
        
        # Symptom synonyms for extraction
        self.symptom_synonyms = self._load_symptom_synonyms()
        
        # Disease priors P(D)
        self.disease_priors = self._load_disease_priors()
        
        logger.info(f"Engine initialized: {len(self.diseases)} diseases, {len(self.symptoms)} symptoms")
    
    def _load_disease_symptoms(self) -> List[Dict]:
        """Load disease-symptom relationships from trained CSV."""
        data = []
        
        # Try trained data first (from DDXPlus or medical literature)
        trained_csv = KNOWLEDGE_DIR / "disease_symptom_trained.csv"
        original_csv = KNOWLEDGE_DIR / "disease_symptom.csv"
        
        csv_path = trained_csv if trained_csv.exists() else original_csv
        
        if csv_path.exists():
            logger.info(f"Loading from: {csv_path.name}")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append({
                        "disease": row["disease"],
                        "symptom": row["symptom"].lower(),
                        "weight": float(row.get("weight", 0.5)),
                        "info_gain": float(row.get("info_gain", 0.0)) if "info_gain" in row else 0.0
                    })
                    # Cache info gain
                    if "info_gain" in row and row["info_gain"]:
                        self.info_gain_cache[row["symptom"].lower()] = float(row["info_gain"])
        else:
            logger.warning("No trained data found. Using default knowledge base.")
            data = self._get_default_disease_symptoms()
        
        return data
    
    def _load_disease_priors(self) -> Dict[str, float]:
        """Load disease priors P(D) from trained data."""
        priors_path = KNOWLEDGE_DIR / "disease_priors.json"
        
        if priors_path.exists():
            with open(priors_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Uniform priors if no trained data
        n = len(self.diseases)
        return {d: 1.0/n for d in self.diseases}
    
    def _get_default_disease_symptoms(self) -> List[Dict]:
        """
        Default disease-symptom data based on medical literature.
        
        Probabilities are epidemiologically-informed estimates.
        In production, use trained data from DDXPlus dataset.
        """
        return [
            # ===== DENGUE (Vector-borne) =====
            {"disease": "Dengue", "symptom": "fever", "weight": 0.95},
            {"disease": "Dengue", "symptom": "headache", "weight": 0.85},
            {"disease": "Dengue", "symptom": "body ache", "weight": 0.80},
            {"disease": "Dengue", "symptom": "joint pain", "weight": 0.75},
            {"disease": "Dengue", "symptom": "rash", "weight": 0.50},
            {"disease": "Dengue", "symptom": "nausea", "weight": 0.45},
            {"disease": "Dengue", "symptom": "fatigue", "weight": 0.70},
            {"disease": "Dengue", "symptom": "eye pain", "weight": 0.55},
            
            # ===== MALARIA (Vector-borne) =====
            {"disease": "Malaria", "symptom": "fever", "weight": 0.95},
            {"disease": "Malaria", "symptom": "chills", "weight": 0.90},
            {"disease": "Malaria", "symptom": "sweating", "weight": 0.75},
            {"disease": "Malaria", "symptom": "headache", "weight": 0.70},
            {"disease": "Malaria", "symptom": "fatigue", "weight": 0.65},
            {"disease": "Malaria", "symptom": "nausea", "weight": 0.50},
            {"disease": "Malaria", "symptom": "vomiting", "weight": 0.40},
            {"disease": "Malaria", "symptom": "muscle pain", "weight": 0.55},
            
            # ===== COMMON COLD (Viral URI) =====
            {"disease": "Common Cold", "symptom": "runny nose", "weight": 0.90},
            {"disease": "Common Cold", "symptom": "sneezing", "weight": 0.85},
            {"disease": "Common Cold", "symptom": "sore throat", "weight": 0.80},
            {"disease": "Common Cold", "symptom": "cough", "weight": 0.70},
            {"disease": "Common Cold", "symptom": "mild fever", "weight": 0.40},
            {"disease": "Common Cold", "symptom": "congestion", "weight": 0.75},
            {"disease": "Common Cold", "symptom": "watery eyes", "weight": 0.35},
            
            # ===== INFLUENZA (Flu) =====
            {"disease": "Influenza", "symptom": "fever", "weight": 0.90},
            {"disease": "Influenza", "symptom": "body ache", "weight": 0.85},
            {"disease": "Influenza", "symptom": "fatigue", "weight": 0.80},
            {"disease": "Influenza", "symptom": "cough", "weight": 0.75},
            {"disease": "Influenza", "symptom": "headache", "weight": 0.70},
            {"disease": "Influenza", "symptom": "chills", "weight": 0.65},
            {"disease": "Influenza", "symptom": "sore throat", "weight": 0.50},
            {"disease": "Influenza", "symptom": "runny nose", "weight": 0.45},
            
            # ===== COVID-19 =====
            {"disease": "COVID-19", "symptom": "fever", "weight": 0.85},
            {"disease": "COVID-19", "symptom": "cough", "weight": 0.80},
            {"disease": "COVID-19", "symptom": "loss of taste", "weight": 0.75},
            {"disease": "COVID-19", "symptom": "loss of smell", "weight": 0.75},
            {"disease": "COVID-19", "symptom": "fatigue", "weight": 0.70},
            {"disease": "COVID-19", "symptom": "shortness of breath", "weight": 0.60},
            {"disease": "COVID-19", "symptom": "body ache", "weight": 0.55},
            {"disease": "COVID-19", "symptom": "headache", "weight": 0.50},
            {"disease": "COVID-19", "symptom": "sore throat", "weight": 0.45},
            
            # ===== TYPHOID =====
            {"disease": "Typhoid", "symptom": "fever", "weight": 0.95},
            {"disease": "Typhoid", "symptom": "abdominal pain", "weight": 0.80},
            {"disease": "Typhoid", "symptom": "headache", "weight": 0.70},
            {"disease": "Typhoid", "symptom": "weakness", "weight": 0.65},
            {"disease": "Typhoid", "symptom": "constipation", "weight": 0.50},
            {"disease": "Typhoid", "symptom": "loss of appetite", "weight": 0.60},
            {"disease": "Typhoid", "symptom": "rose spots", "weight": 0.30},
            
            # ===== GASTROENTERITIS =====
            {"disease": "Gastroenteritis", "symptom": "diarrhea", "weight": 0.90},
            {"disease": "Gastroenteritis", "symptom": "vomiting", "weight": 0.85},
            {"disease": "Gastroenteritis", "symptom": "abdominal pain", "weight": 0.80},
            {"disease": "Gastroenteritis", "symptom": "nausea", "weight": 0.75},
            {"disease": "Gastroenteritis", "symptom": "fever", "weight": 0.50},
            {"disease": "Gastroenteritis", "symptom": "dehydration", "weight": 0.45},
            {"disease": "Gastroenteritis", "symptom": "loss of appetite", "weight": 0.55},
            
            # ===== MIGRAINE =====
            {"disease": "Migraine", "symptom": "severe headache", "weight": 0.95},
            {"disease": "Migraine", "symptom": "headache", "weight": 0.95},
            {"disease": "Migraine", "symptom": "nausea", "weight": 0.70},
            {"disease": "Migraine", "symptom": "light sensitivity", "weight": 0.75},
            {"disease": "Migraine", "symptom": "vision changes", "weight": 0.50},
            {"disease": "Migraine", "symptom": "vomiting", "weight": 0.40},
            {"disease": "Migraine", "symptom": "sound sensitivity", "weight": 0.55},
            
            # ===== PNEUMONIA =====
            {"disease": "Pneumonia", "symptom": "cough", "weight": 0.90},
            {"disease": "Pneumonia", "symptom": "fever", "weight": 0.85},
            {"disease": "Pneumonia", "symptom": "shortness of breath", "weight": 0.80},
            {"disease": "Pneumonia", "symptom": "chest pain", "weight": 0.70},
            {"disease": "Pneumonia", "symptom": "fatigue", "weight": 0.65},
            {"disease": "Pneumonia", "symptom": "chills", "weight": 0.55},
            {"disease": "Pneumonia", "symptom": "difficulty breathing", "weight": 0.60},
            
            # ===== TUBERCULOSIS =====
            {"disease": "Tuberculosis", "symptom": "cough", "weight": 0.85},
            {"disease": "Tuberculosis", "symptom": "night sweats", "weight": 0.80},
            {"disease": "Tuberculosis", "symptom": "weight loss", "weight": 0.75},
            {"disease": "Tuberculosis", "symptom": "fever", "weight": 0.70},
            {"disease": "Tuberculosis", "symptom": "fatigue", "weight": 0.65},
            {"disease": "Tuberculosis", "symptom": "chest pain", "weight": 0.50},
            {"disease": "Tuberculosis", "symptom": "coughing blood", "weight": 0.40},
            
            # ===== URINARY TRACT INFECTION (UTI) =====
            {"disease": "UTI", "symptom": "painful urination", "weight": 0.90},
            {"disease": "UTI", "symptom": "frequent urination", "weight": 0.85},
            {"disease": "UTI", "symptom": "urgency to urinate", "weight": 0.80},
            {"disease": "UTI", "symptom": "lower abdominal pain", "weight": 0.65},
            {"disease": "UTI", "symptom": "cloudy urine", "weight": 0.55},
            {"disease": "UTI", "symptom": "fever", "weight": 0.40},
            
            # ===== HYPERTENSION =====
            {"disease": "Hypertension", "symptom": "headache", "weight": 0.60},
            {"disease": "Hypertension", "symptom": "dizziness", "weight": 0.55},
            {"disease": "Hypertension", "symptom": "blurred vision", "weight": 0.45},
            {"disease": "Hypertension", "symptom": "shortness of breath", "weight": 0.40},
            {"disease": "Hypertension", "symptom": "chest pain", "weight": 0.35},
            {"disease": "Hypertension", "symptom": "fatigue", "weight": 0.50},
            
            # ===== DIABETES TYPE 2 =====
            {"disease": "Diabetes Type 2", "symptom": "frequent urination", "weight": 0.80},
            {"disease": "Diabetes Type 2", "symptom": "excessive thirst", "weight": 0.85},
            {"disease": "Diabetes Type 2", "symptom": "fatigue", "weight": 0.70},
            {"disease": "Diabetes Type 2", "symptom": "blurred vision", "weight": 0.55},
            {"disease": "Diabetes Type 2", "symptom": "slow healing wounds", "weight": 0.50},
            {"disease": "Diabetes Type 2", "symptom": "weight loss", "weight": 0.45},
            
            # ===== APPENDICITIS =====
            {"disease": "Appendicitis", "symptom": "right lower abdominal pain", "weight": 0.90},
            {"disease": "Appendicitis", "symptom": "abdominal pain", "weight": 0.85},
            {"disease": "Appendicitis", "symptom": "nausea", "weight": 0.75},
            {"disease": "Appendicitis", "symptom": "vomiting", "weight": 0.65},
            {"disease": "Appendicitis", "symptom": "fever", "weight": 0.60},
            {"disease": "Appendicitis", "symptom": "loss of appetite", "weight": 0.70},
            
            # ===== ASTHMA =====
            {"disease": "Asthma", "symptom": "shortness of breath", "weight": 0.90},
            {"disease": "Asthma", "symptom": "wheezing", "weight": 0.85},
            {"disease": "Asthma", "symptom": "chest tightness", "weight": 0.80},
            {"disease": "Asthma", "symptom": "cough", "weight": 0.75},
            {"disease": "Asthma", "symptom": "difficulty breathing", "weight": 0.70},
            
            # ===== ALLERGIC RHINITIS =====
            {"disease": "Allergic Rhinitis", "symptom": "sneezing", "weight": 0.90},
            {"disease": "Allergic Rhinitis", "symptom": "runny nose", "weight": 0.85},
            {"disease": "Allergic Rhinitis", "symptom": "itchy eyes", "weight": 0.80},
            {"disease": "Allergic Rhinitis", "symptom": "nasal congestion", "weight": 0.75},
            {"disease": "Allergic Rhinitis", "symptom": "watery eyes", "weight": 0.70},
            
            # ===== ANXIETY DISORDER =====
            {"disease": "Anxiety Disorder", "symptom": "nervousness", "weight": 0.85},
            {"disease": "Anxiety Disorder", "symptom": "restlessness", "weight": 0.80},
            {"disease": "Anxiety Disorder", "symptom": "rapid heartbeat", "weight": 0.75},
            {"disease": "Anxiety Disorder", "symptom": "sweating", "weight": 0.65},
            {"disease": "Anxiety Disorder", "symptom": "difficulty sleeping", "weight": 0.70},
            {"disease": "Anxiety Disorder", "symptom": "difficulty concentrating", "weight": 0.60},
            
            # ===== DEPRESSION =====
            {"disease": "Depression", "symptom": "persistent sadness", "weight": 0.90},
            {"disease": "Depression", "symptom": "fatigue", "weight": 0.80},
            {"disease": "Depression", "symptom": "loss of interest", "weight": 0.85},
            {"disease": "Depression", "symptom": "sleep changes", "weight": 0.75},
            {"disease": "Depression", "symptom": "appetite changes", "weight": 0.65},
            {"disease": "Depression", "symptom": "difficulty concentrating", "weight": 0.60},
        ]
    
    def _load_red_flags(self) -> List[Dict]:
        """Load red flag symptoms that require immediate medical attention."""
        json_path = KNOWLEDGE_DIR / "red_flags.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, dict):
                    return [{"symptom": k, **v} for k, v in data.get("red_flags", data).items()]
                return data
        
        # Default red flags with severity levels
        return [
            {"symptom": "chest pain", "severity": "critical", "action": "Seek emergency care immediately - possible cardiac event"},
            {"symptom": "difficulty breathing", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "shortness of breath", "severity": "high", "action": "Consult doctor urgently"},
            {"symptom": "severe headache", "severity": "high", "action": "Consult doctor urgently - rule out serious conditions"},
            {"symptom": "sudden severe headache", "severity": "critical", "action": "Seek emergency care - possible stroke or aneurysm"},
            {"symptom": "confusion", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "loss of consciousness", "severity": "critical", "action": "Call emergency services (911)"},
            {"symptom": "severe bleeding", "severity": "critical", "action": "Apply pressure and seek emergency care"},
            {"symptom": "high fever", "severity": "high", "action": "Consult doctor within 24 hours"},
            {"symptom": "persistent vomiting", "severity": "high", "action": "Consult doctor urgently - risk of dehydration"},
            {"symptom": "seizure", "severity": "critical", "action": "Call emergency services, protect from injury"},
            {"symptom": "coughing blood", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "sudden vision loss", "severity": "critical", "action": "Seek emergency care immediately"},
            {"symptom": "severe abdominal pain", "severity": "high", "action": "Seek urgent medical attention"},
            {"symptom": "suicidal thoughts", "severity": "critical", "action": "Call crisis helpline or seek immediate help"},
        ]
    
    def _load_symptom_questions(self) -> Dict[str, Dict]:
        """Load follow-up questions for symptoms."""
        # Try trained questions first
        trained_path = KNOWLEDGE_DIR / "symptom_questions_trained.json"
        original_path = KNOWLEDGE_DIR / "symptom_questions.json"
        
        json_path = trained_path if trained_path.exists() else original_path
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Default questions with improved wording
        return {
            "fever": {
                "question": "Do you have a fever or elevated body temperature?",
                "text": "How high is your fever?",
                "options": ["Mild (99-100°F / 37.2-37.8°C)", "Moderate (100-102°F / 37.8-38.9°C)", "High (>102°F / >38.9°C)", "Not sure"]
            },
            "headache": {
                "question": "Are you experiencing any headaches?",
                "text": "How would you describe your headache?",
                "options": ["Mild", "Throbbing/Pulsating", "Severe", "With nausea/light sensitivity"]
            },
            "cough": {
                "question": "Do you have a cough?",
                "text": "What type of cough do you have?",
                "options": ["Dry cough", "Wet/productive cough", "With blood", "Persistent (>2 weeks)"]
            },
            "body ache": {
                "question": "Are you experiencing body aches or muscle pain?",
                "text": "Where do you feel the body aches most?",
                "options": ["Joints", "Muscles", "All over", "Back/Limbs"]
            },
            "fatigue": {
                "question": "Are you feeling unusually tired or fatigued?",
                "text": "How severe is your fatigue?",
                "options": ["Mild tiredness", "Moderate - affecting daily activities", "Severe - bed-bound", "With dizziness"]
            },
            "rash": {
                "question": "Do you have any skin rash or unusual skin changes?",
                "text": "Describe the rash:",
                "options": ["Red spots", "Itchy", "Spreading", "With fever"]
            },
            "nausea": {
                "question": "Are you experiencing nausea or feeling sick?",
                "text": "Is the nausea accompanied by:",
                "options": ["Vomiting", "Abdominal pain", "Loss of appetite", "None of these"]
            },
            "diarrhea": {
                "question": "Are you experiencing diarrhea or loose stools?",
                "text": "How frequent is the diarrhea?",
                "options": ["1-3 times/day", "4-6 times/day", ">6 times/day", "With blood/mucus"]
            },
            "vomiting": {
                "question": "Have you been vomiting?",
                "text": "How often are you vomiting?",
                "options": ["Occasional", "Frequent", "Cannot keep food down", "With blood"]
            },
            "chills": {
                "question": "Are you experiencing chills or shivering?",
                "text": "Describe the chills:",
                "options": ["Mild", "With fever", "Severe/rigors", "Come and go"]
            },
            "sore throat": {
                "question": "Do you have a sore throat?",
                "text": "Describe the throat pain:",
                "options": ["Mild", "Painful to swallow", "With white patches", "With swollen glands"]
            },
            "runny nose": {
                "question": "Do you have a runny or stuffy nose?",
                "text": "Describe the nasal symptoms:",
                "options": ["Clear discharge", "Colored/thick discharge", "Blocked/congested", "With sneezing"]
            },
            "shortness of breath": {
                "question": "Are you experiencing shortness of breath?",
                "text": "When does the breathlessness occur?",
                "options": ["At rest", "During activity", "When lying down", "Sudden onset"]
            },
            "chest pain": {
                "question": "Do you have any chest pain or discomfort?",
                "text": "Describe the chest pain:",
                "options": ["Sharp", "Dull/pressure", "With breathing", "Radiating to arm/jaw"]
            },
            "abdominal pain": {
                "question": "Are you having abdominal or stomach pain?",
                "text": "Where is the abdominal pain located?",
                "options": ["Upper abdomen", "Lower abdomen", "Around navel", "All over"]
            },
            "loss of taste": {
                "question": "Have you noticed any loss of taste?",
                "text": "How is your sense of taste affected?",
                "options": ["Complete loss", "Partial loss", "Food tastes different", "Not sure"]
            },
            "loss of smell": {
                "question": "Have you noticed any loss of smell?",
                "text": "How is your sense of smell affected?",
                "options": ["Complete loss", "Partial loss", "Things smell different", "Not sure"]
            },
            "joint pain": {
                "question": "Are you experiencing joint pain?",
                "text": "Which joints are affected?",
                "options": ["Hands/fingers", "Knees", "Multiple joints", "With swelling"]
            },
            "night sweats": {
                "question": "Do you experience night sweats?",
                "text": "How severe are the night sweats?",
                "options": ["Mild", "Soaking sheets", "With fever", "Frequent"]
            },
            "weight loss": {
                "question": "Have you experienced unintentional weight loss?",
                "text": "How much weight have you lost?",
                "options": ["<5 lbs", "5-10 lbs", ">10 lbs", "Not sure"]
            },
            "painful urination": {
                "question": "Do you experience pain or burning when urinating?",
                "text": "Describe the urination symptoms:",
                "options": ["Burning sensation", "Pain", "With urgency", "With blood"]
            },
            "dizziness": {
                "question": "Are you experiencing dizziness?",
                "text": "Describe the dizziness:",
                "options": ["Lightheaded", "Room spinning (vertigo)", "With standing up", "Constant"]
            },
            "sweating": {
                "question": "Are you sweating excessively?",
                "text": "When does the sweating occur?",
                "options": ["All the time", "At night", "With fever", "During activity"]
            }
        }
    
    def _load_symptom_synonyms(self) -> Dict[str, List[str]]:
        """Load symptom synonyms for better extraction using NLP patterns."""
        return {
            "fever": ["fever", "temperature", "hot", "feverish", "pyrexia", "febrile", "high temp", "burning up"],
            "headache": ["headache", "head pain", "head ache", "migraine", "head hurts", "head throbbing"],
            "cough": ["cough", "coughing", "dry cough", "wet cough", "hacking cough", "productive cough"],
            "body ache": ["body ache", "body pain", "muscle pain", "aching", "soreness", "myalgia", "aches all over"],
            "fatigue": ["fatigue", "tired", "exhausted", "weakness", "weak", "lethargy", "no energy", "worn out", "run down"],
            "chills": ["chills", "shivering", "cold sweats", "rigors", "feeling cold", "goosebumps"],
            "nausea": ["nausea", "nauseous", "queasy", "sick feeling", "upset stomach", "feel like vomiting"],
            "vomiting": ["vomiting", "vomit", "throwing up", "puking", "emesis", "been sick"],
            "diarrhea": ["diarrhea", "loose stools", "watery stools", "loose motion", "frequent bowel movements", "runs"],
            "rash": ["rash", "skin rash", "spots", "eruption", "skin breakout", "hives", "red patches"],
            "sore throat": ["sore throat", "throat pain", "painful throat", "scratchy throat", "throat hurts"],
            "runny nose": ["runny nose", "nasal discharge", "stuffy nose", "blocked nose", "congestion", "rhinorrhea"],
            "joint pain": ["joint pain", "joint ache", "arthralgia", "joints hurt", "stiff joints", "joint swelling"],
            "chest pain": ["chest pain", "chest tightness", "chest discomfort", "chest pressure", "heart pain"],
            "shortness of breath": ["shortness of breath", "breathless", "difficulty breathing", "dyspnea", "can't breathe", "gasping"],
            "loss of taste": ["loss of taste", "can't taste", "ageusia", "food tasteless", "no taste"],
            "loss of smell": ["loss of smell", "can't smell", "anosmia", "smell gone", "no smell"],
            "abdominal pain": ["abdominal pain", "stomach pain", "belly pain", "stomach ache", "tummy ache", "gut pain"],
            "night sweats": ["night sweats", "sweating at night", "wake up sweating", "drenching sweats"],
            "weight loss": ["weight loss", "losing weight", "lost weight", "unintended weight loss"],
            "swelling": ["swelling", "swollen", "edema", "puffy", "inflammation"],
            "dizziness": ["dizziness", "dizzy", "lightheaded", "vertigo", "room spinning", "unsteady"],
            "blurred vision": ["blurred vision", "blurry vision", "vision problems", "can't see clearly"],
            "painful urination": ["painful urination", "burning urination", "dysuria", "hurts to pee"],
            "frequent urination": ["frequent urination", "urinating often", "polyuria", "always peeing"],
            "constipation": ["constipation", "constipated", "can't go", "hard stools", "no bowel movement"],
            "back pain": ["back pain", "backache", "lower back pain", "upper back pain", "spine pain"],
            "anxiety": ["anxiety", "anxious", "nervous", "worried", "panic", "on edge"],
            "depression": ["depression", "depressed", "sad", "hopeless", "down", "low mood"],
            "insomnia": ["insomnia", "can't sleep", "sleep problems", "sleepless", "trouble sleeping"],
            "palpitations": ["palpitations", "heart racing", "rapid heartbeat", "heart pounding", "skipping beats"],
            "sweating": ["sweating", "perspiring", "sweaty", "profuse sweating", "diaphoresis"],
            "itching": ["itching", "itchy", "pruritus", "scratching"],
            "eye pain": ["eye pain", "eyes hurt", "painful eyes", "eye ache"],
            "ear pain": ["ear pain", "earache", "ear hurts", "otalgia"],
            "sneezing": ["sneezing", "sneeze", "achoo"],
            "wheezing": ["wheezing", "wheeze", "whistling breath"],
            "muscle pain": ["muscle pain", "muscular pain", "myalgia", "muscles hurt", "muscle ache"],
            "loss of appetite": ["loss of appetite", "not hungry", "no appetite", "anorexia", "don't want to eat"],
        }
    
    def _build_likelihood_matrix(self) -> Dict[str, Dict[str, float]]:
        """Build P(S|D) matrix from disease-symptom data with smoothing."""
        matrix = {}
        
        for disease in self.diseases:
            matrix[disease] = {}
            disease_symptoms = [d for d in self.disease_symptoms if d["disease"] == disease]
            
            for symptom in self.symptoms:
                # Find weight for this symptom-disease pair
                match = next((d for d in disease_symptoms if d["symptom"] == symptom), None)
                # Use Laplace smoothing for unknown combinations
                matrix[disease][symptom] = match["weight"] if match else self.SMOOTHING_FACTOR
        
        return matrix
    
    def extract_symptoms(self, text: str) -> Dict[str, Any]:
        """
        Extract symptoms from free-text input.
        
        Uses Bio_ClinicalBERT when use_bert_nlp=True (requires HF_TOKEN for API),
        otherwise falls back to synonym matching and rule-based patterns.
        
        Bio_ClinicalBERT provides ~90% entity extraction accuracy on medical text.
        """
        # Try Bio_ClinicalBERT if enabled
        if self.use_bert_nlp:
            nlp = get_nlp_extractor()
            if nlp:
                try:
                    bert_result = nlp.extract_symptoms(text)
                    if bert_result.get("symptoms"):
                        # Map BERT-extracted symptoms to our canonical symptom list
                        canonical_symptoms = self._map_to_canonical_symptoms(bert_result["symptoms"])
                        red_flags = self.check_red_flags(canonical_symptoms)
                        
                        # Extract duration using patterns
                        duration = self._extract_duration(text)
                        
                        return {
                            "symptoms": canonical_symptoms,
                            "entities": bert_result.get("entities", []),
                            "duration": duration,
                            "original_text": text,
                            "red_flags": red_flags,
                            "extraction_method": "bio_clinicalbert"
                        }
                except Exception as e:
                    print(f"[WARN] Bio_ClinicalBERT extraction failed, falling back to rules: {e}")
        
        # Fallback to rule-based extraction
        text_lower = text.lower()
        found_symptoms = []
        entities = []
        
        for canonical, synonyms in self.symptom_synonyms.items():
            for synonym in synonyms:
                if synonym in text_lower:
                    if canonical not in found_symptoms:
                        found_symptoms.append(canonical)
                        start_idx = text_lower.find(synonym)
                        entities.append({
                            "text": synonym,
                            "label": canonical,
                            "start": start_idx,
                            "end": start_idx + len(synonym)
                        })
                    break
        
        # Extract duration
        duration = self._extract_duration(text)
        
        # Check for red flags in the extracted symptoms
        red_flags = self.check_red_flags(found_symptoms)
        
        return {
            "symptoms": found_symptoms,
            "entities": entities,
            "duration": duration,
            "original_text": text,
            "red_flags": red_flags,
            "extraction_method": "rule_based"
        }
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration patterns from text."""
        text_lower = text.lower()
        duration_patterns = [
            (r"(\d+)\s*days?", "days"),
            (r"(\d+)\s*weeks?", "weeks"),
            (r"(\d+)\s*hours?", "hours"),
            (r"since\s+(\w+)", "since"),
            (r"for\s+(\d+\s*\w+)", "for")
        ]
        
        for pattern, _ in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(0)
        return None
    
    def _map_to_canonical_symptoms(self, bert_symptoms: List[str]) -> List[str]:
        """
        Map BERT-extracted symptom terms to canonical symptom names.
        
        Uses multi-stage matching:
        1. Direct match in symptom list
        2. Synonym dictionary match
        3. SapBERT semantic similarity (if available)
        4. Fuzzy substring match (fallback)
        """
        canonical = []
        
        for symptom in bert_symptoms:
            symptom_lower = symptom.lower().strip()
            
            # Stage 1: Direct match in our symptom list
            if symptom_lower in self.symptoms:
                if symptom_lower not in canonical:
                    canonical.append(symptom_lower)
                continue
            
            # Stage 2: Check synonyms
            matched = False
            for canonical_name, synonyms in self.symptom_synonyms.items():
                if symptom_lower in [s.lower() for s in synonyms]:
                    if canonical_name not in canonical:
                        canonical.append(canonical_name)
                    matched = True
                    break
            
            if matched:
                continue
            
            # Stage 3: SapBERT semantic matching (high accuracy)
            sapbert = get_sapbert_adapter()
            if sapbert:
                try:
                    result = sapbert.normalize_symptom(symptom_lower, self.symptoms[:100])  # Top 100 symptoms
                    if result["similarity"] > 0.75:  # High similarity threshold
                        if result["canonical"] not in canonical:
                            canonical.append(result["canonical"])
                        continue
                except Exception as e:
                    logger.debug(f"SapBERT matching failed for '{symptom}': {e}")
            
            # Stage 4: Fuzzy match - check if any synonym is contained
            for canonical_name, synonyms in self.symptom_synonyms.items():
                for syn in synonyms:
                    if syn.lower() in symptom_lower or symptom_lower in syn.lower():
                        if canonical_name not in canonical:
                            canonical.append(canonical_name)
                        matched = True
                        break
                if matched:
                    break
        
        return canonical
    
    def check_red_flags(self, symptoms: List[str]) -> List[Dict]:
        """Check for critical/red flag symptoms that need immediate attention."""
        warnings = []
        
        for flag in self.red_flags:
            flag_symptom = flag["symptom"].lower()
            for symptom in symptoms:
                if flag_symptom in symptom.lower() or symptom.lower() in flag_symptom:
                    warnings.append({
                        "symptom": symptom,
                        "severity": flag.get("severity", "high"),
                        "action": flag.get("action", "Seek medical attention")
                    })
                    break
        
        return warnings
    
    def start(self, symptoms: List[str], session_id: str = None) -> Dict[str, Any]:
        """
        Initialize triage session with extracted symptoms.
        
        Returns initial state with disease probabilities.
        """
        session_id = session_id or str(uuid.uuid4())
        
        # Normalize symptoms
        symptoms = [s.lower().strip() for s in symptoms]
        
        # Check for red flags
        red_flags = self.check_red_flags(symptoms)
        
        # Initialize with disease priors P(D)
        prior = self.disease_priors.copy()
        
        # Update with initial symptoms using Bayes' rule
        posterior = self._compute_posterior(prior, symptoms)
        
        # Sort by probability
        sorted_probs = sorted(
            [{"disease": d, "probability": p} for d, p in posterior.items()],
            key=lambda x: x["probability"],
            reverse=True
        )
        
        # Get first follow-up question
        next_q = self._get_best_question(posterior, symptoms)
        
        return {
            "session_id": session_id,
            "probabilities": sorted_probs,
            "posterior": posterior,
            "observed_symptoms": symptoms,
            "confirmed_symptoms": symptoms.copy(),
            "denied_symptoms": [],
            "negative_symptoms": [],
            "asked_questions": [],
            "question_count": 0,
            "answers": {},
            "candidate_questions": self._get_candidate_questions(symptoms),
            "next_question": next_q,
            "status": "EMERGENCY" if red_flags else "IN_PROGRESS",
            "red_flags": red_flags
        }
    
    def _compute_posterior(
        self, 
        prior: Dict[str, float], 
        symptoms: List[str],
        negative_symptoms: List[str] = None
    ) -> Dict[str, float]:
        """
        Compute posterior P(D|S) using Bayes' rule with proper handling.
        
        P(D|S+,S-) ∝ P(D) × Π P(s+|D) × Π (1 - P(s-|D))
        
        where S+ are positive (confirmed) symptoms and S- are negative (denied) symptoms.
        """
        negative_symptoms = negative_symptoms or []
        posterior = {}
        
        for disease in self.diseases:
            # Start with prior
            prob = prior.get(disease, 1.0 / len(self.diseases))
            
            # Multiply by likelihood for each positive symptom
            for symptom in symptoms:
                likelihood = self.likelihood_matrix.get(disease, {}).get(symptom, self.SMOOTHING_FACTOR)
                prob *= likelihood
            
            # Multiply by (1 - likelihood) for negative symptoms
            for neg_symptom in negative_symptoms:
                likelihood = self.likelihood_matrix.get(disease, {}).get(neg_symptom, self.SMOOTHING_FACTOR)
                prob *= (1.0 - likelihood)
            
            posterior[disease] = prob
        
        # Normalize to ensure probabilities sum to 1
        total = sum(posterior.values())
        if total > 0:
            posterior = {d: p / total for d, p in posterior.items()}
        else:
            # Fallback to uniform distribution
            posterior = {d: 1.0 / len(self.diseases) for d in self.diseases}
        
        return posterior
    
    def _get_candidate_questions(self, observed: List[str]) -> List[str]:
        """Get symptoms we haven't asked about yet."""
        all_symptoms = set(self.symptoms)
        observed_set = set(observed)
        return list(all_symptoms - observed_set)
    
    def _get_best_question(
        self, 
        posterior: Dict[str, float], 
        asked_symptoms: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Select next question using information gain (entropy reduction).
        
        IG(S) = H(D) - E[H(D|S)]
        
        Focuses on symptoms relevant to top probable diseases.
        """
        # Get candidate symptoms from top diseases
        top_diseases = [
            d for d, p in sorted(posterior.items(), key=lambda x: x[1], reverse=True)[:10]
            if p > 0.01
        ]
        
        candidate_symptoms = set()
        for disease in top_diseases:
            if disease in self.likelihood_matrix:
                candidate_symptoms.update(self.likelihood_matrix[disease].keys())
        
        best_symptom = None
        best_gain = -1
        
        for symptom in candidate_symptoms:
            if symptom in asked_symptoms:
                continue
            
            gain = self._expected_information_gain(posterior, symptom)
            
            # Boost by cached info gain from training
            if symptom in self.info_gain_cache:
                gain += self.info_gain_cache[symptom] * 0.1
            
            if gain > best_gain:
                best_gain = gain
                best_symptom = symptom
        
        if best_symptom is None:
            return None
        
        # Get question template
        question_data = self.symptom_questions.get(best_symptom, {})
        question_text = question_data.get("question", question_data.get("text", f"Do you have {best_symptom}?"))
        
        return {
            "symptom": best_symptom,
            "question": question_text,
            "text": question_data.get("text", question_text),
            "options": question_data.get("options", ["Yes", "No", "Not sure"]),
            "info_gain": round(best_gain, 4)
        }
    
    def next_question(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get next question based on 3-5-7 rule and expected information gain.
        
        Returns None if session should finish.
        """
        questions_asked = len(state.get("asked_questions", []))
        posterior = state.get("posterior", {})
        
        # Get top prediction confidence
        sorted_probs = sorted(posterior.items(), key=lambda x: x[1], reverse=True)
        top_confidence = sorted_probs[0][1] if sorted_probs else 0.0
        
        # ===== 3-5-7 RULE DECISION LOGIC =====
        # Case A: Below minimum - MUST continue
        if questions_asked < self.MIN_QUESTIONS:
            return self._get_best_question(
                posterior, 
                state.get("asked_questions", []) + state.get("observed_symptoms", [])
            )
        
        # Case B: Between MIN (3) and SOFT_MAX (5) - stop only if HIGH confidence
        if self.MIN_QUESTIONS <= questions_asked < self.SOFT_MAX_QUESTIONS:
            if top_confidence >= self.HIGH_CONFIDENCE:
                return None  # High confidence reached, can stop
            return self._get_best_question(
                posterior, 
                state.get("asked_questions", []) + state.get("observed_symptoms", [])
            )
        
        # Case C: Between SOFT_MAX (5) and HARD_MAX (7) - continue only if LOW confidence
        if self.SOFT_MAX_QUESTIONS <= questions_asked < self.HARD_MAX_QUESTIONS:
            if top_confidence >= self.LOW_CONFIDENCE:
                return None  # Sufficient confidence, stop
            return self._get_best_question(
                posterior, 
                state.get("asked_questions", []) + state.get("observed_symptoms", [])
            )
        
        # Case D: HARD_MAX (7) reached - MUST stop
        return None
    
    def _expected_information_gain(
        self, 
        posterior: Dict[str, float], 
        symptom: str
    ) -> float:
        """
        Calculate expected information gain for asking about a symptom.
        
        Uses entropy reduction:
        IG(D,S) = H(D) - [P(S) × H(D|S=yes) + P(¬S) × H(D|S=no)]
        """
        # Current entropy H(D)
        current_entropy = self._entropy(list(posterior.values()))
        
        # Estimate P(symptom = yes) across diseases
        p_yes = sum(
            posterior.get(d, 0) * self.likelihood_matrix.get(d, {}).get(symptom, self.SMOOTHING_FACTOR)
            for d in self.diseases
        )
        p_no = 1 - p_yes
        
        # Clamp probabilities
        p_yes = max(0.01, min(0.99, p_yes))
        p_no = max(0.01, min(0.99, p_no))
        
        # H(D|S=yes) - posterior if symptom is confirmed
        posterior_yes = {}
        for d in self.diseases:
            likelihood = self.likelihood_matrix.get(d, {}).get(symptom, self.SMOOTHING_FACTOR)
            posterior_yes[d] = posterior.get(d, 0) * likelihood
        total_yes = sum(posterior_yes.values())
        if total_yes > 0:
            posterior_yes = {d: p / total_yes for d, p in posterior_yes.items()}
        entropy_yes = self._entropy(list(posterior_yes.values()))
        
        # H(D|S=no) - posterior if symptom is denied
        posterior_no = {}
        for d in self.diseases:
            likelihood = self.likelihood_matrix.get(d, {}).get(symptom, self.SMOOTHING_FACTOR)
            posterior_no[d] = posterior.get(d, 0) * (1.0 - likelihood)
        total_no = sum(posterior_no.values())
        if total_no > 0:
            posterior_no = {d: p / total_no for d, p in posterior_no.items()}
        entropy_no = self._entropy(list(posterior_no.values()))
        
        # Expected conditional entropy
        expected_entropy = p_yes * entropy_yes + p_no * entropy_no
        
        # Information gain
        return max(0, current_entropy - expected_entropy)
    
    def _entropy(self, probs: List[float]) -> float:
        """Calculate Shannon entropy of probability distribution."""
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p + 1e-10)
        return entropy
    
    def update(self, state: Dict[str, Any], answer: str, symptom: str = None) -> Dict[str, Any]:
        """
        Update session state based on patient's answer using 3-5-7 rule.
        
        Args:
            state: Current session state
            answer: Patient's answer ('yes', 'no', or specific option)
            symptom: The symptom being answered (optional, inferred if not provided)
            
        Returns:
            Updated session state with status determination
        """
        # Get the symptom that was asked
        current_symptom = symptom
        if not current_symptom and state.get("next_question"):
            current_symptom = state["next_question"].get("symptom")
        
        if not current_symptom:
            # Find from candidates
            candidates = state.get("candidate_questions", [])
            asked = state.get("asked_questions", [])
            remaining = [q for q in candidates if q not in asked]
            if remaining:
                current_symptom = remaining[0]
        
        if current_symptom is None:
            # No symptom to update, just return current state
            state["status"] = "FINISHED"
            state["final_predictions"] = self._generate_predictions(state["posterior"])
            return state
        
        # Normalize symptom
        current_symptom = current_symptom.lower().strip()
        
        # Update tracking lists
        observed = state.get("observed_symptoms", []).copy()
        negative = state.get("negative_symptoms", state.get("denied_symptoms", [])).copy()
        asked = state.get("asked_questions", []).copy()
        
        # Interpret answer
        answer_lower = answer.lower().strip()
        
        # Add to asked questions
        if current_symptom not in asked:
            asked.append(current_symptom)
        
        # Update symptom lists based on answer
        if "yes" in answer_lower or answer_lower in ["mild", "moderate", "severe", "true", "1"]:
            if current_symptom not in observed:
                observed.append(current_symptom)
                # Check for new red flags
                new_flags = self.check_red_flags([current_symptom])
                if new_flags:
                    state.setdefault("red_flags", []).extend(new_flags)
        elif "no" in answer_lower or answer_lower in ["false", "0"]:
            if current_symptom not in negative:
                negative.append(current_symptom)
        # "Not sure" or other answers don't update
        
        # Recompute posterior
        prior = self.disease_priors.copy()
        posterior = self._compute_posterior(prior, observed, negative)
        
        # Sort by probability
        sorted_probs = sorted(
            [{"disease": d, "probability": p} for d, p in posterior.items()],
            key=lambda x: x["probability"],
            reverse=True
        )
        
        # Get top confidence
        top_disease, top_score = sorted_probs[0]["disease"], sorted_probs[0]["probability"]
        questions_asked = len(asked)
        
        # ===== 3-5-7 DECISION LOGIC =====
        should_stop = False
        stop_reason = None
        
        if questions_asked < self.MIN_QUESTIONS:
            should_stop = False
        elif self.MIN_QUESTIONS <= questions_asked < self.SOFT_MAX_QUESTIONS:
            if top_score >= self.HIGH_CONFIDENCE:
                should_stop = True
                stop_reason = f"High confidence ({top_score:.1%}) reached at {questions_asked} questions"
        elif self.SOFT_MAX_QUESTIONS <= questions_asked < self.HARD_MAX_QUESTIONS:
            if top_score >= self.LOW_CONFIDENCE:
                should_stop = True
                stop_reason = f"Sufficient confidence ({top_score:.1%}) at {questions_asked} questions"
        else:
            should_stop = True
            stop_reason = f"Maximum questions ({self.HARD_MAX_QUESTIONS}) reached"
        
        # Update state
        new_state = {
            "session_id": state.get("session_id"),
            "probabilities": sorted_probs,
            "posterior": posterior,
            "observed_symptoms": observed,
            "confirmed_symptoms": observed,
            "denied_symptoms": negative,
            "negative_symptoms": negative,
            "asked_questions": asked,
            "question_count": questions_asked,
            "answers": {**state.get("answers", {}), current_symptom: answer},
            "candidate_questions": state.get("candidate_questions", []),
            "last_question": current_symptom,
            "red_flags": state.get("red_flags", [])
        }
        
        if should_stop:
            new_state["status"] = "FINISHED"
            new_state["stop_reason"] = stop_reason
            new_state["next_question"] = None
            new_state["final_predictions"] = self._generate_predictions(posterior)
        else:
            new_state["status"] = "IN_PROGRESS"
            next_q = self._get_best_question(posterior, observed + negative + asked)
            
            if next_q:
                new_state["next_question"] = next_q
            else:
                # No more questions available
                new_state["status"] = "FINISHED"
                new_state["stop_reason"] = "All relevant questions exhausted"
                new_state["next_question"] = None
                new_state["final_predictions"] = self._generate_predictions(posterior)
        
        return new_state
    
    def _generate_predictions(self, posterior: Dict[str, float]) -> List[Dict]:
        """Generate structured predictions with confidence levels and explanations."""
        ranked = sorted(posterior.items(), key=lambda x: x[1], reverse=True)
        predictions = []
        
        for i, (disease, prob) in enumerate(ranked[:5]):
            if prob < 0.01:
                continue
            
            # Determine confidence level
            if prob >= self.HIGH_CONFIDENCE:
                confidence = "HIGH"
            elif prob >= self.MEDIUM_CONFIDENCE:
                confidence = "MEDIUM"
            elif prob >= self.LOW_CONFIDENCE:
                confidence = "MODERATE"
            else:
                confidence = "LOW"
            
            predictions.append({
                "rank": i + 1,
                "disease": disease,
                "probability": round(prob, 4),
                "percentage": f"{prob * 100:.1f}%",
                "confidence": confidence,
                "explanation": self._get_explanation(disease, prob, confidence)
            })
        
        return predictions
    
    def enhance_predictions_with_sapbert(
        self, 
        symptoms: List[str], 
        bayesian_predictions: List[Dict],
        weight_bayesian: float = 0.7
    ) -> List[Dict]:
        """
        Enhance Bayesian predictions using SapBERT semantic similarity.
        
        Combines:
        - Bayesian P(D|S): Statistical probability from training data
        - SapBERT similarity: Semantic understanding from pre-trained model
        
        Args:
            symptoms: List of confirmed symptoms
            bayesian_predictions: Predictions from Bayesian inference
            weight_bayesian: Weight for Bayesian score (default 0.7)
            
        Returns:
            Enhanced predictions with combined scores
        """
        sapbert = get_sapbert_adapter()
        if not sapbert or not symptoms:
            return bayesian_predictions
        
        try:
            # Get disease names from predictions
            diseases = [p["disease"] for p in bayesian_predictions]
            
            # Get SapBERT semantic scores
            sapbert_ranking = sapbert.encode_differential_diagnosis(
                patient_symptoms=symptoms,
                candidate_diseases=diseases
            )
            
            # Create lookup for SapBERT scores
            sapbert_scores = {r["disease"]: r["score"] for r in sapbert_ranking}
            
            # Combine scores
            enhanced = []
            for pred in bayesian_predictions:
                disease = pred["disease"]
                bayesian_prob = pred["probability"]
                sapbert_score = sapbert_scores.get(disease, 0.5)
                
                # Weighted combination
                combined_score = (
                    weight_bayesian * bayesian_prob +
                    (1 - weight_bayesian) * sapbert_score
                )
                
                enhanced.append({
                    **pred,
                    "bayesian_score": bayesian_prob,
                    "sapbert_score": round(sapbert_score, 4),
                    "combined_score": round(combined_score, 4),
                    "probability": round(combined_score, 4),
                    "percentage": f"{combined_score * 100:.1f}%"
                })
            
            # Re-rank by combined score
            enhanced.sort(key=lambda x: x["combined_score"], reverse=True)
            
            # Update ranks
            for i, pred in enumerate(enhanced):
                pred["rank"] = i + 1
            
            logger.debug(f"Enhanced predictions with SapBERT semantic similarity")
            return enhanced
            
        except Exception as e:
            logger.warning(f"SapBERT enhancement failed: {e}")
            return bayesian_predictions
    
    def _get_explanation(self, disease: str, prob: float, confidence: str) -> str:
        """Generate explanation for a prediction."""
        if confidence == "HIGH":
            return f"Strong match based on reported symptoms. {disease} is highly consistent with your symptom profile."
        elif confidence == "MEDIUM":
            return f"Good match for {disease}. Your symptoms align well with this condition."
        elif confidence == "MODERATE":
            return f"{disease} is a reasonable possibility based on some matching symptoms."
        else:
            return f"Lower probability match. Consider {disease} if other conditions are ruled out."
    
    def get_session_summary(self, state: Dict) -> Dict:
        """Generate a comprehensive summary of the triage session."""
        predictions = state.get("final_predictions", [])
        top_prediction = predictions[0] if predictions else None
        
        return {
            "session_id": state.get("session_id"),
            "questions_asked": state.get("question_count", len(state.get("asked_questions", []))),
            "symptoms_confirmed": len(state.get("confirmed_symptoms", state.get("observed_symptoms", []))),
            "symptoms_denied": len(state.get("denied_symptoms", state.get("negative_symptoms", []))),
            "top_prediction": top_prediction,
            "all_predictions": predictions,
            "red_flags": state.get("red_flags", []),
            "status": state.get("status"),
            "stop_reason": state.get("stop_reason"),
            "recommendations": self._get_recommendations(state)
        }
    
    def _get_recommendations(self, state: Dict) -> List[str]:
        """Generate recommendations based on triage results."""
        recommendations = []
        
        # Red flag warnings
        if state.get("red_flags"):
            recommendations.append("⚠️ URGENT: Critical symptoms detected. Seek immediate medical attention!")
        
        # Based on top prediction
        predictions = state.get("final_predictions", [])
        if predictions:
            top = predictions[0]
            if top.get("confidence") == "HIGH":
                recommendations.append(f"Strongly consider consulting a healthcare provider about {top['disease']}.")
            elif top.get("confidence") in ["MEDIUM", "MODERATE"]:
                recommendations.append("Schedule an appointment with a healthcare provider for proper diagnosis.")
            else:
                recommendations.append("Monitor your symptoms and consult a doctor if they persist or worsen.")
        
        # General disclaimers
        recommendations.append("This AI assessment is not a substitute for professional medical advice, diagnosis, or treatment.")
        recommendations.append("Keep track of any new or changing symptoms and report them to your healthcare provider.")
        
        return recommendations
