"""
Model Evaluation Script
========================

Evaluates the symptom elimination engine on test cases.
Generates accuracy metrics (Top-1, Top-3, Top-5) and entropy reduction graphs.

This script produces publication-ready results for your project report.

Usage:
    python evaluate_model.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Try matplotlib (optional for graphs)
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlib not installed. Graphs will be skipped.")

from ai_service.engines.symptom_elimination import SymptomEliminationEngine

EVAL_DIR = Path(__file__).parent
DATASETS_DIR = EVAL_DIR / "datasets"
REPORTS_DIR = EVAL_DIR / "reports"


def calculate_top_k_accuracy(predictions: list, true_label: str, k: int = 3) -> int:
    """Check if true disease is in top K predictions."""
    if not predictions:
        return 0
    
    # Handle different prediction formats
    if isinstance(predictions[0], dict):
        top_k = [p.get('disease', p.get('name', '')) for p in predictions[:k]]
    else:
        top_k = predictions[:k]
    
    return 1 if true_label.lower() in [d.lower() for d in top_k] else 0


def calculate_entropy(probabilities: dict) -> float:
    """Calculate Shannon entropy of probability distribution."""
    if not probabilities:
        return 0
    
    probs = list(probabilities.values())
    return -sum(p * np.log2(p) for p in probs if p > 0)


def run_evaluation(test_file: str = None, max_cases: int = 100):
    """
    Run full evaluation on test cases.
    
    Args:
        test_file: Path to test cases CSV
        max_cases: Maximum cases to evaluate
    """
    # Find test file
    if test_file is None:
        test_file = DATASETS_DIR / "test_cases.csv"
        if not test_file.exists():
            test_file = DATASETS_DIR / "synthetic_cases.csv"
    else:
        test_file = Path(test_file)
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"📊 Loading test cases: {test_file}")
    test_df = pd.read_csv(test_file)
    
    if len(test_df) > max_cases:
        test_df = test_df.head(max_cases)
    
    print(f"   Cases to evaluate: {len(test_df)}")
    
    # Initialize engine
    print("🔧 Initializing symptom engine...")
    engine = SymptomEliminationEngine()
    
    # Results storage
    results = {
        "top1": [],
        "top3": [],
        "top5": [],
        "entropy_history": [],
        "question_counts": [],
        "confidence_scores": []
    }
    
    print("🧪 Running evaluation...")
    
    for idx, row in test_df.iterrows():
        # Get true disease
        true_disease = row.get('disease', row.get('expected_disease', ''))
        if not true_disease:
            continue
        
        # Get symptoms (try different column formats)
        symptoms = []
        if 'symptoms' in row:
            symptoms = str(row['symptoms']).split(',')
        else:
            # Try symptom_1, symptom_2, etc.
            for i in range(1, 10):
                col = f'symptom_{i}'
                if col in row and pd.notna(row[col]):
                    symptoms.append(str(row[col]))
        
        symptoms = [s.strip() for s in symptoms if s.strip()]
        
        if not symptoms:
            continue
        
        # Start triage
        state = engine.start(symptoms)
        
        entropy_trace = []
        turn = 0
        max_turns = 7
        
        # Simulate interaction
        while state.get('status') == 'IN_PROGRESS' and turn < max_turns:
            # Calculate current entropy
            posterior = state.get('posterior', {})
            entropy = calculate_entropy(posterior)
            entropy_trace.append(entropy)
            
            # Get next question
            next_q = state.get('next_question')
            if not next_q:
                break
            
            symptom = next_q.get('symptom', '')
            
            # Oracle answering: check if symptom is related to true disease
            # In real evaluation, you'd have ground truth answers
            answer = "yes" if symptom in [s.lower() for s in symptoms] else "no"
            
            state = engine.update(state, symptom, answer)
            turn += 1
        
        # Get final predictions
        probabilities = state.get('posterior', {})
        sorted_preds = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        predictions = [{'disease': d, 'probability': p} for d, p in sorted_preds]
        
        # Calculate metrics
        results['top1'].append(calculate_top_k_accuracy(predictions, true_disease, 1))
        results['top3'].append(calculate_top_k_accuracy(predictions, true_disease, 3))
        results['top5'].append(calculate_top_k_accuracy(predictions, true_disease, 5))
        results['entropy_history'].append(entropy_trace)
        results['question_counts'].append(turn)
        
        if predictions:
            results['confidence_scores'].append(predictions[0]['probability'])
    
    # Calculate averages
    avg_top1 = np.mean(results['top1']) * 100 if results['top1'] else 0
    avg_top3 = np.mean(results['top3']) * 100 if results['top3'] else 0
    avg_top5 = np.mean(results['top5']) * 100 if results['top5'] else 0
    avg_questions = np.mean(results['question_counts']) if results['question_counts'] else 0
    avg_confidence = np.mean(results['confidence_scores']) * 100 if results['confidence_scores'] else 0
    
    # Print results
    print("\n" + "=" * 50)
    print("📈 EVALUATION RESULTS")
    print("=" * 50)
    print(f"Test Cases: {len(results['top1'])}")
    print(f"Top-1 Accuracy: {avg_top1:.1f}%")
    print(f"Top-3 Accuracy: {avg_top3:.1f}%")
    print(f"Top-5 Accuracy: {avg_top5:.1f}%")
    print(f"Avg Questions Asked: {avg_questions:.1f}")
    print(f"Avg Confidence: {avg_confidence:.1f}%")
    print("=" * 50)
    
    # Save results
    REPORTS_DIR.mkdir(exist_ok=True)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_file": str(test_file),
        "total_cases": len(results['top1']),
        "metrics": {
            "top1_accuracy": round(avg_top1, 2),
            "top3_accuracy": round(avg_top3, 2),
            "top5_accuracy": round(avg_top5, 2),
            "avg_questions": round(avg_questions, 2),
            "avg_confidence": round(avg_confidence, 2)
        }
    }
    
    report_path = REPORTS_DIR / f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Report saved: {report_path}")
    
    # Generate graphs
    if HAS_MATPLOTLIB and results['entropy_history']:
        generate_entropy_graph(results['entropy_history'])


def generate_entropy_graph(entropy_histories: list):
    """Generate entropy reduction graph."""
    if not entropy_histories:
        return
    
    # Calculate average entropy per turn
    max_len = max(len(h) for h in entropy_histories)
    avg_entropy = []
    
    for i in range(max_len):
        step_vals = [h[i] for h in entropy_histories if len(h) > i]
        if step_vals:
            avg_entropy.append(np.mean(step_vals))
    
    if not avg_entropy:
        return
    
    # Create figure
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(avg_entropy)), avg_entropy, 'ro-', linewidth=2, markersize=8)
    plt.fill_between(range(len(avg_entropy)), avg_entropy, alpha=0.3, color='red')
    
    plt.title("Symptom Entropy Reduction Over Questions", fontsize=14, fontweight='bold')
    plt.xlabel("Number of Questions Asked", fontsize=12)
    plt.ylabel("Entropy (Uncertainty)", fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add annotations
    if len(avg_entropy) > 1:
        reduction = (avg_entropy[0] - avg_entropy[-1]) / avg_entropy[0] * 100
        plt.annotate(f'Reduction: {reduction:.1f}%', 
                    xy=(len(avg_entropy)-1, avg_entropy[-1]),
                    xytext=(len(avg_entropy)-2, avg_entropy[0]),
                    fontsize=10,
                    arrowprops=dict(arrowstyle='->', color='gray'))
    
    # Save
    graph_path = REPORTS_DIR / "entropy_reduction_graph.png"
    plt.tight_layout()
    plt.savefig(graph_path, dpi=150)
    plt.close()
    
    print(f"📊 Graph saved: {graph_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate symptom elimination engine")
    parser.add_argument("--test-file", default=None, help="Path to test cases CSV")
    parser.add_argument("--max-cases", type=int, default=100, help="Max cases to evaluate")
    
    args = parser.parse_args()
    run_evaluation(args.test_file, args.max_cases)
