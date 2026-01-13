"""
DDXPlus Dataset Trainer

Converts the DDXPlus dataset (from Figshare/HuggingFace) into the probability
matrix format used by the symptom elimination engine.

DDXPlus is a large-scale synthetic medical dataset with:
- 1M+ synthetic patient cases
- 49 pathologies (diseases)
- 223 symptoms/evidences
- Scientifically validated by medical professionals

This script handles both:
1. The metadata files (release_conditions.json, release_evidences.json)
2. The full patient CSV files for complete probability calculation

Usage:
    python train_ddxplus.py --data-dir ./raw_data/ddxplus
"""

import json
import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
KNOWLEDGE_DIR = SCRIPT_DIR.parent / "knowledge"
DEFAULT_DATA_DIR = SCRIPT_DIR.parent.parent / "evaluation" / "datasets"


class DDXPlusTrainer:
    """
    Trains the knowledge base from DDXPlus dataset.
    """
    
    def __init__(self, data_dir: str = None, output_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.output_dir = Path(output_dir) if output_dir else KNOWLEDGE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.conditions = {}
        self.evidences = {}
        self.probability_matrix = defaultdict(lambda: defaultdict(float))
        self.disease_counts = defaultdict(int)
        
    def load_metadata(self) -> bool:
        """Load DDXPlus condition and evidence definitions."""
        print("📂 Loading DDXPlus Metadata...")
        
        # Try multiple possible locations
        possible_paths = [
            self.data_dir / "release_conditions.json",
            self.data_dir / "ddxplus_release" / "release_conditions.json",
            KNOWLEDGE_DIR / "ddxplus_conditions.json",
        ]
        
        conditions_path = None
        for path in possible_paths:
            if path.exists():
                conditions_path = path
                break
        
        possible_paths = [
            self.data_dir / "release_evidences.json",
            self.data_dir / "ddxplus_release" / "release_evidences.json",
            KNOWLEDGE_DIR / "ddxplus_evidences.json",
        ]
        
        evidences_path = None
        for path in possible_paths:
            if path.exists():
                evidences_path = path
                break
        
        if not conditions_path or not evidences_path:
            print("❌ DDXPlus metadata files not found.")
            print("   Expected: release_conditions.json and release_evidences.json")
            print(f"   Searched in: {self.data_dir}")
            return False
        
        try:
            with open(conditions_path, 'r') as f:
                self.conditions = json.load(f)
            print(f"   ✅ Loaded {len(self.conditions)} conditions")
            
            with open(evidences_path, 'r') as f:
                self.evidences = json.load(f)
            print(f"   ✅ Loaded {len(self.evidences)} evidences")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading metadata: {e}")
            return False
    
    def extract_symptom_name(self, evidence_code: str) -> str:
        """Extract readable symptom name from evidence code."""
        if evidence_code not in self.evidences:
            return evidence_code
        
        ev_data = self.evidences[evidence_code]
        
        # Try different fields for the name
        if 'question_en' in ev_data:
            # Extract meaningful part from question
            question = ev_data['question_en']
            # Remove common prefixes
            for prefix in ['Do you have ', 'Have you ', 'Are you ', 'Is your ', 'Does your ']:
                if question.startswith(prefix):
                    question = question[len(prefix):]
            return question.rstrip('?').strip()
        
        if 'name' in ev_data and ev_data['name'] != evidence_code:
            return ev_data['name']
        
        return evidence_code
    
    def train_from_metadata(self):
        """Train probability matrix from DDXPlus metadata (fast method)."""
        if not self.load_metadata():
            return False
        
        print("\n🧠 Training from DDXPlus Metadata...")
        
        training_rows = []
        
        for cond_code, cond_data in self.conditions.items():
            # Get disease name
            disease_name = cond_data.get('cond-name-eng', 
                          cond_data.get('condition_name', cond_code))
            
            # Get symptom probabilities
            # DDXPlus stores symptoms in 'symptoms' field
            symptoms = cond_data.get('symptoms', {})
            
            # Also check 'antecedents' for risk factors
            antecedents = cond_data.get('antecedents', {})
            
            all_evidences = {**symptoms, **antecedents}
            
            for ev_code, expected_prob in all_evidences.items():
                # Handle different probability formats
                if isinstance(expected_prob, dict):
                    prob = expected_prob.get('probability', 0.5)
                elif isinstance(expected_prob, (int, float)):
                    prob = float(expected_prob)
                else:
                    prob = 0.5
                
                # Filter very low probability symptoms
                if prob < 0.05:
                    continue
                
                # Get readable symptom name
                symptom_name = self.extract_symptom_name(ev_code)
                
                training_rows.append({
                    'disease': disease_name,
                    'symptom': symptom_name,
                    'weight': round(prob, 3),
                    'evidence_code': ev_code
                })
        
        if not training_rows:
            print("⚠️ No training data extracted from metadata.")
            print("   Trying to extract from condition definitions...")
            training_rows = self._extract_from_definitions()
        
        return self._save_training_data(training_rows)
    
    def _extract_from_definitions(self) -> list:
        """Fallback: Extract symptom associations from condition definitions."""
        training_rows = []
        
        for cond_code, cond_data in self.conditions.items():
            disease_name = cond_data.get('cond-name-eng', cond_code)
            
            # Look for any field that might contain symptoms
            for key in ['symptoms', 'antecedents', 'evidences', 'findings']:
                if key in cond_data:
                    data = cond_data[key]
                    if isinstance(data, dict):
                        for ev_code, prob in data.items():
                            symptom_name = self.extract_symptom_name(ev_code)
                            if isinstance(prob, (int, float)) and prob > 0.05:
                                training_rows.append({
                                    'disease': disease_name,
                                    'symptom': symptom_name,
                                    'weight': round(float(prob), 3),
                                    'evidence_code': ev_code
                                })
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, str):
                                symptom_name = self.extract_symptom_name(item)
                                training_rows.append({
                                    'disease': disease_name,
                                    'symptom': symptom_name,
                                    'weight': 0.5,  # Default probability
                                    'evidence_code': item
                                })
        
        return training_rows
    
    def train_from_patients(self, patient_file: str = None, max_rows: int = 100000):
        """
        Train probability matrix from patient CSV (accurate method).
        
        This calculates P(Symptom|Disease) directly from patient data:
        P(S|D) = count(patients with S and D) / count(patients with D)
        """
        if not self.load_metadata():
            return False
        
        # Find patient file
        if patient_file:
            patient_path = Path(patient_file)
        else:
            possible_paths = [
                self.data_dir / "release_train_patients.csv",
                self.data_dir / "ddxplus_release" / "release_train_patients" / "release_train_patients",
                self.data_dir / "train.csv",
            ]
            patient_path = None
            for path in possible_paths:
                if path.exists():
                    patient_path = path
                    break
        
        if not patient_path or not patient_path.exists():
            print("⚠️ Patient file not found. Using metadata-only training.")
            return self.train_from_metadata()
        
        print(f"\n📊 Loading patient data from {patient_path}...")
        
        try:
            df = pd.read_csv(patient_path, nrows=max_rows)
            print(f"   Loaded {len(df)} patient records")
        except Exception as e:
            print(f"❌ Error loading patient file: {e}")
            return self.train_from_metadata()
        
        # Identify columns
        disease_col = self._find_column(df, ['PATHOLOGY', 'pathology', 'disease', 'DISEASE'])
        evidence_col = self._find_column(df, ['EVIDENCES', 'evidences', 'symptoms', 'SYMPTOMS'])
        
        if not disease_col:
            print("❌ Could not find disease column")
            return False
        
        print(f"\n🧠 Training from {len(df)} patient records...")
        
        # Count occurrences
        symptom_disease_counts = defaultdict(lambda: defaultdict(int))
        disease_counts = defaultdict(int)
        
        for _, row in df.iterrows():
            disease = str(row[disease_col])
            disease_counts[disease] += 1
            
            # Parse evidences
            if evidence_col and evidence_col in row:
                evidences_str = str(row[evidence_col])
                # Handle different formats
                if evidences_str.startswith('['):
                    # JSON array format
                    try:
                        evidences = json.loads(evidences_str.replace("'", '"'))
                    except:
                        evidences = []
                else:
                    # Comma-separated
                    evidences = [e.strip() for e in evidences_str.split(',')]
                
                for ev in evidences:
                    if ev:
                        symptom_disease_counts[disease][ev] += 1
        
        # Calculate probabilities
        training_rows = []
        
        for disease, symptoms in symptom_disease_counts.items():
            total_cases = disease_counts[disease]
            if total_cases < 10:  # Skip very rare diseases
                continue
            
            for symptom_code, count in symptoms.items():
                prob = count / total_cases
                
                if prob < 0.05:  # Skip rare symptoms
                    continue
                
                symptom_name = self.extract_symptom_name(symptom_code)
                
                training_rows.append({
                    'disease': disease,
                    'symptom': symptom_name,
                    'weight': round(prob, 3),
                    'evidence_code': symptom_code
                })
        
        return self._save_training_data(training_rows)
    
    def _find_column(self, df: pd.DataFrame, candidates: list) -> str:
        """Find first matching column."""
        for col in candidates:
            if col in df.columns:
                return col
        return None
    
    def _save_training_data(self, training_rows: list) -> bool:
        """Save the training data to CSV."""
        if not training_rows:
            print("❌ No training data to save")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(training_rows)
        
        # Remove duplicates (keep highest weight)
        df = df.sort_values('weight', ascending=False)
        df = df.drop_duplicates(subset=['disease', 'symptom'], keep='first')
        
        # Save main file
        output_path = self.output_dir / "disease_symptom_ddxplus.csv"
        df[['disease', 'symptom', 'weight']].to_csv(output_path, index=False)
        
        # Save with evidence codes for reference
        full_path = self.output_dir / "disease_symptom_ddxplus_full.csv"
        df.to_csv(full_path, index=False)
        
        # Generate summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'source': 'DDXPlus Dataset',
            'total_associations': len(df),
            'unique_diseases': len(df['disease'].unique()),
            'unique_symptoms': len(df['symptom'].unique()),
            'diseases': sorted(df['disease'].unique().tolist()),
            'top_symptoms': df['symptom'].value_counts().head(20).to_dict()
        }
        
        summary_path = self.output_dir / "ddxplus_training_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ DDXPlus Training Complete!")
        print("=" * 60)
        print(f"   📊 Total Associations: {summary['total_associations']}")
        print(f"   🏥 Unique Diseases:    {summary['unique_diseases']}")
        print(f"   🩺 Unique Symptoms:    {summary['unique_symptoms']}")
        print(f"\n   📁 Output: {output_path}")
        print(f"   📁 Full:   {full_path}")
        print(f"   📁 Summary: {summary_path}")
        
        return True
    
    def merge_with_existing(self, existing_path: str = None):
        """Merge DDXPlus data with existing knowledge base."""
        if existing_path is None:
            existing_path = self.output_dir / "disease_symptom_trained.csv"
        
        existing_path = Path(existing_path)
        ddxplus_path = self.output_dir / "disease_symptom_ddxplus.csv"
        
        if not existing_path.exists() or not ddxplus_path.exists():
            print("⚠️ Cannot merge: files not found")
            return
        
        print("\n🔗 Merging DDXPlus with existing knowledge base...")
        
        df_existing = pd.read_csv(existing_path)
        df_ddxplus = pd.read_csv(ddxplus_path)
        
        # Combine (DDXPlus takes priority for overlaps)
        df_combined = pd.concat([df_existing, df_ddxplus])
        df_combined = df_combined.sort_values('weight', ascending=False)
        df_combined = df_combined.drop_duplicates(subset=['disease', 'symptom'], keep='first')
        
        merged_path = self.output_dir / "disease_symptom_merged.csv"
        df_combined.to_csv(merged_path, index=False)
        
        print(f"✅ Merged knowledge base saved: {merged_path}")
        print(f"   Total: {len(df_combined)} associations")


def main():
    parser = argparse.ArgumentParser(description='Train knowledge base from DDXPlus')
    parser.add_argument('--data-dir', '-d', type=str, help='Path to DDXPlus data directory')
    parser.add_argument('--output-dir', '-o', type=str, help='Output directory')
    parser.add_argument('--from-patients', '-p', action='store_true',
                       help='Train from patient CSV (slower but more accurate)')
    parser.add_argument('--patient-file', type=str, help='Path to patient CSV')
    parser.add_argument('--max-rows', '-m', type=int, default=100000,
                       help='Maximum patient rows to process')
    parser.add_argument('--merge', action='store_true',
                       help='Merge with existing knowledge base')
    
    args = parser.parse_args()
    
    trainer = DDXPlusTrainer(data_dir=args.data_dir, output_dir=args.output_dir)
    
    if args.from_patients:
        trainer.train_from_patients(args.patient_file, args.max_rows)
    else:
        trainer.train_from_metadata()
    
    if args.merge:
        trainer.merge_with_existing()


if __name__ == "__main__":
    main()
