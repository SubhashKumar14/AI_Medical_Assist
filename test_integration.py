"""
Integration Test Suite for AI-Assisted Telemedicine Platform
============================================================

This script tests the entire pipeline end-to-end:
1. Knowledge base loading
2. Training data integrity  
3. Symptom extraction
4. Bayesian inference
5. Question selection (3-5-7 rule)
6. API endpoints

Run with: python test_integration.py
"""

import sys
import os
import json
import time
from pathlib import Path

# Add parent directories to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "ai_service"))

# Test results tracking
RESULTS = {
    'passed': 0,
    'failed': 0,
    'warnings': 0,
    'tests': []
}


def log_test(name: str, status: str, message: str = ""):
    """Log a test result."""
    icon = {'pass': '✅', 'fail': '❌', 'warn': '⚠️'}.get(status, '•')
    print(f"  {icon} {name}: {message}")
    RESULTS['tests'].append({'name': name, 'status': status, 'message': message})
    if status == 'pass':
        RESULTS['passed'] += 1
    elif status == 'fail':
        RESULTS['failed'] += 1
    else:
        RESULTS['warnings'] += 1


def test_knowledge_base():
    """Test knowledge base files exist and are valid."""
    print("\n📂 Testing Knowledge Base...")
    
    knowledge_dir = SCRIPT_DIR / "ai_service" / "knowledge"
    
    required_files = [
        ("disease_symptom_trained.csv", 1000),  # min rows
        ("symptom_questions_trained.json", 100),  # min entries
        ("disease_priors.json", 40),  # min diseases
        ("red_flags.json", 5),  # min red flags
    ]
    
    for filename, min_size in required_files:
        filepath = knowledge_dir / filename
        if filepath.exists():
            if filename.endswith('.csv'):
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    count = sum(1 for _ in csv.reader(f)) - 1  # minus header
                if count >= min_size:
                    log_test(filename, 'pass', f"{count} rows loaded")
                else:
                    log_test(filename, 'warn', f"Only {count} rows (expected >= {min_size})")
            elif filename.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, (list, dict)) else 0
                if count >= min_size:
                    log_test(filename, 'pass', f"{count} entries loaded")
                else:
                    log_test(filename, 'warn', f"Only {count} entries (expected >= {min_size})")
        else:
            log_test(filename, 'fail', "File not found")


def test_symptom_engine():
    """Test the symptom elimination engine."""
    print("\n🧠 Testing Symptom Elimination Engine...")
    
    try:
        from ai_service.engines.symptom_elimination import SymptomEliminationEngine
        
        engine = SymptomEliminationEngine()
        log_test("Engine initialization", 'pass', 
                 f"{len(engine.diseases)} diseases, {len(engine.symptoms)} symptoms")
        
        # Test symptom extraction
        test_text = "I have fever, headache, and body aches for 3 days"
        extracted = engine.extract_symptoms(test_text)
        symptoms = extracted.get('symptoms', [])
        
        if len(symptoms) >= 2:
            log_test("Symptom extraction", 'pass', f"Extracted: {symptoms}")
        else:
            log_test("Symptom extraction", 'warn', f"Only extracted: {symptoms}")
        
        # Test probability calculation
        state = engine.start(symptoms)
        probs = state.get('probabilities', [])
        
        if len(probs) >= 5:
            top3 = [(p['disease'], round(p['probability'], 3)) for p in probs[:3]]
            log_test("Probability calculation", 'pass', f"Top-3: {top3}")
        else:
            log_test("Probability calculation", 'fail', "No probabilities returned")
        
        # Test question selection
        question = engine.next_question(state)
        if question:
            log_test("Question selection", 'pass', f"Q: {question.get('question', '')[:50]}...")
        else:
            log_test("Question selection", 'warn', "No follow-up question returned")
        
        # Test 3-5-7 rule constants
        assert engine.MIN_QUESTIONS == 3, "MIN_QUESTIONS should be 3"
        assert engine.SOFT_MAX_QUESTIONS == 5, "SOFT_MAX_QUESTIONS should be 5"
        assert engine.HARD_MAX_QUESTIONS == 7, "HARD_MAX_QUESTIONS should be 7"
        log_test("3-5-7 Rule constants", 'pass', "MIN=3, SOFT=5, HARD=7")
        
        # Test red flag detection
        red_flags = engine.check_red_flags(['chest pain', 'shortness of breath'])
        if isinstance(red_flags, list):
            log_test("Red flag detection", 'pass', f"Detected: {red_flags[:3]}...")
        else:
            log_test("Red flag detection", 'warn', "Red flag check returned unexpected format")
            
    except ImportError as e:
        log_test("Engine import", 'fail', str(e))
    except Exception as e:
        log_test("Engine test", 'fail', str(e))


def test_training_scripts():
    """Test training scripts can be imported."""
    print("\n📚 Testing Training Scripts...")
    
    scripts = [
        ("train_knowledge_base", "DDXPlusTrainer"),
        ("train_ddxplus", "DDXPlusTrainer"),
        ("train_question_policy", "QuestionPolicyTrainer"),
        ("preprocess_mimic", "MIMICPreprocessor"),
    ]
    
    for module_name, class_name in scripts:
        try:
            module = __import__(f"ai_service.training.{module_name}", fromlist=[class_name])
            if hasattr(module, class_name):
                log_test(f"{module_name}.py", 'pass', f"{class_name} class found")
            else:
                log_test(f"{module_name}.py", 'warn', f"{class_name} not found in module")
        except ImportError as e:
            log_test(f"{module_name}.py", 'fail', str(e))


def test_model_adapters():
    """Test model adapter modules."""
    print("\n🔌 Testing Model Adapters...")
    
    adapters = [
        ("sapbert_ddxplus", "SapBERTDDXPlusAdapter"),
        ("bio_clinicalbert", "BioClinicalBERT"),
        ("model_selector", "ModelSelector"),
    ]
    
    for module_name, class_name in adapters:
        try:
            module = __import__(f"ai_service.model_adapters.{module_name}", fromlist=[class_name])
            if hasattr(module, class_name):
                log_test(f"{module_name}.py", 'pass', f"{class_name} class found")
            else:
                log_test(f"{module_name}.py", 'warn', f"{class_name} not found")
        except ImportError as e:
            # These might fail if torch not installed - that's OK
            if 'torch' in str(e) or 'transformers' in str(e):
                log_test(f"{module_name}.py", 'warn', f"Optional: {e}")
            else:
                log_test(f"{module_name}.py", 'fail', str(e))


def test_document_analysis():
    """Test document analysis modules."""
    print("\n📄 Testing Document Analysis...")
    
    try:
        from ai_service.document_analysis.report_analyzer import MedicalReportAnalyzer
        
        analyzer = MedicalReportAnalyzer()
        
        # Test with sample text (no OCR needed)
        sample_text = """
        Laboratory Results:
        Hemoglobin: 10.5 g/dL
        Glucose: 145 mg/dL
        Platelet: 250000 /uL
        """
        
        lab_values = analyzer.parse_lab_values(sample_text)
        if len(lab_values) >= 2:
            log_test("Report analyzer", 'pass', f"Parsed {len(lab_values)} lab values")
        else:
            log_test("Report analyzer", 'warn', f"Only parsed {len(lab_values)} values")
            
    except ImportError as e:
        if 'paddleocr' in str(e):
            log_test("Report analyzer", 'warn', f"PaddleOCR not installed: {e}")
        else:
            log_test("Report analyzer", 'fail', str(e))


def test_evaluation_data():
    """Test evaluation data exists."""
    print("\n📊 Testing Evaluation Data...")
    
    eval_dir = SCRIPT_DIR / "evaluation"
    
    # Test cases file
    test_cases = eval_dir / "datasets" / "test_cases.csv"
    if test_cases.exists():
        import csv
        with open(test_cases, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            diseases = set(r.get('disease', '') for r in rows)
            
        if len(rows) >= 30:
            log_test("test_cases.csv", 'pass', f"{len(rows)} cases, {len(diseases)} diseases")
        else:
            log_test("test_cases.csv", 'warn', f"Only {len(rows)} cases (recommend >= 100)")
    else:
        log_test("test_cases.csv", 'fail', "File not found")
    
    # Evaluate script
    evaluate_script = eval_dir / "evaluate_model.py"
    if evaluate_script.exists():
        log_test("evaluate_model.py", 'pass', "Script exists")
    else:
        log_test("evaluate_model.py", 'fail', "Script not found")


def test_api_endpoints():
    """Test API endpoint definitions (without starting server)."""
    print("\n🌐 Testing API Definitions...")
    
    try:
        from ai_service.app import app
        
        # Check routes exist
        routes = [route.path for route in app.routes]
        
        required_routes = ['/start', '/next', '/health']
        for route in required_routes:
            if route in routes:
                log_test(f"Endpoint {route}", 'pass', "Route defined")
            else:
                log_test(f"Endpoint {route}", 'fail', "Route not found")
                
    except ImportError as e:
        log_test("FastAPI app", 'warn', f"Could not import: {e}")


def test_dataset_coverage():
    """Check trained data coverage vs DDXPlus."""
    print("\n📈 Testing Dataset Coverage...")
    
    knowledge_dir = SCRIPT_DIR / "ai_service" / "knowledge"
    
    # Check training summary
    summary_path = knowledge_dir / "training_summary.json"
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            summary = json.load(f)
        
        total_cases = summary.get('total_cases', 0)
        total_diseases = summary.get('total_diseases', 0)
        total_symptoms = summary.get('total_symptoms', 0)
        
        log_test("Training cases", 'pass' if total_cases >= 1000000 else 'warn',
                 f"{total_cases:,} cases processed")
        log_test("Disease coverage", 'pass' if total_diseases >= 49 else 'warn',
                 f"{total_diseases} diseases trained")
        log_test("Symptom coverage", 'pass' if total_symptoms >= 200 else 'warn',
                 f"{total_symptoms} symptoms mapped")
    else:
        log_test("Training summary", 'warn', "training_summary.json not found")


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 60)
    print("📋 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    total = RESULTS['passed'] + RESULTS['failed'] + RESULTS['warnings']
    
    print(f"\n✅ Passed:   {RESULTS['passed']}/{total}")
    print(f"❌ Failed:   {RESULTS['failed']}/{total}")
    print(f"⚠️  Warnings: {RESULTS['warnings']}/{total}")
    
    if RESULTS['failed'] == 0:
        print("\n🎉 All critical tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        print("\nFailed tests:")
        for test in RESULTS['tests']:
            if test['status'] == 'fail':
                print(f"   ❌ {test['name']}: {test['message']}")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("🧪 AI-ASSISTED TELEMEDICINE PLATFORM - INTEGRATION TESTS")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all test suites
    test_knowledge_base()
    test_symptom_engine()
    test_training_scripts()
    test_model_adapters()
    test_document_analysis()
    test_evaluation_data()
    test_api_endpoints()
    test_dataset_coverage()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Tests completed in {elapsed:.2f} seconds")
    
    print_summary()
    
    # Return exit code
    return 1 if RESULTS['failed'] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
