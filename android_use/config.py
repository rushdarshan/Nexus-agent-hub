"""
Configuration module for Android-Use
Centralized settings and environment management
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AndroidUseConfig:
    """Global configuration for android-use package"""
    
    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("android_output"))
    save_screenshots: bool = True
    screenshot_quality: int = 90
    
    # Agent defaults
    default_max_steps: int = 20
    default_step_delay: float = 1.0
    default_budget: float = 2.0
    loop_threshold: int = 3
    
    # LLM settings
    default_model: str = "openai/gpt-4o-mini"
    default_provider: str = "openrouter"
    temperature: float = 0.3
    
    # API keys (from environment)
    openrouter_api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENROUTER_API_KEY'))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    google_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GOOGLE_API_KEY'))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY'))
    
    # Device settings
    default_device_serial: Optional[str] = field(default_factory=lambda: os.getenv('ANDROID_SERIAL'))
    device_timeout: float = 30.0
    
    # Demo mode
    demo_mode: bool = False
    demo_delay: float = 0.5
    
    # Logging
    log_level: str = "INFO"
    
    def __post_init__(self):
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def has_api_key(self) -> bool:
        """Check if any API key is configured"""
        return bool(
            self.openrouter_api_key or 
            self.openai_api_key or 
            self.google_api_key or
            self.anthropic_api_key
        )
    
    @property
    def best_api_key(self) -> Optional[str]:
        """Get the first available API key"""
        return (
            self.openrouter_api_key or 
            self.openai_api_key or 
            self.google_api_key or
            self.anthropic_api_key
        )


# Global config instance
config = AndroidUseConfig()


def get_config() -> AndroidUseConfig:
    """Get the global configuration"""
    return config


def update_config(**kwargs) -> AndroidUseConfig:
    """Update global configuration"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
