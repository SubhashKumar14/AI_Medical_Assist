"""
Accuracy Evaluation Script

Evaluate Top-1 and Top-3 accuracy of the symptom elimination engine
using synthetic test cases.

Usage:
    python calculate_accuracy.py --test-file datasets/test_cases.csv
    python calculate_accuracy.py --api-url http://localhost:8000
"""

import os
import sys
import csv
import json
import argparse
import asyncio
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from ai_service.engines.symptom_elimination import SymptomEliminationEngine
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False


class AccuracyEvaluator:
    """
    Evaluate accuracy of symptom elimination engine.
    
    Metrics:
    - Top-1 Accuracy: Correct disease is the top prediction
    - Top-3 Accuracy: Correct disease is in top 3 predictions
    - Top-5 Accuracy: Correct disease is in top 5 predictions
    - Mean Reciprocal Rank (MRR)
    """
    
    def __init__(self, api_url: str = None):
        """
        Initialize evaluator.
        
        Args:
            api_url: Optional API URL for testing via HTTP
        """
        self.api_url = api_url
        self.engine = None
        
        if not api_url and ENGINE_AVAILABLE:
            self.engine = SymptomEliminationEngine()
    
    async def evaluate_case(
        self,
        symptoms: List[str],
        expected_disease: str
    ) -> Dict[str, Any]:
        """
        Evaluate a single test case.
        
        Args:
            symptoms: List of symptom strings
            expected_disease: Ground truth disease
            
        Returns:
            Evaluation result with metrics
        """
        if self.api_url:
            predictions = await self._call_api(symptoms)
        else:
            predictions = self._call_engine(symptoms)
        
        # Find rank of expected disease
        rank = None
        for i, pred in enumerate(predictions):
            if pred["disease"].lower() == expected_disease.lower():
                rank = i + 1  # 1-indexed
                break
        
        return {
            "symptoms": symptoms,
            "expected": expected_disease,
            "predictions": [p["disease"] for p in predictions[:5]],
            "top_prediction": predictions[0]["disease"] if predictions else None,
            "top_probability": predictions[0]["probability"] if predictions else 0,
            "rank": rank,
            "top1_correct": rank == 1 if rank else False,
            "top3_correct": rank is not None and rank <= 3,
            "top5_correct": rank is not None and rank <= 5,
            "reciprocal_rank": 1.0 / rank if rank else 0
        }
    
    def _call_engine(self, symptoms: List[str]) -> List[Dict]:
        """Call local engine directly."""
        if not self.engine:
            return []
        
        state = self.engine.start(symptoms)
        return state["probabilities"]
    
    async def _call_api(self, symptoms: List[str]) -> List[Dict]:
        """Call AI service via HTTP."""
        if not AIOHTTP_AVAILABLE:
            print("aiohttp not available for API testing")
            return []
        
        symptom_text = ", ".join(symptoms)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/start",
                json={"text": symptom_text}
            ) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                return data.get("probabilities", [])
    
    async def evaluate_dataset(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate full dataset.
        
        Args:
            test_cases: List of {symptoms: [...], disease: "..."}
            
        Returns:
            Aggregate metrics
        """
        results = []
        
        for i, case in enumerate(test_cases):
            symptoms = case.get("symptoms", [])
            expected = case.get("disease", "")
            
            if isinstance(symptoms, str):
                symptoms = [s.strip() for s in symptoms.split(",")]
            
            result = await self.evaluate_case(symptoms, expected)
            results.append(result)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Evaluated {i + 1}/{len(test_cases)} cases...")
        
        # Calculate aggregate metrics
        n = len(results)
        
        top1_accuracy = sum(r["top1_correct"] for r in results) / n if n > 0 else 0
        top3_accuracy = sum(r["top3_correct"] for r in results) / n if n > 0 else 0
        top5_accuracy = sum(r["top5_correct"] for r in results) / n if n > 0 else 0
        mrr = sum(r["reciprocal_rank"] for r in results) / n if n > 0 else 0
        
        return {
            "total_cases": n,
            "top1_accuracy": round(top1_accuracy * 100, 2),
            "top3_accuracy": round(top3_accuracy * 100, 2),
            "top5_accuracy": round(top5_accuracy * 100, 2),
            "mean_reciprocal_rank": round(mrr, 4),
            "detailed_results": results
        }
    
    def generate_report(self, metrics: Dict[str, Any]) -> str:
        """Generate human-readable evaluation report."""
        report_lines = [
            "=" * 60,
            "AI TELEMEDICINE CDSS - ACCURACY EVALUATION REPORT",
            "=" * 60,
            "",
            f"Total Test Cases: {metrics['total_cases']}",
            "",
            "ACCURACY METRICS:",
            f"  • Top-1 Accuracy: {metrics['top1_accuracy']}%",
            f"  • Top-3 Accuracy: {metrics['top3_accuracy']}%",
            f"  • Top-5 Accuracy: {metrics['top5_accuracy']}%",
            f"  • Mean Reciprocal Rank (MRR): {metrics['mean_reciprocal_rank']}",
            "",
            "=" * 60,
        ]
        
        # Add per-disease breakdown
        disease_results = {}
        for result in metrics.get("detailed_results", []):
            expected = result["expected"]
            if expected not in disease_results:
                disease_results[expected] = {"correct": 0, "total": 0}
            disease_results[expected]["total"] += 1
            if result["top1_correct"]:
                disease_results[expected]["correct"] += 1
        
        report_lines.append("")
        report_lines.append("PER-DISEASE TOP-1 ACCURACY:")
        for disease, counts in sorted(disease_results.items()):
            acc = counts["correct"] / counts["total"] * 100 if counts["total"] > 0 else 0
            report_lines.append(f"  • {disease}: {acc:.1f}% ({counts['correct']}/{counts['total']})")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        # Sample failures
        failures = [r for r in metrics.get("detailed_results", []) if not r["top1_correct"]]
        if failures:
            report_lines.append("")
            report_lines.append("SAMPLE INCORRECT PREDICTIONS (up to 5):")
            for failure in failures[:5]:
                report_lines.append(f"  Symptoms: {', '.join(failure['symptoms'])}")
                report_lines.append(f"  Expected: {failure['expected']}")
                report_lines.append(f"  Predicted: {failure['top_prediction']} (rank: {failure['rank']})")
                report_lines.append("")
        
        return "\n".join(report_lines)


def load_test_cases(file_path: str) -> List[Dict]:
    """Load test cases from CSV file."""
    test_cases = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symptoms = row.get("symptoms", "").split(",")
            symptoms = [s.strip() for s in symptoms if s.strip()]
            disease = row.get("disease", "").strip()
            
            if symptoms and disease:
                test_cases.append({
                    "symptoms": symptoms,
                    "disease": disease
                })
    
    return test_cases


def create_synthetic_test_cases() -> List[Dict]:
    """Create synthetic test cases for evaluation."""
    return [
        # Dengue cases
        {"symptoms": ["fever", "headache", "body ache", "joint pain"], "disease": "Dengue"},
        {"symptoms": ["fever", "rash", "fatigue", "nausea"], "disease": "Dengue"},
        {"symptoms": ["high fever", "severe headache", "joint pain"], "disease": "Dengue"},
        
        # Malaria cases
        {"symptoms": ["fever", "chills", "sweating"], "disease": "Malaria"},
        {"symptoms": ["fever", "chills", "headache", "fatigue"], "disease": "Malaria"},
        {"symptoms": ["cyclic fever", "chills", "nausea"], "disease": "Malaria"},
        
        # Common Cold cases
        {"symptoms": ["runny nose", "sneezing", "sore throat"], "disease": "Common Cold"},
        {"symptoms": ["runny nose", "cough", "mild fever"], "disease": "Common Cold"},
        {"symptoms": ["sneezing", "sore throat", "fatigue"], "disease": "Common Cold"},
        
        # Influenza cases
        {"symptoms": ["fever", "body ache", "fatigue", "cough"], "disease": "Influenza"},
        {"symptoms": ["fever", "headache", "chills", "fatigue"], "disease": "Influenza"},
        {"symptoms": ["body ache", "cough", "fever", "weakness"], "disease": "Influenza"},
        
        # COVID-19 cases
        {"symptoms": ["fever", "cough", "loss of taste", "loss of smell"], "disease": "COVID-19"},
        {"symptoms": ["cough", "fatigue", "loss of smell"], "disease": "COVID-19"},
        {"symptoms": ["fever", "shortness of breath", "fatigue"], "disease": "COVID-19"},
        
        # Gastroenteritis cases
        {"symptoms": ["diarrhea", "vomiting", "abdominal pain"], "disease": "Gastroenteritis"},
        {"symptoms": ["nausea", "vomiting", "diarrhea", "fever"], "disease": "Gastroenteritis"},
        {"symptoms": ["abdominal pain", "diarrhea", "nausea"], "disease": "Gastroenteritis"},
        
        # Typhoid cases
        {"symptoms": ["fever", "abdominal pain", "headache", "weakness"], "disease": "Typhoid"},
        {"symptoms": ["high fever", "constipation", "fatigue"], "disease": "Typhoid"},
        
        # Migraine cases
        {"symptoms": ["severe headache", "nausea", "light sensitivity"], "disease": "Migraine"},
        {"symptoms": ["throbbing headache", "nausea", "vision changes"], "disease": "Migraine"},
    ]


async def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate AI Telemedicine CDSS accuracy")
    parser.add_argument("--test-file", type=str, help="Path to CSV test file")
    parser.add_argument("--api-url", type=str, help="AI service API URL")
    parser.add_argument("--output", type=str, default="evaluation_report.txt", help="Output report file")
    parser.add_argument("--use-synthetic", action="store_true", help="Use synthetic test cases")
    
    args = parser.parse_args()
    
    # Load test cases
    if args.test_file and os.path.exists(args.test_file):
        print(f"Loading test cases from {args.test_file}...")
        test_cases = load_test_cases(args.test_file)
    else:
        print("Using synthetic test cases...")
        test_cases = create_synthetic_test_cases()
    
    print(f"Loaded {len(test_cases)} test cases")
    
    # Initialize evaluator
    evaluator = AccuracyEvaluator(api_url=args.api_url)
    
    # Run evaluation
    print("Running evaluation...")
    metrics = await evaluator.evaluate_dataset(test_cases)
    
    # Generate report
    report = evaluator.generate_report(metrics)
    print("\n" + report)
    
    # Save report
    output_path = Path(__file__).parent / args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to {output_path}")
    
    # Save detailed JSON results
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print(f"Detailed results saved to {json_path}")
    
    return metrics


if __name__ == "__main__":
    asyncio.run(main())
