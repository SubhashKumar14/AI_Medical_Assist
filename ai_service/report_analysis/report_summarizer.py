"""
Report Summarizer

Generate AI summaries of medical reports using model selector.
Falls back gracefully between Gemini, OpenRouter, and local templates.
"""

from typing import Dict, List, Any, Optional


class ReportSummarizer:
    """
    Generate summaries of medical reports.
    
    Uses AI APIs when available, falls back to template-based summaries.
    """
    
    def __init__(self, model_selector=None):
        """Initialize with optional model selector."""
        self.model_selector = model_selector
    
    async def summarize(
        self,
        extracted_text: str,
        lab_values: List[Dict],
        abnormal_findings: List[Dict]
    ) -> str:
        """
        Generate a summary of the medical report.
        
        Args:
            extracted_text: Raw OCR text
            lab_values: Parsed lab values
            abnormal_findings: Identified abnormalities
            
        Returns:
            Summary string
        """
        # Try AI-powered summary first
        if self.model_selector:
            try:
                return await self.model_selector.summarize_report(
                    extracted_text,
                    lab_values,
                    abnormal_findings
                )
            except Exception as e:
                print(f"AI summary failed, using template: {e}")
        
        # Fallback to template-based summary
        return self._generate_template_summary(lab_values, abnormal_findings)
    
    def _generate_template_summary(
        self,
        lab_values: List[Dict],
        abnormal_findings: List[Dict]
    ) -> str:
        """Generate template-based summary when AI is unavailable."""
        summary_parts = []
        
        # Header
        summary_parts.append("**Medical Report Summary**\n")
        summary_parts.append("_This summary is automatically generated. Please consult a healthcare professional for interpretation._\n")
        
        # Overview
        total_tests = len(lab_values)
        abnormal_count = len(abnormal_findings)
        normal_count = total_tests - abnormal_count
        
        summary_parts.append(f"\n**Overview:**")
        summary_parts.append(f"- Total tests analyzed: {total_tests}")
        summary_parts.append(f"- Normal values: {normal_count}")
        summary_parts.append(f"- Abnormal values: {abnormal_count}")
        
        # Abnormal findings
        if abnormal_findings:
            summary_parts.append(f"\n**Findings Requiring Attention:**\n")
            
            for finding in abnormal_findings:
                severity_emoji = {
                    "critical": "🚨",
                    "high": "⚠️",
                    "moderate": "📋"
                }.get(finding["severity"], "📋")
                
                summary_parts.append(
                    f"{severity_emoji} **{finding['test_name']}**: {finding['value']} {finding['unit']} "
                    f"({finding['direction']}, {finding['deviation_percent']}% from normal range)"
                )
                summary_parts.append(f"   - {finding['interpretation']}\n")
        else:
            summary_parts.append("\n**All analyzed values are within normal ranges.**")
        
        # Normal values summary
        normal_values = [lab for lab in lab_values if not lab.get("is_abnormal")]
        if normal_values:
            summary_parts.append("\n**Normal Values:**")
            for lab in normal_values[:5]:  # Show first 5
                summary_parts.append(f"- {lab['name']}: {lab['value']} {lab['unit']} ✓")
            if len(normal_values) > 5:
                summary_parts.append(f"- ... and {len(normal_values) - 5} more normal values")
        
        # Disclaimer
        summary_parts.append("\n\n---")
        summary_parts.append("_⚠️ This is an automated analysis and should not replace professional medical advice. "
                           "Please share these results with your healthcare provider for proper interpretation and guidance._")
        
        return "\n".join(summary_parts)
