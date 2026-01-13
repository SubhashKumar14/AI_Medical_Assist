"""
Safety Configuration & Tensors
==============================

Strict safety protocols and content filters for the CDSS AI.
These rules define the "Safety Tensors" that govern AI behavior.

Core Principle:
    The AI is a Clinical Decision Support System, not a diagnostic tool.
    It must NEVER diagnose, prescribe, or replace a doctor.

"""

import re
from typing import Tuple, Optional

# === 1. BLOCKED WORDS (Absolute Ban) ===
UNSAFE_TERMS = [
    "diagnosed", 
    "confirmed diagnosis",
    "confirm that you have",
    "we have confirmed",
    "prescribe", 
    "prescription",
    "dosage", 
    "take [0-9]+ mg",
    "cure", 
    "guaranteed recovery",
    "nothing to worry about",
    "treatment plan",
    "start taking",
]

# === 1.1 RED FLAG SYMPTOMS (Immediate Emergency) ===
RED_FLAG_SYMPTOMS = [
    "chest pain",
    "severe chest pain",
    "crushing chest pain",
    "trouble breathing",
    "difficulty breathing",
    "shortness of breath",
    "choking",
    "loss of consciousness",
    "fainting",
    "severe weakness",
    "severe bleeding",
    "vomiting blood",
    "coughing up blood",
    "sudden numbness",
    "slurred speech",
    "vision loss",
    "suicidal thoughts",
    "swallowing poison",
    "overdose",
]

# === 1.2 RISK CATEGORIES (Disease -> Safe Grouping) ===
RISK_CATEGORIES = {
    # Cardiac
    "Myocardial infarction": "Cardiovascular concern requiring immediate evaluation",
    "NSTEMI / STEMI": "Cardiovascular concern requiring immediate evaluation",
    "Possible NSTEMI / STEMI": "Cardiovascular concern requiring immediate evaluation",
    "Unstable angina": "Cardiovascular concern",
    "Stable angina": "Cardiovascular concern",
    "Heart failure": "Heart function concern",
    "Pericarditis": "Inflammatory heart condition",
    "Myocarditis": "Inflammatory heart condition",
    "Atrial fibrillation": "Heart rhythm concern",
    
    # Neurological
    "Stroke": "Neurological emergency",
    "TIA": "Neurological concern",
    "Meningitis": "Serious neurological infection",
    "Guillain-Barré syndrome": "Neurological condition",
    "Myasthenia gravis": "Neuromuscular condition",
    
    # Oncology
    "Pancreatic neoplasm": "Pancreatic issue requiring specialist review",
    "Pulmonary neoplasm": "Lung tissue concern requiring imaging",
    "Neoplasm": "Tissue growth requiring biopsy/evaluation",
    "Cancer": "Condition requiring oncologist consultation",
    
    # Critical Infections / Systemic
    "Sepsis": "Severe systemic infection",
    "HIV (initial infection)": "Viral immune system concern",
    "HIV": "Viral immune system concern",
    "Ebola": "Serious viral infection",
    "Chagas": "Parasitic infection concern",
    "Tuberculosis": "Serious respiratory infection",
    
    # Organ Failure
    "Chronic kidney failure": "Kidney function concern",
    "Acute pulmonary edema": "Fluid accumulation in lungs",
    "Boerhaave": "Esophageal emergency",
}

# === 2. MANDATORY SYSTEM PROMPT ===
SYSTEM_PROMPT = """
You are an AI assistant for clinical decision support.
You do NOT diagnose diseases.
You do NOT prescribe medication.
You only provide general medical information.
Always recommend consulting a qualified doctor.
Do not use words like "diagnose", "confirm", "cure", or "prescribe".
"""

# === 3. SAFE RESPONSE DISCLAIMER ===
DISCLAIMER_HEADER = """
**DISCLAIMER: This system provides AI-assisted triage support and is NOT a medical diagnosis.**
"""

DISCLAIMER_FOOTER = """
*Please consult a qualified healthcare professional for proper evaluation and treatment.*
"""

def safety_filter(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check text for unsafe terms.
    
    Returns:
        (is_safe, error_message)
    """
    text_lower = text.lower()
    
    for term in UNSAFE_TERMS:
        # Regex search for the term (handles simple spaces)
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            return False, f"Safety Violation: Response contained blocked term '{term}'"
            
    return True, None

def format_safe_response(
    conditions: list, 
    general_explanation: str, 
    missing_info: str = None,
    next_step: str = None
) -> str:
    """
    Format a response according to the mandatory structure.
    """
    response_parts = [DISCLAIMER_HEADER]
    
    if conditions:
        response_parts.append("**Possible conditions (for clinical consideration):**")
        for cond in conditions:
            # Handle dictionary or string conditions
            name = cond.get('disease', cond) if isinstance(cond, dict) else cond
            response_parts.append(f"• {name}")
    
    if general_explanation:
        response_parts.append("\n**General Information:**")
        response_parts.append(general_explanation)
    
    if missing_info:
        response_parts.append("\n**Missing Information:**")
        response_parts.append(missing_info)
        
    response_parts.append("\n**Recommended Next Step:**")
    if next_step:
        response_parts.append(next_step)
    else:
        response_parts.append("Consult a general physician.")
        
    response_parts.append(DISCLAIMER_FOOTER)
    
    return "\n".join(response_parts)

def validate_safety(text: str) -> str:
    """
    Validate text against safety tensors.
    If unsafe, returns a sanitized blocked message.
    """
    is_safe, error = safety_filter(text)
    if not is_safe:
        return "This system does not provide medical diagnosis or treatment advice. (Safety Block)"
    return text
