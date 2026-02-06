"""
Configuration settings for the Commander Agent system.
"""
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

# Load .env file if it exists
def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

# Load .env on import
load_env()


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "gpt-4")
    temperature: float = 0.7
    max_tokens: int = 2000
    
    def get_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        if self.provider == "google":
            return self.google_api_key
        return self.api_key


@dataclass
class AgentConfig:
    """Agent timeout and retry settings."""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass  
class Config:
    """Main configuration."""
    llm: LLMConfig = None
    agents: AgentConfig = None
    debug: bool = True
    
    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.agents is None:
            self.agents = AgentConfig()


# Global config instance
config = Config()
