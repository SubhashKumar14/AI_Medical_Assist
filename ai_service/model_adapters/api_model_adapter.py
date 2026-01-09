"""
API Model Adapter

Unified adapter for cloud-based AI APIs:
- Google Gemini Pro
- OpenRouter (multi-model)
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class APIAdapter(ABC):
    """Base class for API adapters."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if API is configured."""
        pass


class GeminiAdapter(APIAdapter):
    """
    Adapter for Google Gemini Pro API.
    
    Best for:
    - Medical text reasoning
    - Report summarization
    - Conversational responses
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._client = None
        self._initialized = False
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _initialize(self):
        """Initialize Gemini client."""
        if self._initialized:
            return
        
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel('gemini-pro')
            self._initialized = True
        except ImportError:
            raise ImportError("google-generativeai package not installed")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """
        Generate response using Gemini Pro.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum response tokens
            
        Returns:
            Generated text
        """
        self._initialize()
        
        try:
            response = self._client.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                raise RateLimitError(f"Gemini rate limit: {e}")
            raise


class OpenRouterAdapter(APIAdapter):
    """
    Adapter for OpenRouter API.
    
    Provides access to multiple models:
    - Claude (Anthropic)
    - Mixtral
    - LLaMA
    - And many others
    
    Good for:
    - Vendor flexibility
    - Cost optimization
    - Fallback scenarios
    """
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Available models (cost-effectiveness ordered)
    MODELS = {
        "haiku": "anthropic/claude-3-haiku",
        "mixtral": "mistralai/mixtral-8x7b-instruct",
        "llama": "meta-llama/llama-3-70b-instruct",
        "sonnet": "anthropic/claude-3-sonnet",
        "gpt4": "openai/gpt-4-turbo"
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.default_model = self.MODELS["haiku"]  # Cost-effective default
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """
        Generate response using OpenRouter.
        
        Args:
            prompt: Input prompt
            model: Model key or full model name
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            
        Returns:
            Generated text
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
        
        # Resolve model name
        model_name = self.MODELS.get(model, model) if model else self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telemedicine-cdss.app",
            "X-Title": "AI Telemedicine CDSS"
        }
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("OpenRouter rate limit exceeded")
                    
                    response.raise_for_status()
                    data = await response.json()
                    
                    return data["choices"][0]["message"]["content"]
                    
        except aiohttp.ClientError as e:
            raise ConnectionError(f"OpenRouter connection error: {e}")
    
    async def generate_with_fallback(
        self,
        prompt: str,
        models: List[str] = None,
        **kwargs
    ) -> str:
        """
        Try multiple models with fallback.
        
        Args:
            prompt: Input prompt
            models: List of models to try in order
            
        Returns:
            Generated text from first successful model
        """
        models = models or ["haiku", "mixtral", "llama"]
        
        last_error = None
        for model in models:
            try:
                return await self.generate(prompt, model=model, **kwargs)
            except (RateLimitError, ConnectionError) as e:
                last_error = e
                continue
        
        raise last_error or Exception("All models failed")


class RateLimitError(Exception):
    """Exception for API rate limits."""
    pass


# Factory function
def get_api_adapter(provider: str = "gemini") -> APIAdapter:
    """
    Get API adapter by provider name.
    
    Args:
        provider: "gemini" or "openrouter"
        
    Returns:
        Configured API adapter
    """
    if provider == "gemini":
        return GeminiAdapter()
    elif provider == "openrouter":
        return OpenRouterAdapter()
    else:
        raise ValueError(f"Unknown provider: {provider}")
