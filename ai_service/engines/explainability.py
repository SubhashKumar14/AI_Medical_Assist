"""
Explainability Engine

Explain AI predictions via symptom contribution scoring.
FREE implementation - no SHAP, no LIME, no paid libraries.

Methods:
- Symptom contribution scores (delta in probability)
- Probability change per question
- Rule-based trace logs
"""

from typing import Dict, List, Any, Optional
import math


class ExplainabilityEngine:
    """
    Explainability engine for symptom-disease predictions.
    
    Provides transparent explanations without paid XAI tools.
    """
    
    def __init__(self, likelihood_matrix: Dict[str, Dict[str, float]] = None):
        """
        Initialize explainability engine.
        
        Args:
            likelihood_matrix: P(S|D) matrix from elimination engine
        """
        self.likelihood_matrix = likelihood_matrix or {}
    
    def add_contributions(
        self,
        probabilities: List[Dict[str, Any]],
        observed_symptoms: List[str],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Add symptom contributions to probability results.
        
        Args:
            probabilities: List of {disease, probability} dicts
            observed_symptoms: Symptoms extracted from user
            top_n: Number of top contributing symptoms to include
            
        Returns:
            Probabilities with contributing_symptoms added
        """
        enhanced = []
        
        for prob_entry in probabilities:
            disease = prob_entry["disease"]
            probability = prob_entry["probability"]
            
            # Calculate contribution of each symptom
            contributions = self.symptom_contributions(
                disease,
                observed_symptoms,
                probability
            )
            
            # Get top contributing symptoms
            sorted_contributions = sorted(
                contributions.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            top_symptoms = [s[0] for s in sorted_contributions[:top_n]]
            
            enhanced.append({
                **prob_entry,
                "contributing_symptoms": top_symptoms,
                "contribution_scores": dict(sorted_contributions[:top_n])
            })
        
        return enhanced
    
    def symptom_contributions(
        self,
        disease: str,
        symptoms: List[str],
        current_probability: float
    ) -> Dict[str, float]:
        """
        Calculate how much each symptom contributes to disease probability.
        
        Uses the log-odds ratio: log(P(S|D) / P(S|not D))
        
        Args:
            disease: Target disease
            symptoms: Observed symptoms
            current_probability: Current disease probability
            
        Returns:
            Dict mapping symptom to contribution score
        """
        contributions = {}
        
        disease_likelihoods = self.likelihood_matrix.get(disease, {})
        
        for symptom in symptoms:
            # P(S|D) - probability of symptom given disease
            p_s_given_d = disease_likelihoods.get(symptom, 0.1)
            
            # P(S|not D) - assume base rate for population
            p_s_given_not_d = 0.2  # Default base rate
            
            # Contribution is the likelihood ratio
            if p_s_given_not_d > 0:
                contribution = p_s_given_d / p_s_given_not_d
            else:
                contribution = p_s_given_d * 10
            
            contributions[symptom] = round(contribution, 2)
        
        return contributions
    
    def generate_explanation(
        self,
        disease: str,
        probability: float,
        symptoms: List[str],
        contributions: Dict[str, float]
    ) -> str:
        """
        Generate human-readable explanation for a prediction.
        
        Args:
            disease: Predicted disease
            probability: Probability score
            symptoms: Observed symptoms
            contributions: Symptom contribution scores
            
        Returns:
            Explanation string
        """
        # Sort symptoms by contribution
        sorted_symptoms = sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        explanation_parts = []
        
        # Confidence level
        if probability > 0.7:
            confidence = "high"
        elif probability > 0.4:
            confidence = "moderate"
        else:
            confidence = "low"
        
        explanation_parts.append(
            f"**{disease}** ({probability*100:.1f}% probability, {confidence} confidence)"
        )
        
        # Key symptoms
        if sorted_symptoms:
            top_3 = sorted_symptoms[:3]
            symptom_explanations = []
            
            for symptom, score in top_3:
                if score > 2.0:
                    strength = "strongly suggests"
                elif score > 1.0:
                    strength = "suggests"
                else:
                    strength = "may indicate"
                
                symptom_explanations.append(f"'{symptom}' {strength} this condition")
            
            explanation_parts.append("Key factors: " + "; ".join(symptom_explanations))
        
        # Missing symptoms (if we have likelihood data)
        if disease in self.likelihood_matrix:
            disease_symptoms = self.likelihood_matrix[disease]
            high_weight_symptoms = [
                s for s, w in disease_symptoms.items() 
                if w > 0.7 and s not in symptoms
            ]
            
            if high_weight_symptoms:
                explanation_parts.append(
                    f"Note: Common symptoms not reported: {', '.join(high_weight_symptoms[:3])}"
                )
        
        return "\n".join(explanation_parts)
    
    def probability_change_trace(
        self,
        history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate trace of probability changes across questions.
        
        Args:
            history: List of session state snapshots
            
        Returns:
            List of change records
        """
        if len(history) < 2:
            return []
        
        trace = []
        
        for i in range(1, len(history)):
            prev_state = history[i - 1]
            curr_state = history[i]
            
            prev_probs = {p["disease"]: p["probability"] for p in prev_state.get("probabilities", [])}
            curr_probs = {p["disease"]: p["probability"] for p in curr_state.get("probabilities", [])}
            
            changes = []
            for disease in curr_probs:
                prev_p = prev_probs.get(disease, 0)
                curr_p = curr_probs.get(disease, 0)
                change = curr_p - prev_p
                
                if abs(change) > 0.01:  # Significant change
                    changes.append({
                        "disease": disease,
                        "previous": round(prev_p, 3),
                        "current": round(curr_p, 3),
                        "change": round(change, 3),
                        "direction": "increased" if change > 0 else "decreased"
                    })
            
            # Sort by absolute change
            changes.sort(key=lambda x: abs(x["change"]), reverse=True)
            
            trace.append({
                "step": i,
                "question_answered": curr_state.get("last_question"),
                "answer": curr_state.get("last_answer"),
                "top_changes": changes[:5]
            })
        
        return trace
    
    def rule_trace(
        self,
        disease: str,
        symptoms: List[str],
        negative_symptoms: List[str] = None
    ) -> List[str]:
        """
        Generate rule-based trace explaining elimination logic.
        
        Args:
            disease: Target disease
            symptoms: Observed symptoms
            negative_symptoms: Symptoms user said "no" to
            
        Returns:
            List of trace statements
        """
        negative_symptoms = negative_symptoms or []
        trace = []
        
        disease_likelihoods = self.likelihood_matrix.get(disease, {})
        
        # Positive evidence
        for symptom in symptoms:
            weight = disease_likelihoods.get(symptom, 0)
            if weight > 0.7:
                trace.append(f"✅ '{symptom}' is highly associated with {disease} (weight: {weight:.2f})")
            elif weight > 0.4:
                trace.append(f"✅ '{symptom}' is moderately associated with {disease} (weight: {weight:.2f})")
        
        # Negative evidence
        for symptom in negative_symptoms:
            weight = disease_likelihoods.get(symptom, 0)
            if weight > 0.7:
                trace.append(f"❌ Absence of '{symptom}' reduces likelihood of {disease} (expected weight: {weight:.2f})")
        
        # Missing key symptoms
        for symptom, weight in disease_likelihoods.items():
            if weight > 0.8 and symptom not in symptoms and symptom not in negative_symptoms:
                trace.append(f"❓ Key symptom '{symptom}' not yet assessed for {disease}")
        
        return trace
    
    def generate_full_report(
        self,
        probabilities: List[Dict[str, Any]],
        symptoms: List[str],
        negative_symptoms: List[str] = None,
        top_diseases: int = 3
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explainability report.
        
        Args:
            probabilities: Disease probabilities
            symptoms: Observed symptoms
            negative_symptoms: Denied symptoms
            top_diseases: Number of top diseases to explain
            
        Returns:
            Full explanation report
        """
        negative_symptoms = negative_symptoms or []
        
        # Add contributions
        enhanced_probs = self.add_contributions(probabilities, symptoms)
        
        # Generate explanations for top diseases
        explanations = []
        for prob in enhanced_probs[:top_diseases]:
            disease = prob["disease"]
            
            explanation = {
                "disease": disease,
                "probability": prob["probability"],
                "confidence_level": self._confidence_level(prob["probability"]),
                "contributing_symptoms": prob.get("contributing_symptoms", []),
                "contribution_scores": prob.get("contribution_scores", {}),
                "narrative": self.generate_explanation(
                    disease,
                    prob["probability"],
                    symptoms,
                    prob.get("contribution_scores", {})
                ),
                "rule_trace": self.rule_trace(disease, symptoms, negative_symptoms)
            }
            explanations.append(explanation)
        
        return {
            "observed_symptoms": symptoms,
            "denied_symptoms": negative_symptoms,
            "top_predictions": explanations,
            "disclaimer": "This analysis is for informational purposes only and does not constitute medical diagnosis."
        }
    
    def _confidence_level(self, probability: float) -> str:
        """Convert probability to confidence level."""
        if probability > 0.7:
            return "high"
        elif probability > 0.4:
            return "moderate"
        elif probability > 0.2:
            return "low"
        else:
            return "very low"
    
    def set_likelihood_matrix(self, matrix: Dict[str, Dict[str, float]]):
        """Update the likelihood matrix."""
        self.likelihood_matrix = matrix
