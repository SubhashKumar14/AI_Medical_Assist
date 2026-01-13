"""
Model Selector - AI Model/API Routing

Decision rules for choosing between:
- Local models (Bio_ClinicalBERT, etc.)
- Gemini Pro API
- OpenRouter API (multi-model fallback)

Handles rate limiting, fallbacks, and cost optimization.
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

# Environment variables for API configuration
USE_LOCAL = os.getenv("USE_LOCAL_AI", "true").lower() == "true"
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true"
USE_OPENROUTER = os.getenv("USE_OPENROUTER", "false").lower() == "true"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


class BaseModelAdapter(ABC):
    """Abstract base class for model adapters."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from model."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is available."""
        pass


class LocalModelAdapter(BaseModelAdapter):
    """Adapter for local models (Bio_ClinicalBERT, etc.)"""
    
    def __init__(self):
        self._model = None
        self._tokenizer = None
    
    def is_available(self) -> bool:
        """Check if local model can be loaded."""
        try:
            # Try importing transformers
            import transformers
            return True
        except ImportError:
            return False
    
    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from transformers import AutoTokenizer, AutoModel
                model_name = "distilbert-base-uncased"  # Lightweight fallback
                self._tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._model = AutoModel.from_pretrained(model_name)
            except Exception as e:
                print(f"Failed to load local model: {e}")
                self._model = "unavailable"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate using local model (limited capability)."""
        self._load_model()
        
        if self._model == "unavailable":
            return "[Local model unavailable]"
        
        # For complex generation, local DistilBERT isn't ideal
        # Return a template response
        return self._template_response(prompt)
    
    def _template_response(self, prompt: str) -> str:
        """Template response when local generation isn't available."""
        if "summarize" in prompt.lower():
            return "Please review the extracted values above. Consult your healthcare provider for interpretation."
        return "Analysis complete. Please review with a healthcare professional."


class GeminiModelAdapter(BaseModelAdapter):
    """Adapter for Google Gemini Pro API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self._client = None
        self._rate_limit_remaining = 100
        self._last_request_time = 0
    
    def is_available(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(self.api_key)
    
    def _get_client(self):
        """Get or create Gemini client."""
        if self._client is None and self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel('gemini-pro')
            except ImportError:
                print("google-generativeai not installed")
                self._client = "unavailable"
            except Exception as e:
                print(f"Failed to initialize Gemini: {e}")
                self._client = "unavailable"
        return self._client
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Gemini Pro."""
        client = self._get_client()
        
        if client == "unavailable" or client is None:
            raise Exception("Gemini client unavailable")
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            # Prepend Mandatory System Prompt
            from safety_config import SYSTEM_PROMPT
            full_prompt = f"{SYSTEM_PROMPT}\n\nTask: {prompt}"

            # Generate response
            response = client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.3),
                    "max_output_tokens": kwargs.get("max_tokens", 1024),
                }
            )
            
            return response.text
            
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                raise RateLimitError(f"Gemini rate limit: {e}")
            raise
    
    async def _rate_limit(self):
        """Simple rate limiting."""
        import time
        current_time = time.time()
        
        # Minimum 100ms between requests
        time_since_last = current_time - self._last_request_time
        if time_since_last < 0.1:
            await asyncio.sleep(0.1 - time_since_last)
        
        self._last_request_time = time.time()


class OpenRouterModelAdapter(BaseModelAdapter):
    """Adapter for OpenRouter API (multi-model access)."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = "anthropic/claude-3-haiku"  # Cost-effective default
    
    def is_available(self) -> bool:
        """Check if OpenRouter API is configured."""
        return bool(self.api_key)
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenRouter."""
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")
        
        try:
            import aiohttp
            
            model = kwargs.get("model", self.default_model)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telemedicine-cdss.local",
            }
            
            from safety_config import SYSTEM_PROMPT
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 1024),
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("OpenRouter rate limit exceeded")
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    return data["choices"][0]["message"]["content"]
                    
        except Exception as e:
            if "429" in str(e):
                raise RateLimitError(f"OpenRouter rate limit: {e}")
            raise


class RateLimitError(Exception):
    """Exception for rate limit errors."""
    pass


class ModelSelector:
    """
    Main model selector that routes requests to appropriate adapter.
    
    Decision rules:
    1. Use local models for simple tasks (symptom extraction)
    2. Use Gemini Pro for summaries and reasoning (when available)
    3. Fall back to OpenRouter on Gemini rate limit
    4. Use templates as final fallback
    """
    
    def __init__(self):
        self.local_adapter = LocalModelAdapter()
        self.gemini_adapter = GeminiModelAdapter()
        self.openrouter_adapter = OpenRouterModelAdapter()
        
        # Configure based on environment
        self.use_local = USE_LOCAL
        self.use_gemini = USE_GEMINI and self.gemini_adapter.is_available()
        self.use_openrouter = USE_OPENROUTER and self.openrouter_adapter.is_available()
    
    async def generate(
        self,
        prompt: str,
        task_type: str = "general",
        provider: str = "auto",
        **kwargs
    ) -> str:
        """
        Generate response using best available model or requested provider.
        
        Args:
            prompt: The prompt to send
            task_type: Type of task (extraction, summary, reasoning)
            provider: 'auto', 'gemini', 'openrouter', or 'local'
            **kwargs: Additional parameters
            
        Returns:
            Generated response string
        """
        # Explicit Provider Selection
        if provider == "gemini":
            if self.use_gemini:
                try:
                    return await self.gemini_adapter.generate(prompt, **kwargs)
                except Exception as e:
                    return f"[Error using Gemini: {str(e)}]"
            else:
                return "[Gemini is not configured or available]"

        if provider == "openrouter":
            if self.use_openrouter:
                try:
                    return await self.openrouter_adapter.generate(prompt, **kwargs)
                except Exception as e:
                    return f"[Error using OpenRouter: {str(e)}]"
            else:
                return "[OpenRouter is not configured or available]"
                
        if provider == "local":
             if self.use_local:
                 return await self.local_adapter.generate(prompt, **kwargs)
             else:
                 return "[Local model is not enabled]"

        # === AUTO MODE (Fallback Logic) ===
        
        # For simple extraction tasks, prefer local
        if task_type == "extraction" and self.use_local:
            try:
                return await self.local_adapter.generate(prompt, **kwargs)
            except Exception:
                pass
        
        # For summaries and reasoning, prefer Gemini
        if self.use_gemini:
            try:
                return await self.gemini_adapter.generate(prompt, **kwargs)
            except RateLimitError:
                print("Gemini rate limited, trying fallback...")
            except Exception as e:
                print(f"Gemini error: {e}")
        
        # Fallback to OpenRouter
        if self.use_openrouter:
            try:
                return await self.openrouter_adapter.generate(prompt, **kwargs)
            except RateLimitError:
                print("OpenRouter rate limited")
            except Exception as e:
                print(f"OpenRouter error: {e}")
        
        # Final fallback to local/template
        if self.use_local:
            return await self.local_adapter.generate(prompt, **kwargs)
        
        return "[AI service temporarily unavailable. Please try again later.]"
    
    async def summarize_report(
        self,
        extracted_text: str,
        lab_values: List[Dict],
        abnormal_findings: List[Dict],
        provider: str = "auto"
    ) -> str:
        """
        Generate AI summary of medical report.
        """
        # Build prompt
        prompt = self._build_report_summary_prompt(
            extracted_text,
            lab_values,
            abnormal_findings
        )
        
        return await self.generate(prompt, task_type="summary", provider=provider)
    
    def _build_report_summary_prompt(
        self,
        extracted_text: str,
        lab_values: List[Dict],
        abnormal_findings: List[Dict]
    ) -> str:
        """Build prompt for report summarization."""
        # Truncate text if too long
        text_preview = extracted_text[:1000] if len(extracted_text) > 1000 else extracted_text
        
        # Format lab values
        lab_summary = "\n".join([
            f"- {lab['name']}: {lab['value']} {lab['unit']} ({'ABNORMAL' if lab.get('is_abnormal') else 'normal'})"
            for lab in lab_values[:15]  # Limit to 15
        ])
        
        # Format abnormal findings
        abnormal_summary = "\n".join([
            f"- {f['test_name']}: {f['value']} {f['unit']} ({f['direction']}, {f['severity']})"
            for f in abnormal_findings
        ])
        
        prompt = f"""Summarize the following medical lab report into a concise clinical note.

IMPORTANT GUIDELINES:
- Highlight abnormal values and their clinical significance
- Do NOT provide diagnosis or treatment recommendations
- Do NOT suggest specific medications or dosages
- Keep the summary factual and objective
- Recommend consulting a healthcare provider

EXTRACTED TEXT (preview):
{text_preview}

PARSED LAB VALUES:
{lab_summary if lab_summary else "No lab values extracted"}

ABNORMAL FINDINGS:
{abnormal_summary if abnormal_summary else "No abnormal findings detected"}

Please provide a brief, professional summary suitable for pre-consultation review."""

        return prompt
    
    async def extract_symptoms_ai(self, text: str) -> Dict[str, Any]:
        """
        Use AI to extract symptoms from text (enhanced extraction).
        
        Falls back to rule-based extraction if AI unavailable.
        """
        prompt = f"""Extract medical symptoms from the following patient description.

Return a JSON object with:
- symptoms: list of canonical symptom names
- duration: how long symptoms have been present (if mentioned)
- severity: severity level if mentioned (mild/moderate/severe)

Patient description: "{text}"

Return ONLY valid JSON, no other text."""

        try:
            response = await self.generate(prompt, task_type="extraction")
            
            # Try to parse JSON response
            import json
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            return json.loads(response)
        except Exception:
            # Return empty result on failure
            return {"symptoms": [], "duration": None, "severity": None}

    async def generate_chat_response(
        self,
        system_prompt: str,
        user_message: str,
        session_context: Dict[str, Any],
        provider: str = "auto"
    ) -> str:
        """
        Generate chat response using Gemini or fallback.
        """
        full_prompt = f"{system_prompt}\n\nUSER QUESTION: {user_message}"
        
        # We can pass context as kwargs if adapters supported it, but for now simple concatenation
        return await self.generate(full_prompt, task_type="reasoning", provider=provider)
    
    async def identify_pill(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Identify pill from image using Gemini Vision (or mockup fallback).
        """
        # PROMPT for Vision Model
        prompt = """
        Analyze this pill image. Identify:
        1. Imprint code (letters/numbers on pill)
        2. Shape (round, oval, etc.)
        3. Color
        4. Likely Drug Name (if confident)
        5. Strength (e.g. 500mg)
        
        DISCLAIMER: State clearly that this is AI identification and requires pharmacist verification.
        
        Return JSON: {
            "imprint": "...",
            "characteristics": "...",
            "likely_name": "...",
            "strength": "...",
            "safety_warning": "..."
        }
        """

        if self.use_gemini and self.gemini_adapter:
             # In a real scenario, we'd pass the image bytes to Gemini Vision here
             # self.gemini_adapter.generate_vision(image_bytes, prompt)
             pass
        
        # MOCK RESPONSE (For now, as Vision API setup is complex without actual tokens/images)
        # In production, this would call the actual Vision API.
        import asyncio
        await asyncio.sleep(1) # Simulate think time
        return {
            "imprint": "AL T 500",
            "characteristics": "White, Oval",
            "likely_name": "Acetaminophen (Generic for Tylenol)",
            "strength": "500 mg",
            "safety_warning": "⚠️ visual identification is experimental. Verify with a pharmacist."
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all adapters."""
        return {
            "local": {
                "enabled": self.use_local,
                "available": self.local_adapter.is_available()
            },
            "gemini": {
                "enabled": self.use_gemini,
                "available": self.gemini_adapter.is_available()
            },
            "openrouter": {
                "enabled": self.use_openrouter,
                "available": self.openrouter_adapter.is_available()
            }
        }
