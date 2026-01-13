"""
Fix Symptom Names - Convert DDXPlus codes to proper medical terminology

This script transforms cryptic DDXPlus evidence codes into readable medical questions:
- "e 54 - sensitive" → "Pain character: sensitive"
- "e 56 (4)" → "Pain intensity: 4 out of 10"
- "feel pain - cheek(r)" → "Pain location: right cheek"
- "pain radiate to another location - nowhere" → "Pain does not radiate"
"""

import json
import pandas as pd
from pathlib import Path
import re

SCRIPT_DIR = Path(__file__).parent
KNOWLEDGE_DIR = SCRIPT_DIR.parent / "knowledge"
DATASET_DIR = SCRIPT_DIR.parent.parent / "evaluation" / "datasets" / "Automatic Symptom Detection"

# DDXPlus Evidence Definitions (from release_evidences.json)
EVIDENCE_DEFINITIONS = {
    "E_53": {
        "question_en": "Do you have pain somewhere, related to your reason for consulting?",
        "name": "pain"
    },
    "E_54": {
        "question_en": "Characterize your pain:",
        "name": "pain_character",
        "values": {
            "V_71": "heartbreaking/tearing",
            "V_112": "throbbing/lancinating",
            "V_154": "tedious/dull",
            "V_161": "sensitive/tender",
            "V_179": "stabbing",
            "V_180": "tugging/pulling",
            "V_181": "burning",
            "V_182": "cramping",
            "V_183": "heavy/pressure",
            "V_184": "pulsating",
            "V_191": "violent/severe",
            "V_192": "sharp",
            "V_193": "sickening",
            "V_196": "scary/frightening",
            "V_198": "exhausting"
        }
    },
    "E_55": {
        "question_en": "Where do you feel the pain?",
        "name": "pain_location"
    },
    "E_56": {
        "question_en": "How intense is the pain? (0-10 scale)",
        "name": "pain_intensity"
    },
    "E_57": {
        "question_en": "Does the pain radiate to another location?",
        "name": "pain_radiation"
    },
    "E_58": {
        "question_en": "How precisely is the pain located? (0-10 scale)",
        "name": "pain_localization"
    },
    "E_59": {
        "question_en": "How fast did the pain appear? (0=sudden, 10=gradual)",
        "name": "pain_onset_speed"
    },
    "E_41": {
        "question_en": "Have you been in contact with someone with similar symptoms in the past 2 weeks?",
        "name": "contact_with_sick_person"
    },
    "E_194": {
        "question_en": "Have you noticed a high pitched sound when breathing in?",
        "name": "stridor_on_inspiration"
    },
    "E_214": {
        "question_en": "Have you noticed a wheezing sound when you exhale?",
        "name": "wheezing_on_exhalation"
    },
    "E_159": {
        "question_en": "Did you lose consciousness?",
        "name": "loss_of_consciousness"
    },
    "E_27": {
        "question_en": "Have you ever had a sexually transmitted infection?",
        "name": "history_of_sti"
    },
    "E_204": {
        "question_en": "Have you traveled out of the country in the last 4 weeks?",
        "name": "recent_travel",
        "values": {
            "V_10": "No",
            "V_0": "North Africa",
            "V_1": "West Africa", 
            "V_2": "South Africa",
            "V_3": "Central America",
            "V_4": "North America",
            "V_5": "South America",
            "V_6": "Asia",
            "V_7": "South East Asia",
            "V_8": "Caribbean",
            "V_9": "Europe",
            "V_13": "Oceania"
        }
    },
    "E_130": {
        "question_en": "What color is the rash?",
        "name": "rash_color"
    },
    "E_131": {
        "question_en": "Do your lesions peel off?",
        "name": "lesions_peeling"
    },
    "E_132": {
        "question_en": "Is the rash swollen?",
        "name": "rash_swelling"
    },
    "E_133": {
        "question_en": "Where is the affected skin region located?",
        "name": "lesion_location"
    },
    "E_134": {
        "question_en": "How intense is the pain from the rash? (0-10)",
        "name": "rash_pain_intensity"
    },
    "E_135": {
        "question_en": "Is the lesion larger than 1cm?",
        "name": "lesion_size"
    },
    "E_136": {
        "question_en": "How severe is the itching? (0-10)",
        "name": "itching_severity"
    },
    "E_152": {
        "question_en": "Where is the swelling located?",
        "name": "swelling_location"
    }
}

# Body location mappings
BODY_LOCATIONS = {
    "cheek(r)": "right cheek",
    "cheek(l)": "left cheek",
    "temple(r)": "right temple",
    "temple(l)": "left temple",
    "forehead": "forehead",
    "occiput": "back of head",
    "top of the head": "top of head",
    "chest": "chest",
    "abdomen": "abdomen",
    "back": "back",
    "neck": "neck",
    "shoulder(r)": "right shoulder",
    "shoulder(l)": "left shoulder",
    "arm(r)": "right arm",
    "arm(l)": "left arm",
    "hand(r)": "right hand",
    "hand(l)": "left hand",
    "leg(r)": "right leg",
    "leg(l)": "left leg",
    "foot(r)": "right foot",
    "foot(l)": "left foot",
    "knee(r)": "right knee",
    "knee(l)": "left knee",
    "hip(r)": "right hip",
    "hip(l)": "left hip",
    "ankle(r)": "right ankle",
    "ankle(l)": "left ankle",
    "wrist(r)": "right wrist",
    "wrist(l)": "left wrist",
    "elbow(r)": "right elbow",
    "elbow(l)": "left elbow",
    "groin(r)": "right groin",
    "groin(l)": "left groin",
    "axilla(r)": "right armpit",
    "axilla(l)": "left armpit",
    "flank(r)": "right flank",
    "flank(l)": "left flank",
    "epigastric": "upper abdomen",
    "hypochondrium(r)": "right upper abdomen",
    "hypochondrium(l)": "left upper abdomen",
    "iliac fossa(r)": "right lower abdomen",
    "iliac fossa(l)": "left lower abdomen",
    "lumbar spine": "lower back",
    "thoracic spine": "mid back",
    "cervical spine": "neck/upper back",
    "nowhere": "no specific location"
}

# Pain character translations
PAIN_CHARACTERS = {
    "sensitive": "tender/sensitive",
    "heavy": "heavy/pressure-like",
    "tedious": "dull/aching",
    "burning": "burning",
    "sharp": "sharp",
    "cramping": "cramping",
    "pulsating": "throbbing/pulsating",
    "tugging": "pulling/tugging",
    "heartbreaking": "tearing",
    "haunting": "lancinating/shooting",
    "a cramp": "cramping",
    "a pulse": "pulsating",
    "a knife stroke": "stabbing"
}


def transform_symptom_name(symptom: str) -> str:
    """Transform cryptic DDXPlus symptom code to readable medical term."""
    original = symptom
    symptom_lower = symptom.lower().strip()
    
    # Pattern: "e XX - value" (categorical evidence with value)
    match = re.match(r'^e\s*(\d+)\s*-\s*(.+)$', symptom_lower)
    if match:
        code = match.group(1)
        value = match.group(2).strip()
        
        if code == "54":  # Pain character
            char = PAIN_CHARACTERS.get(value, value)
            return f"pain character: {char}"
        elif code == "204":  # Travel
            if value == "n":
                return "no recent international travel"
            return f"recent travel to: {value}"
        elif code == "130":  # Rash color
            return f"rash color: {value}"
        elif code == "131":  # Lesions peeling
            if value in ["y", "o"]:
                return "skin lesions are peeling"
            return "skin lesions are not peeling"
        elif code == "132":
            return f"rash swelling level: {value}"
        elif code == "135":  # Lesion size
            if value in ["y", "o"]:
                return "lesion larger than 1cm"
            return "lesion smaller than 1cm"
        elif code == "133":  # Lesion location
            readable_loc = BODY_LOCATIONS.get(value, value)
            return f"skin lesion on {readable_loc}"
        elif code == "152":  # Swelling location
            readable_loc = BODY_LOCATIONS.get(value, value)
            return f"swelling in {readable_loc}"
        elif code == "27":  # STI history
            if value in ["y", "o"]:
                return "history of sexually transmitted infection"
            return "no history of sexually transmitted infection"
        elif code == "41":  # Contact with sick person
            return "contact with person with similar symptoms"
        
        return f"clinical finding {code}: {value}"
    
    # Pattern: "e XX (N)" (numeric scale evidence)
    match = re.match(r'^e\s*(\d+)\s*\((\d+)\)$', symptom_lower)
    if match:
        code = match.group(1)
        value = match.group(2)
        
        if code == "56":  # Pain intensity
            return f"pain intensity: {value}/10"
        elif code == "58":  # Pain localization precision
            return f"pain localization: {value}/10"
        elif code == "59":  # Pain onset speed
            if int(value) <= 2:
                return "pain onset: sudden"
            elif int(value) <= 5:
                return "pain onset: gradual"
            else:
                return "pain onset: very gradual"
        elif code == "134":
            return f"rash pain intensity: {value}/10"
        elif code == "136":
            return f"itching severity: {value}/10"
        elif code == "132":
            return f"rash swelling: {value}/10"
        
        return f"scale evidence {code}: {value}/10"
    
    # Pattern: "e XX" alone
    match = re.match(r'^e\s*(\d+)$', symptom_lower)
    if match:
        code = match.group(1)
        ev_key = f"E_{code}"
        if ev_key in EVIDENCE_DEFINITIONS:
            return EVIDENCE_DEFINITIONS[ev_key].get("name", f"clinical finding {code}")
        # Map remaining clinical evidence codes to readable names
        clinical_code_names = {
            "194": "stridor on inspiration",
            "214": "wheezing on exhalation", 
            "159": "loss of consciousness",
            "41": "contact with person with similar symptoms",
        }
        if code in clinical_code_names:
            return clinical_code_names[code]
        return f"clinical finding {code}"
    
    # ===== PATTERNS FOR ALREADY-TRANSFORMED DATA =====
    
    # Pattern: "evidence XXX: value" (already partially transformed)
    match = re.match(r'^evidence\s*(\d+):\s*(.+)$', symptom_lower)
    if match:
        code = match.group(1)
        value = match.group(2).strip()
        
        if code == "135":  # Lesion size
            if value in ["y", "o"]:
                return "lesion larger than 1cm"
            elif value == "n":
                return "lesion smaller than 1cm"
        elif code == "133":  # Lesion location
            if value == "nowhere":
                return "no skin lesions present"
            readable_loc = BODY_LOCATIONS.get(value, value)
            return f"skin lesion on {readable_loc}"
        elif code == "152":  # Swelling location
            if value == "nowhere":
                return "no swelling present"
            readable_loc = BODY_LOCATIONS.get(value, value)
            return f"swelling in {readable_loc}"
        elif code == "27":  # STI history
            if value in ["y", "o"]:
                return "history of sexually transmitted infection"
            return "no history of STI"
        
        return f"clinical assessment {code}: {value}"
    
    # Pattern: "lesions peeling: value"
    match = re.match(r'^lesions peeling:\s*(.+)$', symptom_lower)
    if match:
        value = match.group(1).strip()
        if value in ["y", "o"]:
            return "skin lesions are peeling"
        return "skin lesions are not peeling"
    
    # Pattern: "rash color: value"  
    match = re.match(r'^rash color:\s*(.+)$', symptom_lower)
    if match:
        color = match.group(1).strip()
        return f"rash is {color} colored"
    
    # Pattern: "rash swelling level: value"
    match = re.match(r'^rash swelling level:\s*(.+)$', symptom_lower)
    if match:
        value = match.group(1).strip()
        if value in ["y", "o"]:
            return "rash is swollen/raised"
        return "rash is flat (not swollen)"
    
    # ===== END ALREADY-TRANSFORMED PATTERNS =====
    
    # Pattern: "feel pain - LOCATION"
    match = re.match(r'^feel pain\s*-\s*(.+)$', symptom_lower)
    if match:
        loc = match.group(1).strip()
        readable_loc = BODY_LOCATIONS.get(loc, loc)
        return f"pain in {readable_loc}"
    
    # Pattern: "pain radiate to another location - LOCATION"
    match = re.match(r'^pain radiate to another location\s*-\s*(.+)$', symptom_lower)
    if match:
        loc = match.group(1).strip()
        if loc == "nowhere":
            return "pain does not radiate"
        readable_loc = BODY_LOCATIONS.get(loc, loc)
        return f"pain radiates to {readable_loc}"
    
    # Pattern: "swelling - LOCATION" or similar
    match = re.match(r'^swelling\s*-\s*(.+)$', symptom_lower)
    if match:
        loc = match.group(1).strip()
        readable_loc = BODY_LOCATIONS.get(loc, loc)
        return f"swelling in {readable_loc}"
    
    # Pattern: "lesion location - LOCATION"
    match = re.match(r'^(lesion|rash|affected region)\s*(location)?\s*-\s*(.+)$', symptom_lower)
    if match:
        loc = match.group(3).strip()
        readable_loc = BODY_LOCATIONS.get(loc, loc)
        return f"skin lesion on {readable_loc}"
    
    # Clean up parenthetical body side indicators
    symptom = re.sub(r'\(r\)', ' (right)', symptom, flags=re.IGNORECASE)
    symptom = re.sub(r'\(l\)', ' (left)', symptom, flags=re.IGNORECASE)
    symptom = re.sub(r'\(d\)', ' (right)', symptom, flags=re.IGNORECASE)  # French droite
    symptom = re.sub(r'\(g\)', ' (left)', symptom, flags=re.IGNORECASE)   # French gauche
    
    # Clean up common phrases
    symptom = symptom.replace("fever (either felt or measured with a thermometer)", "fever")
    symptom = symptom.replace("diffuse (widespread) muscle pain", "widespread muscle pain")
    symptom = symptom.replace("lesions, redness or problems on your skin that you believe are related to the condition you are consulting for", "skin lesions or redness")
    symptom = symptom.replace("cough that produces colored or more abundant sputum than usual", "productive cough with colored sputum")
    symptom = symptom.replace("nasal congestion or a clear runny nose", "nasal congestion or runny nose")
    symptom = symptom.replace("diarrhea or an increase in stool frequency", "diarrhea")
    
    return symptom.strip()


def generate_question(symptom_name: str) -> dict:
    """Generate a proper medical question for a symptom."""
    name_lower = symptom_name.lower().strip()
    
    # Special handling for lifestyle/history questions (not "Do you have X")
    lifestyle_patterns = [
        (r'^live with \d+ or more people', "Do you live with 4 or more people?"),
        (r'^smoking', "Do you smoke cigarettes?"),
        (r'^exposed to secondhand', "Are you exposed to secondhand cigarette smoke on a daily basis?"),
        (r'^attend or work in a daycare', "Do you attend or work in a daycare?"),
        (r'^no recent international travel', "Have you traveled internationally in the last 4 weeks?"),
        (r'^contact with sick person', "Have you been in contact with someone with similar symptoms in the past 2 weeks?"),
        (r'^unprotected sex', "Have you had unprotected sex with more than one partner in the last 6 months?"),
    ]
    
    for pattern, question in lifestyle_patterns:
        if re.search(pattern, name_lower):
            return {"question": question, "type": "binary"}
    
    # Pain location questions - fix the double "in" issue
    if name_lower.startswith("pain in "):
        location = name_lower.replace("pain in ", "").strip()
        # Add "the" for certain body parts
        if location in ["forehead", "chest", "abdomen", "back", "neck", "throat"]:
            return {"question": f"Do you have pain in the {location}?", "type": "binary"}
        elif "right" in location or "left" in location:
            return {"question": f"Do you have pain in the {location}?", "type": "binary"}
        else:
            return {"question": f"Do you have pain in your {location}?", "type": "binary"}
    
    # Pain radiation
    if "pain does not radiate" in name_lower:
        return {"question": "Does your pain stay in one place without spreading?", "type": "binary"}
    
    if name_lower.startswith("pain radiates to "):
        location = name_lower.replace("pain radiates to ", "").strip()
        return {"question": f"Does your pain spread to your {location}?", "type": "binary"}
    
    # Swelling
    if name_lower.startswith("swelling in "):
        location = name_lower.replace("swelling in ", "").strip()
        return {"question": f"Do you have swelling in your {location}?", "type": "binary"}
    if "no swelling present" in name_lower:
        return {"question": "Do you have any swelling anywhere on your body?", "type": "binary"}
    
    # Rash color questions
    if name_lower.startswith("rash is ") and "colored" in name_lower:
        color = name_lower.replace("rash is ", "").replace(" colored", "").strip()
        if color == "na":
            return {"question": "What color is your rash?", "type": "categorical"}
        return {"question": f"Is your rash {color} in color?", "type": "binary"}
    if "rash is swollen" in name_lower or "rash is raised" in name_lower:
        return {"question": "Is your rash raised or swollen?", "type": "binary"}
    if "rash is flat" in name_lower:
        return {"question": "Is your rash flat (not raised)?", "type": "binary"}
    
    # No lesions present
    if "no skin lesions present" in name_lower:
        return {"question": "Do you have any skin lesions or rashes?", "type": "binary"}
    
    # Lesion/skin questions
    if "lesion larger than 1cm" in name_lower:
        return {"question": "Is your skin lesion larger than 1cm?", "type": "binary"}
    if "lesion smaller than 1cm" in name_lower:
        return {"question": "Is your skin lesion smaller than 1cm?", "type": "binary"}
    if "lesions are peeling" in name_lower:
        return {"question": "Are your skin lesions peeling?", "type": "binary"}
    if "lesions are not peeling" in name_lower:
        return {"question": "Are your skin lesions staying intact (not peeling)?", "type": "binary"}
    if name_lower.startswith("skin lesion on "):
        location = name_lower.replace("skin lesion on ", "").strip()
        return {"question": f"Is your skin lesion located on your {location}?", "type": "binary"}
    
    # History questions
    if "history of sexually transmitted infection" in name_lower:
        return {"question": "Have you ever had a sexually transmitted infection?", "type": "binary"}
    if "contact with person with similar symptoms" in name_lower:
        return {"question": "Have you been in contact with someone who had similar symptoms recently?", "type": "binary"}
    
    # Clinical evidence patterns - map to proper questions
    clinical_evidence_map = {
        "194": ("Have you noticed a high-pitched sound when breathing in (stridor)?", "binary"),
        "214": ("Have you noticed a wheezing sound when you exhale?", "binary"),
        "159": ("Did you lose consciousness?", "binary"),
        "27": ("Have you ever had a sexually transmitted infection?", "binary"),
        "41": ("Have you been in contact with someone with similar symptoms recently?", "binary"),
    }
    
    match = re.match(r'^clinical evidence\s*(\d+)$', name_lower)
    if match:
        code = match.group(1)
        if code in clinical_evidence_map:
            q, t = clinical_evidence_map[code]
            return {"question": q, "type": t}
        return {"question": f"Clinical assessment evidence {code}?", "type": "binary"}
    
    # Clinical findings (catch-all for remaining evidence codes)
    if name_lower.startswith("clinical finding") or name_lower.startswith("clinical assessment"):
        return {"question": f"Medical evaluation required: {symptom_name}", "type": "binary"}
    
    # Boolean symptoms (yes/no questions)
    boolean_patterns = [
        (r'^skin lesion', "Do you have any skin lesions or rashes?"),
        (r'^fever$', "Do you have a fever?"),
        (r'^headache$', "Do you have a headache?"),
        (r'^productive cough', "Do you have a cough that produces colored or thick mucus?"),
        (r'^cough', "Do you have a cough?"),
        (r'^sore throat', "Do you have a sore throat?"),
        (r'^nausea', "Do you feel nauseous?"),
        (r'^vomiting', "Have you been vomiting?"),
        (r'^diarrhea', "Do you have diarrhea?"),
        (r'^fatigue', "Do you feel fatigued or unusually tired?"),
        (r'^chest pain', "Do you have chest pain?"),
        (r'^shortness of breath', "Are you experiencing shortness of breath?"),
        (r'^dizziness', "Do you feel dizzy?"),
        (r'^weakness', "Do you feel weak?"),
        (r'^nasal congestion', "Do you have nasal congestion or a runny nose?"),
        (r'^widespread muscle pain', "Do you have widespread muscle aches?"),
        (r'^swollen.*lymph', "Do you have swollen or painful lymph nodes?"),
        (r'^chills', "Have you had chills or shivers?"),
        (r'^loss of appetite', "Have you lost your appetite recently?"),
        (r'^weight loss', "Have you had unintentional weight loss?"),
        (r'^stridor', "Have you noticed a high-pitched breathing sound?"),
        (r'^wheezing', "Do you have wheezing when you breathe?"),
    ]
    
    for pattern, question in boolean_patterns:
        if re.search(pattern, name_lower):
            return {"question": question, "type": "binary"}
    
    # Scale/intensity questions
    if "intensity:" in name_lower or "/10" in name_lower:
        if "pain intensity" in name_lower:
            return {
                "question": "On a scale of 0-10, how intense is your pain?",
                "type": "scale",
                "min": 0,
                "max": 10
            }
        elif "itching" in name_lower:
            return {
                "question": "On a scale of 0-10, how severe is your itching?",
                "type": "scale",
                "min": 0,
                "max": 10
            }
        elif "rash" in name_lower:
            return {
                "question": "On a scale of 0-10, how severe is your rash?",
                "type": "scale",
                "min": 0,
                "max": 10
            }
    
    # Categorical questions
    if "pain character" in name_lower:
        return {
            "question": "How would you describe your pain?",
            "type": "categorical",
            "options": ["Sharp", "Dull/Aching", "Burning", "Throbbing", "Cramping", "Pressure-like", "Stabbing"]
        }
    
    if "pain onset" in name_lower:
        return {
            "question": "How quickly did your pain start?",
            "type": "categorical", 
            "options": ["Sudden (seconds)", "Quick (minutes)", "Gradual (hours)", "Very gradual (days)"]
        }
    
    if "rash color" in name_lower:
        return {
            "question": "What color is your rash?",
            "type": "categorical",
            "options": ["Red", "Pink", "Purple", "Dark", "Pale", "Yellow"]
        }
    
    if "recent travel" in name_lower:
        if "no recent" in name_lower:
            return {
                "question": "Have you traveled internationally in the last 4 weeks?",
                "type": "binary"
            }
        return {
            "question": "Where did you travel to recently?",
            "type": "categorical",
            "options": ["Africa", "Asia", "Europe", "Americas", "Caribbean", "Oceania"]
        }
    
    # Default: convert to yes/no question
    # Capitalize first letter and add question format
    clean_name = symptom_name.strip()
    if clean_name and not clean_name[0].isupper():
        clean_name = clean_name[0].upper() + clean_name[1:]
    
    return {
        "question": f"Do you have {symptom_name.lower()}?",
        "type": "binary"
    }


def fix_knowledge_base():
    """Fix the symptom names in the knowledge base files."""
    print("🔧 Fixing DDXPlus Symptom Names...")
    print("=" * 60)
    
    # Load current data
    csv_path = KNOWLEDGE_DIR / "disease_symptom_trained.csv"
    json_path = KNOWLEDGE_DIR / "symptom_questions_trained.json"
    
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return False
    
    df = pd.read_csv(csv_path)
    print(f"📊 Loaded {len(df)} associations")
    print(f"   Unique symptoms: {df['symptom'].nunique()}")
    
    # Find problematic symptoms
    problematic = df[df['symptom'].str.match(r'^e\s*\d+|nowhere|\([rlRLdDgG]\)', na=False)]
    print(f"   Problematic entries: {len(problematic)}")
    
    # Transform symptom names
    print("\n🔄 Transforming symptom names...")
    symptom_mapping = {}
    new_questions = {}
    
    for symptom in df['symptom'].unique():
        new_name = transform_symptom_name(symptom)
        if new_name != symptom:
            symptom_mapping[symptom] = new_name
        
        # Generate question
        question_data = generate_question(new_name)
        new_questions[new_name] = question_data
    
    print(f"   Transformed {len(symptom_mapping)} symptom names")
    
    # Show some examples
    print("\n📝 Sample transformations:")
    examples = list(symptom_mapping.items())[:15]
    for old, new in examples:
        print(f"   '{old}' → '{new}'")
    
    # Apply transformations to DataFrame
    df['symptom'] = df['symptom'].map(lambda x: symptom_mapping.get(x, x))
    
    # Remove duplicates (keep highest weight)
    df = df.sort_values('weight', ascending=False)
    df = df.drop_duplicates(subset=['disease', 'symptom'], keep='first')
    
    # Save updated CSV
    backup_csv = csv_path.with_suffix('.csv.backup')
    if csv_path.exists():
        import shutil
        shutil.copy(csv_path, backup_csv)
        print(f"\n💾 Backup saved: {backup_csv}")
    
    df.to_csv(csv_path, index=False)
    print(f"✅ Updated CSV: {csv_path}")
    print(f"   Total associations: {len(df)}")
    print(f"   Unique symptoms: {df['symptom'].nunique()}")
    
    # Save updated questions JSON
    backup_json = json_path.with_suffix('.json.backup')
    if json_path.exists():
        import shutil
        shutil.copy(json_path, backup_json)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_questions, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated questions: {json_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ Knowledge Base Fixed!")
    print("=" * 60)
    print(f"   Diseases: {df['disease'].nunique()}")
    print(f"   Symptoms: {df['symptom'].nunique()}")
    print(f"   Questions: {len(new_questions)}")
    
    # Show sample of new questions
    print("\n📋 Sample Questions:")
    sample_symptoms = list(new_questions.items())[:10]
    for symptom, data in sample_symptoms:
        print(f"   • {symptom}")
        print(f"     Q: {data['question']}")
    
    return True


if __name__ == "__main__":
    fix_knowledge_base()
