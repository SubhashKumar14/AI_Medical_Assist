"""
Medical Report Analyzer using PaddleOCR

Analyzes medical reports (lab results, prescriptions, clinical notes) using:
1. PaddleOCR for text extraction (better than Tesseract for tables)
2. Pattern matching for medical values
3. Range checking for abnormal results

Features:
- Table structure recognition
- Multi-language support
- Lab value extraction and analysis
- Abnormality detection

Requirements:
    pip install paddlepaddle paddleocr

Usage:
    from report_analyzer import MedicalReportAnalyzer
    analyzer = MedicalReportAnalyzer()
    result = analyzer.analyze_report("lab_report.jpg")
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Try importing PaddleOCR
try:
    from paddleocr import PaddleOCR
    HAS_PADDLEOCR = True
except ImportError:
    HAS_PADDLEOCR = False
    print("⚠️ PaddleOCR not installed. Install with: pip install paddlepaddle paddleocr")

# Fallback to Tesseract
try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


@dataclass
class LabValue:
    """Represents an extracted lab value."""
    test_name: str
    value: float
    unit: str
    reference_min: float
    reference_max: float
    status: str  # 'normal', 'low', 'high', 'critical'
    raw_text: str


class MedicalReportAnalyzer:
    """
    Analyzes medical reports using OCR and pattern matching.
    """
    
    # Standard lab reference ranges
    LAB_REFERENCE_RANGES = {
        # Complete Blood Count (CBC)
        'hemoglobin': {'min': 12.0, 'max': 17.5, 'unit': 'g/dL', 'aliases': ['hgb', 'hb']},
        'hematocrit': {'min': 36, 'max': 50, 'unit': '%', 'aliases': ['hct']},
        'rbc': {'min': 4.0, 'max': 5.5, 'unit': 'M/uL', 'aliases': ['red blood cell', 'erythrocyte']},
        'wbc': {'min': 4.5, 'max': 11.0, 'unit': 'K/uL', 'aliases': ['white blood cell', 'leukocyte']},
        'platelet': {'min': 150000, 'max': 450000, 'unit': '/uL', 'aliases': ['plt', 'thrombocyte']},
        'mcv': {'min': 80, 'max': 100, 'unit': 'fL', 'aliases': ['mean corpuscular volume']},
        'mch': {'min': 27, 'max': 33, 'unit': 'pg', 'aliases': ['mean corpuscular hemoglobin']},
        
        # Metabolic Panel
        'glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL', 'aliases': ['blood sugar', 'fasting glucose']},
        'glucose_random': {'min': 70, 'max': 140, 'unit': 'mg/dL', 'aliases': ['random glucose']},
        'hba1c': {'min': 4.0, 'max': 5.6, 'unit': '%', 'aliases': ['glycated hemoglobin', 'a1c']},
        'creatinine': {'min': 0.6, 'max': 1.2, 'unit': 'mg/dL', 'aliases': ['cr', 'serum creatinine']},
        'bun': {'min': 7, 'max': 20, 'unit': 'mg/dL', 'aliases': ['blood urea nitrogen', 'urea']},
        'sodium': {'min': 136, 'max': 145, 'unit': 'mEq/L', 'aliases': ['na']},
        'potassium': {'min': 3.5, 'max': 5.0, 'unit': 'mEq/L', 'aliases': ['k']},
        'chloride': {'min': 98, 'max': 106, 'unit': 'mEq/L', 'aliases': ['cl']},
        'calcium': {'min': 8.5, 'max': 10.5, 'unit': 'mg/dL', 'aliases': ['ca']},
        
        # Liver Function
        'alt': {'min': 7, 'max': 56, 'unit': 'U/L', 'aliases': ['sgpt', 'alanine aminotransferase']},
        'ast': {'min': 10, 'max': 40, 'unit': 'U/L', 'aliases': ['sgot', 'aspartate aminotransferase']},
        'alp': {'min': 44, 'max': 147, 'unit': 'U/L', 'aliases': ['alkaline phosphatase']},
        'bilirubin': {'min': 0.1, 'max': 1.2, 'unit': 'mg/dL', 'aliases': ['total bilirubin']},
        'albumin': {'min': 3.5, 'max': 5.0, 'unit': 'g/dL', 'aliases': ['serum albumin']},
        
        # Lipid Panel
        'cholesterol': {'min': 0, 'max': 200, 'unit': 'mg/dL', 'aliases': ['total cholesterol']},
        'ldl': {'min': 0, 'max': 100, 'unit': 'mg/dL', 'aliases': ['low density lipoprotein']},
        'hdl': {'min': 40, 'max': 200, 'unit': 'mg/dL', 'aliases': ['high density lipoprotein']},
        'triglyceride': {'min': 0, 'max': 150, 'unit': 'mg/dL', 'aliases': ['tg']},
        
        # Thyroid
        'tsh': {'min': 0.4, 'max': 4.0, 'unit': 'mIU/L', 'aliases': ['thyroid stimulating hormone']},
        't3': {'min': 80, 'max': 200, 'unit': 'ng/dL', 'aliases': ['triiodothyronine']},
        't4': {'min': 4.5, 'max': 12.0, 'unit': 'ug/dL', 'aliases': ['thyroxine']},
        
        # Cardiac Markers
        'troponin': {'min': 0, 'max': 0.04, 'unit': 'ng/mL', 'aliases': ['troponin i', 'troponin t']},
        'bnp': {'min': 0, 'max': 100, 'unit': 'pg/mL', 'aliases': ['brain natriuretic peptide']},
        'crp': {'min': 0, 'max': 3.0, 'unit': 'mg/L', 'aliases': ['c-reactive protein']},
        
        # Vitals (for completeness)
        'blood_pressure_systolic': {'min': 90, 'max': 120, 'unit': 'mmHg', 'aliases': ['systolic', 'sbp']},
        'blood_pressure_diastolic': {'min': 60, 'max': 80, 'unit': 'mmHg', 'aliases': ['diastolic', 'dbp']},
        'heart_rate': {'min': 60, 'max': 100, 'unit': 'bpm', 'aliases': ['pulse', 'hr']},
        'temperature': {'min': 97.0, 'max': 99.0, 'unit': '°F', 'aliases': ['temp', 'body temperature']},
        'oxygen_saturation': {'min': 95, 'max': 100, 'unit': '%', 'aliases': ['spo2', 'o2 sat']},
    }
    
    # Critical values that require immediate attention
    CRITICAL_VALUES = {
        'glucose': {'critical_low': 50, 'critical_high': 400},
        'potassium': {'critical_low': 2.5, 'critical_high': 6.5},
        'sodium': {'critical_low': 120, 'critical_high': 160},
        'hemoglobin': {'critical_low': 7.0, 'critical_high': 20.0},
        'platelet': {'critical_low': 50000, 'critical_high': 1000000},
        'creatinine': {'critical_low': 0, 'critical_high': 10.0},
        'troponin': {'critical_low': 0, 'critical_high': 0.5},
    }
    
    def __init__(self, use_gpu: bool = False, lang: str = 'en'):
        """
        Initialize the analyzer.
        
        Args:
            use_gpu: Use GPU acceleration if available
            lang: Language for OCR ('en', 'ch', 'fr', etc.)
        """
        self.ocr = None
        self.lang = lang
        self.use_gpu = use_gpu
        
        if HAS_PADDLEOCR:
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=use_gpu,
                    show_log=False
                )
                print("✅ PaddleOCR initialized")
            except Exception as e:
                print(f"⚠️ PaddleOCR initialization failed: {e}")
        elif HAS_TESSERACT:
            print("⚠️ Using Tesseract as fallback")
        else:
            print("❌ No OCR engine available")
    
    def extract_text(self, image_path: str) -> Tuple[str, List[dict]]:
        """
        Extract text from image using OCR.
        
        Returns:
            Tuple of (full_text, list of text boxes with positions)
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        text_boxes = []
        full_text = ""
        
        if self.ocr:
            # Use PaddleOCR
            result = self.ocr.ocr(str(image_path), cls=True)
            
            if result and result[0]:
                lines = []
                for line in result[0]:
                    bbox, (text, confidence) = line
                    text_boxes.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': bbox
                    })
                    lines.append(text)
                full_text = '\n'.join(lines)
        
        elif HAS_TESSERACT:
            # Fallback to Tesseract
            img = Image.open(image_path)
            full_text = pytesseract.image_to_string(img)
            text_boxes = [{'text': full_text, 'confidence': 0.9}]
        
        else:
            raise RuntimeError("No OCR engine available")
        
        return full_text, text_boxes
    
    def parse_lab_values(self, text: str) -> List[LabValue]:
        """
        Parse lab values from extracted text.
        """
        lab_values = []
        text_lower = text.lower()
        
        for test_name, ref_data in self.LAB_REFERENCE_RANGES.items():
            # Build search pattern including aliases
            search_terms = [test_name] + ref_data.get('aliases', [])
            
            for term in search_terms:
                # Pattern: Test Name followed by numbers
                # Handles various formats: "Glucose: 120", "Glucose 120 mg/dL", "120 glucose"
                patterns = [
                    rf'{re.escape(term)}[:\s]+(\d+\.?\d*)',
                    rf'(\d+\.?\d*)\s*{re.escape(term)}',
                    rf'{re.escape(term)}.*?(\d+\.?\d*)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        try:
                            value = float(match.group(1))
                            
                            # Determine status
                            status = self._determine_status(test_name, value, ref_data)
                            
                            lab_values.append(LabValue(
                                test_name=test_name,
                                value=value,
                                unit=ref_data['unit'],
                                reference_min=ref_data['min'],
                                reference_max=ref_data['max'],
                                status=status,
                                raw_text=match.group(0)
                            ))
                            break
                        except (ValueError, IndexError):
                            continue
                
                if any(lv.test_name == test_name for lv in lab_values):
                    break  # Found value for this test, move on
        
        return lab_values
    
    def _determine_status(self, test_name: str, value: float, ref_data: dict) -> str:
        """Determine if value is normal, low, high, or critical."""
        # Check critical values first
        if test_name in self.CRITICAL_VALUES:
            crit = self.CRITICAL_VALUES[test_name]
            if value <= crit['critical_low']:
                return 'critical_low'
            if value >= crit['critical_high']:
                return 'critical_high'
        
        # Check normal range
        if value < ref_data['min']:
            return 'low'
        elif value > ref_data['max']:
            return 'high'
        else:
            return 'normal'
    
    def analyze_report(self, image_path: str) -> Dict:
        """
        Analyze a medical report image.
        
        Args:
            image_path: Path to the report image
            
        Returns:
            Dictionary with analysis results
        """
        print(f"🔍 Analyzing: {image_path}")
        
        # Extract text
        full_text, text_boxes = self.extract_text(image_path)
        
        # Parse lab values
        lab_values = self.parse_lab_values(full_text)
        
        # Generate findings
        findings = self._generate_findings(lab_values)
        
        # Identify critical alerts
        critical_alerts = [lv for lv in lab_values if 'critical' in lv.status]
        
        # Build response
        result = {
            'timestamp': datetime.now().isoformat(),
            'source_file': str(image_path),
            'raw_text': full_text,
            'text_boxes_count': len(text_boxes),
            'lab_values': [
                {
                    'test': lv.test_name,
                    'value': lv.value,
                    'unit': lv.unit,
                    'reference_range': f"{lv.reference_min}-{lv.reference_max}",
                    'status': lv.status
                }
                for lv in lab_values
            ],
            'findings': findings,
            'critical_alerts': [
                f"⚠️ CRITICAL: {lv.test_name} = {lv.value} {lv.unit} ({lv.status})"
                for lv in critical_alerts
            ],
            'summary': {
                'total_tests_found': len(lab_values),
                'normal_count': len([lv for lv in lab_values if lv.status == 'normal']),
                'abnormal_count': len([lv for lv in lab_values if lv.status != 'normal']),
                'critical_count': len(critical_alerts)
            }
        }
        
        return result
    
    def _generate_findings(self, lab_values: List[LabValue]) -> List[str]:
        """Generate human-readable findings from lab values."""
        findings = []
        
        for lv in lab_values:
            if lv.status == 'normal':
                findings.append(f"✅ {lv.test_name.title()}: {lv.value} {lv.unit} (Normal)")
            elif lv.status == 'low':
                findings.append(
                    f"⚠️ Low {lv.test_name.title()}: {lv.value} {lv.unit} "
                    f"(Normal: {lv.reference_min}-{lv.reference_max})"
                )
            elif lv.status == 'high':
                findings.append(
                    f"⚠️ High {lv.test_name.title()}: {lv.value} {lv.unit} "
                    f"(Normal: {lv.reference_min}-{lv.reference_max})"
                )
            elif 'critical' in lv.status:
                findings.append(
                    f"🚨 CRITICAL {lv.test_name.title()}: {lv.value} {lv.unit} "
                    f"- IMMEDIATE ATTENTION REQUIRED"
                )
        
        return findings
    
    def extract_patient_info(self, text: str) -> Dict:
        """Extract patient information from report text."""
        info = {}
        
        # Patient name patterns
        name_match = re.search(r'(?:patient|name)[:\s]+([A-Za-z\s]+)', text, re.IGNORECASE)
        if name_match:
            info['name'] = name_match.group(1).strip()
        
        # Date patterns
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
        if date_match:
            info['date'] = date_match.group(1)
        
        # Age patterns
        age_match = re.search(r'(?:age)[:\s]+(\d+)', text, re.IGNORECASE)
        if age_match:
            info['age'] = int(age_match.group(1))
        
        # Gender patterns
        gender_match = re.search(r'\b(male|female|m|f)\b', text, re.IGNORECASE)
        if gender_match:
            gender = gender_match.group(1).lower()
            info['gender'] = 'male' if gender in ['m', 'male'] else 'female'
        
        return info
    
    def generate_recommendations(self, lab_values: List[LabValue]) -> List[str]:
        """Generate recommendations based on lab findings."""
        recommendations = []
        
        for lv in lab_values:
            if lv.status == 'normal':
                continue
            
            # Specific recommendations based on test
            if lv.test_name in ['glucose', 'hba1c']:
                if lv.status == 'high':
                    recommendations.append(
                        f"Elevated {lv.test_name}: Consider diabetes screening, "
                        "dietary modifications, and follow-up testing."
                    )
                elif lv.status == 'low':
                    recommendations.append(
                        f"Low {lv.test_name}: Evaluate for hypoglycemia causes. "
                        "Consider medication review."
                    )
            
            elif lv.test_name in ['hemoglobin', 'rbc', 'hematocrit']:
                if lv.status == 'low':
                    recommendations.append(
                        f"Low {lv.test_name}: Evaluate for anemia. Consider iron studies, "
                        "B12, folate levels. Rule out GI bleeding if applicable."
                    )
            
            elif lv.test_name in ['cholesterol', 'ldl', 'triglyceride']:
                if lv.status == 'high':
                    recommendations.append(
                        f"Elevated {lv.test_name}: Recommend lifestyle modifications. "
                        "Consider statin therapy if cardiovascular risk elevated."
                    )
            
            elif lv.test_name in ['creatinine', 'bun']:
                if lv.status == 'high':
                    recommendations.append(
                        f"Elevated {lv.test_name}: Evaluate kidney function. "
                        "Consider GFR calculation, hydration status, nephrology consult."
                    )
            
            elif lv.test_name in ['alt', 'ast', 'bilirubin']:
                if lv.status == 'high':
                    recommendations.append(
                        f"Elevated {lv.test_name}: Evaluate liver function. "
                        "Consider hepatitis panel, imaging studies, medication review."
                    )
            
            elif lv.test_name == 'tsh':
                if lv.status == 'high':
                    recommendations.append(
                        "Elevated TSH suggests hypothyroidism. Consider T4 levels, "
                        "thyroid antibodies, endocrine referral."
                    )
                elif lv.status == 'low':
                    recommendations.append(
                        "Low TSH suggests hyperthyroidism. Consider T3/T4 levels, "
                        "thyroid antibodies, endocrine referral."
                    )
            
            elif lv.test_name == 'troponin':
                if lv.status in ['high', 'critical_high']:
                    recommendations.append(
                        "⚠️ URGENT: Elevated troponin indicates possible cardiac injury. "
                        "Consider serial troponins, ECG, cardiology consultation."
                    )
        
        return recommendations


def main():
    """Demo usage."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python report_analyzer.py <image_path>")
        print("\nDemo mode: Creating sample analysis...")
        
        # Demo with sample text
        analyzer = MedicalReportAnalyzer()
        
        sample_text = """
        Patient: John Doe
        Date: 01/15/2024
        Age: 45  Gender: Male
        
        Laboratory Results:
        Glucose: 145 mg/dL
        Hemoglobin: 10.5 g/dL
        WBC: 8.5 K/uL
        Platelet: 250000 /uL
        Creatinine: 1.8 mg/dL
        Sodium: 140 mEq/L
        Potassium: 4.2 mEq/L
        ALT: 75 U/L
        Cholesterol: 245 mg/dL
        LDL: 165 mg/dL
        TSH: 5.5 mIU/L
        """
        
        lab_values = analyzer.parse_lab_values(sample_text)
        findings = analyzer._generate_findings(lab_values)
        recommendations = analyzer.generate_recommendations(lab_values)
        
        print("\n" + "=" * 60)
        print("📋 MEDICAL REPORT ANALYSIS")
        print("=" * 60)
        
        print("\n📊 Lab Values Detected:")
        for lv in lab_values:
            print(f"   {lv.test_name}: {lv.value} {lv.unit} [{lv.status}]")
        
        print("\n📝 Findings:")
        for f in findings:
            print(f"   {f}")
        
        print("\n💡 Recommendations:")
        for r in recommendations:
            print(f"   • {r}")
        
        return
    
    # Analyze provided image
    image_path = sys.argv[1]
    analyzer = MedicalReportAnalyzer()
    result = analyzer.analyze_report(image_path)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
