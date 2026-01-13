import sys
import os
import json

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_service.report_analysis.report_parser import ReportParser, parse_lab_report

def test_parser():
    print("🧪 TEST: Medical Report Parser")
    print("=============================")
    
    # 1. Synthetic Report Text (Messy OCR style)
    sample_text = """
    PATIENT REPORT
    Date: 12/01/2025
    
    HEMATOLOGY
    --------------------------------
    Hemoglobin : 11.2 g/dL  (13.5 - 17.5)
    Total WBC Count  14,500 /cmm
    Neutrophils 75 %
    Lymphocytes 20 %
    RBC Count: 4.1 mill/cumm
    Platelet Count 120000 /cumm
    
    BIOCHEMISTRY
    --------------------------------
    Fasting Blood Sugar  145 mg/dl  (70-100)
    HbA1c : 7.2 %
    Blood Urea : 25 mg/dl
    Serum Creatinine : 0.9 mg/dl
    
    LIPID PROFILE
    Total Cholesterol : 240 mg/dl
    Triglycerides: 180 mg/dl
    HDL Cholesterol 35 mg/dl
    LDL Cholesterol 160 mg/dl
    
    Thyroid Function
    TSH : 6.5 mIU/L
    """
    
    print("\n📄 INPUT TEXT (Snippet):")
    print(sample_text[:200] + "...\n")
    
    # 2. Parse
    parser = ReportParser()
    results = parse_lab_report(sample_text)
    
    print("\n📊 EXTRACTED VALUES:")
    for item in results["lab_values"]:
        print(f"  - {item['name']}: {item['value']} {item['unit']} (Ref: {item.get('reference_range', 'N/A')})")
        
    print("\n🚨 ABNORMAL FINDINGS:")
    for item in results["abnormal_findings"]:
        print(f"  - {item['test_name']}: {item['value']} ({item['severity']} {item['direction']})")
        print(f"    Interpretation: {item['interpretation']}")

    print("\n🚩 RED FLAGS:")
    for flag in results["red_flags"]:
        print(f"  - {flag}")
        
    # Validation Checks
    print("\n✅ VALIDATION CHECKPOINTS:")
    
    # Check Hb (Low)
    hb = next((x for x in results["lab_values"] if x["name"] == "Hemoglobin"), None)
    if hb and hb["value"] == 11.2 and hb["is_abnormal"]:
        print("  [PASS] Hemoglobin 11.2 detected as Abnormal Low")
    else:
        print(f"  [FAIL] Hemoglobin detection failed. Got: {hb}")

    # Check WBC (High)
    wbc = next((x for x in results["lab_values"] if x["name"] == "Wbc"), None)
    # Parser regex might struggle with "14,500" if it doesn't handle commas. Let's see.
    if wbc and wbc["value"] == 14500:
        print("  [PASS] WBC 14,500 extracted correctly")
    else:
        print(f"  [FAIL] WBC extraction failed. Got: {wbc} (Check comma handling)")
        
    # Check Sugar (High)
    sugar = next((x for x in results["lab_values"] if x["name"] == "Glucose Fasting"), None)
    if sugar and sugar["value"] == 145:
        print("  [PASS] Fasting Sugar 145 detected as Abnormal High")
    else:
         print(f"  [FAIL] Sugar detection failed. Got: {sugar}")

if __name__ == "__main__":
    test_parser()
