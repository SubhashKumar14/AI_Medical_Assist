"""
Medical Report Parser

Parse lab values from OCR text and compare against reference ranges.
Identifies abnormal findings for review.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Path to reference ranges
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class ReportParser:
    """
    Parser for medical lab reports.
    
    Extracts common lab values and flags abnormalities.
    """
    
    def __init__(self):
        """Initialize parser with reference ranges."""
        self.reference_ranges = self._load_reference_ranges()
        self.lab_patterns = self._build_lab_patterns()
    
    def _load_reference_ranges(self) -> Dict[str, Dict]:
        """Load lab reference ranges from JSON."""
        json_path = KNOWLEDGE_DIR / "lab_reference_ranges.json"
        
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert JSON format to internal format with aliases
                if "ranges" in data:
                    return self._convert_json_format(data["ranges"])
                return data
    
    def _convert_json_format(self, ranges: Dict) -> Dict:
        """Convert JSON format to internal format with aliases."""
        result = {}
        alias_map = {
            "hemoglobin": ["hb", "hgb", "hemoglobin"],
            "wbc": ["wbc", "white blood cell", "leukocyte", "leucocyte"],
            "platelets": ["plt", "platelet", "thrombocyte", "platelets"],
            "rbc": ["rbc", "red blood cell", "erythrocyte"],
            "hematocrit": ["hct", "hematocrit", "pcv"],
            "creatinine": ["creatinine", "creat"],
            "blood_urea": ["bun", "blood urea", "urea"],
            "glucose_fasting": ["fbs", "fasting glucose", "fasting blood sugar", "glucose fasting"],
            "glucose_random": ["rbs", "random glucose", "blood sugar"],
            "hba1c": ["hba1c", "a1c", "glycated hemoglobin"],
            "cholesterol_total": ["total cholesterol", "cholesterol"],
            "ldl": ["ldl", "ldl cholesterol", "bad cholesterol"],
            "hdl": ["hdl", "hdl cholesterol", "good cholesterol"],
            "triglycerides": ["triglycerides", "tg"],
            "sgpt": ["sgpt", "alt", "alanine aminotransferase"],
            "sgot": ["sgot", "ast", "aspartate aminotransferase"],
            "bilirubin_total": ["bilirubin", "total bilirubin"],
            "crp": ["crp", "c-reactive protein"],
            "esr": ["esr", "erythrocyte sedimentation rate"],
            "tsh": ["tsh", "thyroid stimulating hormone"],
            "t3": ["t3", "triiodothyronine"],
            "t4": ["t4", "thyroxine"],
            "vitamin_d": ["vitamin d", "25-oh vitamin d", "vit d"],
            "vitamin_b12": ["vitamin b12", "b12", "cobalamin"],
            "sodium": ["sodium", "na"],
            "potassium": ["potassium", "k"],
            "calcium": ["calcium", "ca"],
        }
        
        for test_name, config in ranges.items():
            aliases = alias_map.get(test_name, [test_name])
            unit = config.get("unit", "")
            
            # Get reference values
            if "universal" in config:
                default = {"min": config["universal"].get("low", 0), "max": config["universal"].get("high", 999)}
            elif "male" in config:
                default = {"min": config["male"].get("low", 0), "max": config["male"].get("high", 999)}
            else:
                default = {"min": 0, "max": 999}
            
            result[test_name] = {
                "aliases": aliases,
                "unit": unit,
                "default": default
            }
            
            # Add gender-specific ranges if available
            if "male" in config:
                result[test_name]["male"] = {"min": config["male"].get("low", 0), "max": config["male"].get("high", 999)}
            if "female" in config:
                result[test_name]["female"] = {"min": config["female"].get("low", 0), "max": config["female"].get("high", 999)}
        
        return result
        
        # Default reference ranges
        return {
            "hemoglobin": {
                "aliases": ["hb", "hgb", "hemoglobin"],
                "unit": "g/dL",
                "male": {"min": 13.5, "max": 17.5},
                "female": {"min": 12.0, "max": 16.0},
                "default": {"min": 12.0, "max": 17.5}
            },
            "wbc": {
                "aliases": ["wbc", "white blood cell", "leukocyte", "leucocyte"],
                "unit": "cells/mcL",
                "default": {"min": 4500, "max": 11000}
            },
            "platelets": {
                "aliases": ["plt", "platelet", "thrombocyte"],
                "unit": "cells/mcL",
                "default": {"min": 150000, "max": 400000}
            },
            "rbc": {
                "aliases": ["rbc", "red blood cell", "erythrocyte"],
                "unit": "million cells/mcL",
                "male": {"min": 4.5, "max": 5.5},
                "female": {"min": 4.0, "max": 5.0},
                "default": {"min": 4.0, "max": 5.5}
            },
            "hematocrit": {
                "aliases": ["hct", "hematocrit", "pcv"],
                "unit": "%",
                "male": {"min": 38.8, "max": 50.0},
                "female": {"min": 34.9, "max": 44.5},
                "default": {"min": 34.9, "max": 50.0}
            },
            "creatinine": {
                "aliases": ["creatinine", "creat"],
                "unit": "mg/dL",
                "male": {"min": 0.7, "max": 1.3},
                "female": {"min": 0.6, "max": 1.1},
                "default": {"min": 0.6, "max": 1.3}
            },
            "blood_urea": {
                "aliases": ["bun", "blood urea", "urea"],
                "unit": "mg/dL",
                "default": {"min": 7, "max": 20}
            },
            "glucose_fasting": {
                "aliases": ["fbs", "fasting glucose", "fasting blood sugar", "glucose fasting"],
                "unit": "mg/dL",
                "default": {"min": 70, "max": 100}
            },
            "glucose_random": {
                "aliases": ["rbs", "random glucose", "blood sugar"],
                "unit": "mg/dL",
                "default": {"min": 70, "max": 140}
            },
            "hba1c": {
                "aliases": ["hba1c", "a1c", "glycated hemoglobin"],
                "unit": "%",
                "default": {"min": 4.0, "max": 5.7}
            },
            "cholesterol_total": {
                "aliases": ["total cholesterol", "cholesterol"],
                "unit": "mg/dL",
                "default": {"min": 0, "max": 200}
            },
            "ldl": {
                "aliases": ["ldl", "ldl cholesterol", "bad cholesterol"],
                "unit": "mg/dL",
                "default": {"min": 0, "max": 100}
            },
            "hdl": {
                "aliases": ["hdl", "hdl cholesterol", "good cholesterol"],
                "unit": "mg/dL",
                "default": {"min": 40, "max": 999}
            },
            "triglycerides": {
                "aliases": ["triglycerides", "tg"],
                "unit": "mg/dL",
                "default": {"min": 0, "max": 150}
            },
            "sgpt": {
                "aliases": ["sgpt", "alt", "alanine aminotransferase"],
                "unit": "U/L",
                "default": {"min": 7, "max": 56}
            },
            "sgot": {
                "aliases": ["sgot", "ast", "aspartate aminotransferase"],
                "unit": "U/L",
                "default": {"min": 10, "max": 40}
            },
            "bilirubin_total": {
                "aliases": ["bilirubin", "total bilirubin"],
                "unit": "mg/dL",
                "default": {"min": 0.1, "max": 1.2}
            },
            "crp": {
                "aliases": ["crp", "c-reactive protein"],
                "unit": "mg/L",
                "default": {"min": 0, "max": 10}
            },
            "esr": {
                "aliases": ["esr", "erythrocyte sedimentation rate"],
                "unit": "mm/hr",
                "male": {"min": 0, "max": 15},
                "female": {"min": 0, "max": 20},
                "default": {"min": 0, "max": 20}
            },
            "tsh": {
                "aliases": ["tsh", "thyroid stimulating hormone"],
                "unit": "mIU/L",
                "default": {"min": 0.4, "max": 4.0}
            },
            "t3": {
                "aliases": ["t3", "triiodothyronine"],
                "unit": "ng/dL",
                "default": {"min": 80, "max": 200}
            },
            "t4": {
                "aliases": ["t4", "thyroxine"],
                "unit": "mcg/dL",
                "default": {"min": 4.5, "max": 12.0}
            },
            "vitamin_d": {
                "aliases": ["vitamin d", "25-oh vitamin d", "vit d"],
                "unit": "ng/mL",
                "default": {"min": 30, "max": 100}
            },
            "vitamin_b12": {
                "aliases": ["vitamin b12", "b12", "cobalamin"],
                "unit": "pg/mL",
                "default": {"min": 200, "max": 900}
            },
            "sodium": {
                "aliases": ["sodium", "na"],
                "unit": "mEq/L",
                "default": {"min": 136, "max": 145}
            },
            "potassium": {
                "aliases": ["potassium", "k"],
                "unit": "mEq/L",
                "default": {"min": 3.5, "max": 5.0}
            },
            "calcium": {
                "aliases": ["calcium", "ca"],
                "unit": "mg/dL",
                "default": {"min": 8.5, "max": 10.5}
            }
        }
    
    def _build_lab_patterns(self) -> List[Dict]:
        """Build regex patterns for lab value extraction."""
        patterns = []
        
        for test_name, config in self.reference_ranges.items():
            for alias in config["aliases"]:
                # Pattern: test_name followed by value and optional unit
                # Example: "Hemoglobin: 14.5 g/dL" or "HB 14.5" or "WBC Count 14,500"
                # Updated regex to handle commas in numbers and optional intermediate text
                pattern = rf"(?i){re.escape(alias)}.*?([\d,]+\.?\d*)\s*({re.escape(config['unit'])}|[a-zA-Z/%]+)?"
                patterns.append({
                    "test": test_name,
                    "pattern": pattern,
                    "unit": config["unit"]
                })
        
        return patterns
    
    def parse_lab_values(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract lab values from OCR text.
        
        Args:
            text: Raw OCR text from medical report
            
        Returns:
            List of extracted lab values with metadata
        """
        results = []
        seen_tests = set()
        
        for pattern_info in self.lab_patterns:
            matches = re.finditer(pattern_info["pattern"], text, re.IGNORECASE)
            
            for match in matches:
                test_name = pattern_info["test"]
                
                # Skip duplicates
                if test_name in seen_tests:
                    continue
                
                try:
                    # Remove commas before converting to float
                    value_str = match.group(1).replace(",", "")
                    value = float(value_str)
                    unit = match.group(2) if match.group(2) else pattern_info["unit"]
                    
                    # Get reference range
                    ref_range = self.reference_ranges[test_name]["default"]
                    is_abnormal = value < ref_range["min"] or value > ref_range["max"]
                    
                    results.append({
                        "name": test_name.replace("_", " ").title(),
                        "value": value,
                        "unit": unit,
                        "reference_min": ref_range["min"],
                        "reference_max": ref_range["max"],
                        "reference_range": f"{ref_range['min']} - {ref_range['max']} {unit}",
                        "is_abnormal": is_abnormal
                    })
                    
                    seen_tests.add(test_name)
                except (ValueError, IndexError):
                    continue
        
        return results
    
    def identify_abnormalities(self, lab_values: List[Dict]) -> List[Dict[str, Any]]:
        """
        Identify abnormal findings from lab values.
        
        Args:
            lab_values: List of extracted lab values
            
        Returns:
            List of abnormal findings with severity and interpretation
        """
        abnormal_findings = []
        
        for lab in lab_values:
            if not lab.get("is_abnormal"):
                continue
            
            value = lab["value"]
            ref_min = lab["reference_min"]
            ref_max = lab["reference_max"]
            
            # Determine direction and severity
            if value < ref_min:
                direction = "low"
                deviation = (ref_min - value) / ref_min * 100
            else:
                direction = "high"
                deviation = (value - ref_max) / ref_max * 100
            
            # Classify severity
            if deviation > 50:
                severity = "critical"
            elif deviation > 25:
                severity = "high"
            else:
                severity = "moderate"
            
            # Get interpretation
            interpretation = self._get_interpretation(lab["name"], direction, severity)
            
            abnormal_findings.append({
                "test_name": lab["name"],
                "value": lab["value"],
                "unit": lab["unit"],
                "reference_range": lab["reference_range"],
                "direction": direction,
                "deviation_percent": round(deviation, 1),
                "severity": severity,
                "interpretation": interpretation
            })
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "moderate": 2}
        abnormal_findings.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return abnormal_findings
    
    def _get_interpretation(self, test_name: str, direction: str, severity: str) -> str:
        """Get clinical interpretation for abnormal value."""
        interpretations = {
            "Hemoglobin": {
                "low": "Low hemoglobin may indicate anemia. Common causes include iron deficiency, vitamin B12 deficiency, or chronic disease.",
                "high": "Elevated hemoglobin may indicate dehydration, lung disease, or other conditions."
            },
            "Wbc": {
                "low": "Low WBC (leukopenia) may indicate bone marrow issues, autoimmune conditions, or infections.",
                "high": "Elevated WBC (leukocytosis) may indicate infection, inflammation, or stress response."
            },
            "Platelets": {
                "low": "Low platelets (thrombocytopenia) may increase bleeding risk. Causes include viral infections, medications, or bone marrow disorders.",
                "high": "Elevated platelets (thrombocytosis) may increase clotting risk."
            },
            "Glucose Fasting": {
                "low": "Low fasting glucose (hypoglycemia) may indicate insulin issues or inadequate food intake.",
                "high": "Elevated fasting glucose may indicate prediabetes or diabetes."
            },
            "Creatinine": {
                "low": "Low creatinine is usually not concerning but may indicate low muscle mass.",
                "high": "Elevated creatinine may indicate reduced kidney function."
            },
            "Sgpt": {
                "high": "Elevated ALT/SGPT may indicate liver inflammation or damage."
            },
            "Sgot": {
                "high": "Elevated AST/SGOT may indicate liver, heart, or muscle damage."
            },
            "Tsh": {
                "low": "Low TSH may indicate hyperthyroidism (overactive thyroid).",
                "high": "Elevated TSH may indicate hypothyroidism (underactive thyroid)."
            },
            "Cholesterol Total": {
                "high": "Elevated total cholesterol increases cardiovascular disease risk."
            },
            "Ldl": {
                "high": "Elevated LDL ('bad' cholesterol) increases cardiovascular disease risk."
            },
            "Hdl": {
                "low": "Low HDL ('good' cholesterol) is associated with increased cardiovascular risk."
            }
        }
        
        default_interpretation = f"{direction.capitalize()} {test_name} detected. Please consult with your healthcare provider for proper evaluation."
        
        test_interp = interpretations.get(test_name, {})
        return test_interp.get(direction, default_interpretation)
    
    def check_critical_values(self, lab_values: List[Dict]) -> List[str]:
        """
        Check for critical values requiring immediate attention.
        
        Returns list of red flag warnings.
        """
        critical_thresholds = {
            "hemoglobin": {"critical_low": 7.0, "critical_high": 20.0},
            "glucose_fasting": {"critical_low": 40, "critical_high": 400},
            "glucose_random": {"critical_low": 40, "critical_high": 500},
            "potassium": {"critical_low": 2.5, "critical_high": 6.5},
            "sodium": {"critical_low": 120, "critical_high": 160},
            "platelets": {"critical_low": 50000, "critical_high": 1000000},
            "creatinine": {"critical_high": 10.0}
        }
        
        red_flags = []
        
        for lab in lab_values:
            test_key = lab["name"].lower().replace(" ", "_")
            thresholds = critical_thresholds.get(test_key)
            
            if not thresholds:
                continue
            
            value = lab["value"]
            
            if "critical_low" in thresholds and value < thresholds["critical_low"]:
                red_flags.append(
                    f"🚨 CRITICAL: {lab['name']} is critically low ({value} {lab['unit']}). "
                    f"Seek immediate medical attention."
                )
            elif "critical_high" in thresholds and value > thresholds["critical_high"]:
                red_flags.append(
                    f"🚨 CRITICAL: {lab['name']} is critically high ({value} {lab['unit']}). "
                    f"Seek immediate medical attention."
                )
        
        return red_flags


# Convenience function
def parse_lab_report(text: str) -> Dict[str, Any]:
    """
    Parse a lab report and return structured results.
    
    Args:
        text: Raw OCR text from medical report
        
    Returns:
        Dictionary with lab_values, abnormal_findings, and red_flags
    """
    parser = ReportParser()
    lab_values = parser.parse_lab_values(text)
    abnormal_findings = parser.identify_abnormalities(lab_values)
    red_flags = parser.check_critical_values(lab_values)
    
    return {
        "lab_values": lab_values,
        "abnormal_findings": abnormal_findings,
        "red_flags": red_flags
    }
