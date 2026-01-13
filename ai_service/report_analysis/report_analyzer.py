"""
Medical Report Analyzer with PaddleOCR
=======================================

Extracts and analyzes medical reports from PDFs/images using PaddleOCR.
PaddleOCR provides better table structure recognition than Tesseract.

Features:
- PDF/Image text extraction
- Lab value detection with reference range comparison
- Critical finding highlighting
- Table structure preservation

Usage:
    analyzer = MedicalReportAnalyzer()
    result = analyzer.analyze_report("report.pdf")
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Try PaddleOCR first, fallback to Tesseract
PADDLE_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    logger.info("PaddleOCR not installed. Trying Tesseract fallback.")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    logger.info("Tesseract not installed.")

# Load reference ranges
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class MedicalReportAnalyzer:
    """
    Medical report analyzer using OCR and rule-based value extraction.
    """
    
    def __init__(self, use_paddle: bool = True):
        """
        Initialize analyzer.
        
        Args:
            use_paddle: Prefer PaddleOCR over Tesseract
        """
        self.ocr = None
        self.reference_ranges = self._load_reference_ranges()
        
        if use_paddle and PADDLE_AVAILABLE:
            try:
                self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                logger.info("Using PaddleOCR for text extraction")
            except Exception as e:
                logger.warning(f"PaddleOCR init failed: {e}")
        
        if self.ocr is None and TESSERACT_AVAILABLE:
            logger.info("Using Tesseract OCR fallback")
    
    def _load_reference_ranges(self) -> Dict[str, Dict]:
        """Load lab reference ranges from JSON."""
        json_path = KNOWLEDGE_DIR / "lab_reference_ranges.json"
        
        if json_path.exists():
            with open(json_path, 'r') as f:
                data = json.load(f)
                return data.get('ranges', data)
        
        # Default ranges if file not found
        return {
            "hemoglobin": {"min": 12.0, "max": 17.0, "unit": "g/dL"},
            "hb": {"min": 12.0, "max": 17.0, "unit": "g/dL"},
            "wbc": {"min": 4000, "max": 11000, "unit": "cells/mm3"},
            "platelet": {"min": 150000, "max": 450000, "unit": "/µL"},
            "glucose": {"min": 70, "max": 140, "unit": "mg/dL"},
            "creatinine": {"min": 0.6, "max": 1.2, "unit": "mg/dL"},
            "sgpt": {"min": 7, "max": 56, "unit": "U/L"},
            "sgot": {"min": 10, "max": 40, "unit": "U/L"},
            "bilirubin": {"min": 0.1, "max": 1.2, "unit": "mg/dL"},
            "cholesterol": {"min": 0, "max": 200, "unit": "mg/dL"},
            "sodium": {"min": 136, "max": 145, "unit": "mEq/L"},
            "potassium": {"min": 3.5, "max": 5.0, "unit": "mEq/L"},
        }
    
    def extract_text(self, image_path: str) -> str:
        """
        Extract text from image/PDF using OCR.
        
        Args:
            image_path: Path to image or PDF file
            
        Returns:
            Extracted text
        """
        if not os.path.exists(image_path):
            return ""
        
        # PaddleOCR extraction
        if self.ocr is not None:
            try:
                result = self.ocr.ocr(image_path, cls=True)
                if result and result[0]:
                    lines = [line[1][0] for line in result[0]]
                    return "\n".join(lines)
            except Exception as e:
                logger.warning(f"PaddleOCR extraction failed: {e}")
        
        # Tesseract fallback
        if TESSERACT_AVAILABLE:
            try:
                image = Image.open(image_path)
                return pytesseract.image_to_string(image)
            except Exception as e:
                logger.warning(f"Tesseract extraction failed: {e}")
        
        return ""
    
    def analyze_report(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze a medical report image/PDF.
        
        Returns extracted values, abnormal findings, and alerts.
        """
        raw_text = self.extract_text(image_path)
        
        if not raw_text:
            return {
                "success": False,
                "error": "Could not extract text from image",
                "raw_text": ""
            }
        
        # Extract lab values
        lab_values = self._extract_lab_values(raw_text)
        
        # Check for abnormalities
        abnormal_findings = self._check_abnormalities(lab_values)
        
        # Look for critical keywords
        alerts = self._find_alerts(raw_text)
        
        # Extract blood pressure specifically
        bp_reading = self._extract_blood_pressure(raw_text)
        if bp_reading:
            lab_values['blood_pressure'] = bp_reading
            if bp_reading.get('status') != 'normal':
                abnormal_findings.append(bp_reading)
        
        return {
            "success": True,
            "raw_text": raw_text,
            "lab_values": lab_values,
            "abnormal_findings": abnormal_findings,
            "alerts": alerts,
            "summary": self._generate_summary(lab_values, abnormal_findings, alerts)
        }
    
    def _extract_lab_values(self, text: str) -> Dict[str, Dict]:
        """Extract lab test values from text using regex patterns."""
        values = {}
        text_lower = text.lower()
        
        # Common patterns: "Test Name: 123.45 unit" or "Test Name 123.45"
        patterns = [
            # Hemoglobin
            (r'h[ae]moglobin[:\s]+(\d+\.?\d*)', 'hemoglobin'),
            (r'\bhb[:\s]+(\d+\.?\d*)', 'hemoglobin'),
            # WBC
            (r'wbc[:\s]*count?[:\s]*(\d+\.?\d*)', 'wbc'),
            (r'white\s*blood\s*cell[s]?[:\s]*(\d+\.?\d*)', 'wbc'),
            # Platelet
            (r'platelet[s]?[:\s]*count?[:\s]*(\d+\.?\d*)', 'platelet'),
            # Glucose
            (r'glucose[:\s]+(\d+\.?\d*)', 'glucose'),
            (r'blood\s*sugar[:\s]+(\d+\.?\d*)', 'glucose'),
            # Creatinine
            (r'creatinine[:\s]+(\d+\.?\d*)', 'creatinine'),
            # Liver enzymes
            (r'sgpt[:\s]+(\d+\.?\d*)', 'sgpt'),
            (r'alt[:\s]+(\d+\.?\d*)', 'sgpt'),
            (r'sgot[:\s]+(\d+\.?\d*)', 'sgot'),
            (r'ast[:\s]+(\d+\.?\d*)', 'sgot'),
            # Bilirubin
            (r'bilirubin[:\s]+(\d+\.?\d*)', 'bilirubin'),
            # Cholesterol
            (r'cholesterol[:\s]+(\d+\.?\d*)', 'cholesterol'),
            # Electrolytes
            (r'sodium[:\s]+(\d+\.?\d*)', 'sodium'),
            (r'potassium[:\s]+(\d+\.?\d*)', 'potassium'),
        ]
        
        for pattern, test_name in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = float(match.group(1))
                    ref = self.reference_ranges.get(test_name, {})
                    values[test_name] = {
                        "value": value,
                        "unit": ref.get("unit", ""),
                        "reference_min": ref.get("min"),
                        "reference_max": ref.get("max")
                    }
                except ValueError:
                    pass
        
        return values
    
    def _extract_blood_pressure(self, text: str) -> Optional[Dict]:
        """Extract blood pressure reading."""
        # Patterns: "120/80", "BP: 120/80", "Blood Pressure 120/80"
        pattern = r'(?:bp|blood\s*pressure)?[:\s]*(\d{2,3})[/-](\d{2,3})'
        match = re.search(pattern, text.lower())
        
        if match:
            systolic = int(match.group(1))
            diastolic = int(match.group(2))
            
            status = "normal"
            if systolic > 140 or diastolic > 90:
                status = "high"
            elif systolic < 90 or diastolic < 60:
                status = "low"
            
            return {
                "test": "blood_pressure",
                "systolic": systolic,
                "diastolic": diastolic,
                "reading": f"{systolic}/{diastolic}",
                "status": status
            }
        
        return None
    
    def _check_abnormalities(self, lab_values: Dict) -> List[Dict]:
        """Check lab values against reference ranges."""
        abnormal = []
        
        for test_name, data in lab_values.items():
            value = data.get('value')
            ref_min = data.get('reference_min')
            ref_max = data.get('reference_max')
            
            if value is None:
                continue
            
            status = "normal"
            if ref_min is not None and value < ref_min:
                status = "low"
            elif ref_max is not None and value > ref_max:
                status = "high"
            
            if status != "normal":
                abnormal.append({
                    "test": test_name,
                    "value": value,
                    "unit": data.get('unit', ''),
                    "status": status,
                    "reference": f"{ref_min}-{ref_max}"
                })
        
        return abnormal
    
    def _find_alerts(self, text: str) -> List[str]:
        """Find critical keywords that need attention."""
        alerts = []
        text_lower = text.lower()
        
        critical_keywords = [
            ("positive", "Positive result detected"),
            ("detected", "Abnormality detected"),
            ("critical", "Critical value present"),
            ("urgent", "Urgent attention needed"),
            ("abnormal", "Abnormal finding"),
            ("high risk", "High risk indicator"),
            ("low risk", None),  # Skip "low risk"
        ]
        
        for keyword, message in critical_keywords:
            if keyword in text_lower and message:
                # Find the line containing the keyword
                for line in text.split('\n'):
                    if keyword in line.lower() and "negative" not in line.lower():
                        alerts.append(f"{message}: {line.strip()[:100]}")
                        break
        
        return alerts
    
    def _generate_summary(self, lab_values: Dict, abnormal: List, alerts: List) -> str:
        """Generate a brief summary of findings."""
        parts = []
        
        if not lab_values:
            return "No lab values could be extracted from the report."
        
        parts.append(f"Extracted {len(lab_values)} lab values.")
        
        if abnormal:
            parts.append(f"{len(abnormal)} abnormal finding(s) detected:")
            for ab in abnormal[:3]:  # Top 3
                parts.append(f"  - {ab['test']}: {ab['value']} ({ab['status']})")
        else:
            parts.append("All extracted values are within normal ranges.")
        
        if alerts:
            parts.append(f"{len(alerts)} alert(s) flagged for review.")
        
        return "\n".join(parts)


# Convenience function
def analyze_report(image_path: str) -> Dict[str, Any]:
    """Quick function to analyze a medical report."""
    analyzer = MedicalReportAnalyzer()
    return analyzer.analyze_report(image_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python report_analyzer.py <image_path>")
        sys.exit(1)
    
    result = analyze_report(sys.argv[1])
    
    if result['success']:
        print("\n📋 REPORT ANALYSIS")
        print("=" * 50)
        print(result['summary'])
        
        if result['abnormal_findings']:
            print("\n⚠️ ABNORMAL FINDINGS:")
            for finding in result['abnormal_findings']:
                print(f"  • {finding['test']}: {finding['value']} {finding.get('unit', '')} ({finding['status']})")
        
        if result['alerts']:
            print("\n🚨 ALERTS:")
            for alert in result['alerts']:
                print(f"  • {alert}")
    else:
        print(f"❌ Error: {result['error']}")
