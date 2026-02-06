"""
LLM Client - Unified interface for OpenAI and Google Gemini.

Supports:
- OpenAI GPT-4 / GPT-3.5 (both old and new API versions)
- Google Gemini Pro
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    tokens_used: int = 0


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Generate completion from LLM."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client - supports both old (0.28) and new (1.0+) API."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self._use_new_api = None
    
    def _check_api_version(self):
        """Check which OpenAI API version is installed."""
        if self._use_new_api is not None:
            return self._use_new_api
        
        try:
            from openai import AsyncOpenAI
            self._use_new_api = True
        except ImportError:
            self._use_new_api = False
        
        return self._use_new_api
    
    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Generate completion using OpenAI."""
        if self._check_api_version():
            return await self._complete_new_api(prompt, system_prompt)
        else:
            return await self._complete_old_api(prompt, system_prompt)
    
    async def _complete_new_api(self, prompt: str, system_prompt: str = "") -> str:
        """Use new OpenAI API (1.0+)."""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=self.api_key)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    async def _complete_old_api(self, prompt: str, system_prompt: str = "") -> str:
        """Use old OpenAI API (0.28.x)."""
        import openai
        
        openai.api_key = self.api_key
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Old API uses synchronous calls
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content


class GoogleGeminiClient(BaseLLMClient):
    """Google Gemini client."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                raise ImportError("Please install google-generativeai: pip install google-generativeai")
        return self._client
    
    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Generate completion using Gemini."""
        client = self._get_client()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Gemini doesn't have native async, so we use sync in async context
        response = client.generate_content(full_prompt)
        
        return response.text


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API keys."""
    
    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        """Return a mock response based on prompt content."""
        prompt_lower = prompt.lower()
        
        # Mock planning response
        if "investigation plan" in prompt_lower or "create" in prompt_lower and "plan" in prompt_lower:
            if "latency" in prompt_lower:
                return json.dumps({
                    "reasoning": "Latency issue detected - metrics will show the spike, logs may have slow queries, deploy may show recent changes",
                    "steps": [
                        {"agent": "metrics", "reason": "Check latency spikes and resource utilization", "priority": 1},
                        {"agent": "logs", "reason": "Find slow queries or timeout errors", "priority": 2},
                        {"agent": "deploy", "reason": "Check for recent deployments that may have caused the issue", "priority": 3}
                    ]
                })
            else:
                return json.dumps({
                    "reasoning": "General issue - checking all data sources",
                    "steps": [
                        {"agent": "logs", "reason": "Check for errors", "priority": 1},
                        {"agent": "metrics", "reason": "Check metrics", "priority": 2},
                        {"agent": "deploy", "reason": "Check deployments", "priority": 3}
                    ]
                })
        
        # Mock decision response
        if "root cause" in prompt_lower or "analyze" in prompt_lower:
            return json.dumps({
                "root_cause": "Configuration change reduced database connection pool, causing connection exhaustion under load",
                "confidence": 0.9
            })
        
        # Default response
        return "Unable to determine. Please investigate further."


def create_llm_client(
    provider: str = None,
    api_key: str = None,
    model: str = None
) -> BaseLLMClient:
    """
    Factory function to create the appropriate LLM client.
    
    Reads from environment variables if not provided.
    Falls back to MockLLMClient if no API key is available.
    """
    # Load from environment if not provided
    provider = provider or os.getenv("LLM_PROVIDER", "openai")
    model = model or os.getenv("LLM_MODEL", "gpt-4")
    
    # Get API key based on provider
    if api_key is None:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY", "")
    
    # If no API key, use mock
    if not api_key or api_key == "your-openai-api-key-here" or api_key == "your-google-api-key-here":
        print("[LLM] No API key found - using MockLLMClient (heuristic reasoning)")
        return MockLLMClient()
    
    # Create appropriate client
    if provider == "openai":
        print(f"[LLM] Using OpenAI with model: {model}")
        return OpenAIClient(api_key=api_key, model=model)
    elif provider == "google":
        print(f"[LLM] Using Google Gemini with model: {model}")
        return GoogleGeminiClient(api_key=api_key, model=model)
    else:
        print(f"[LLM] Unknown provider '{provider}' - using MockLLMClient")
        return MockLLMClient()
