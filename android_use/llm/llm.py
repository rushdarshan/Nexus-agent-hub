"""
LLM - Multi-provider Language Model Interface
Mirrors browser-use's LLM abstraction with support for vision models
"""

import os
import json
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pathlib import Path
from PIL import Image
import io

logger = logging.getLogger('android_use.llm')


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    provider: LLMProvider = LLMProvider.OPENROUTER
    model: str = "openai/gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: float = 60.0
    
    def __post_init__(self):
        # Auto-detect API key from environment
        if not self.api_key:
            env_keys = {
                LLMProvider.OPENAI: 'OPENAI_API_KEY',
                LLMProvider.OPENROUTER: 'OPENROUTER_API_KEY',
                LLMProvider.GOOGLE: 'GOOGLE_API_KEY',
                LLMProvider.ANTHROPIC: 'ANTHROPIC_API_KEY',
            }
            env_key = env_keys.get(self.provider)
            if env_key:
                self.api_key = os.getenv(env_key)
        
        # Auto-set base URL
        if not self.base_url:
            base_urls = {
                LLMProvider.OPENAI: 'https://api.openai.com/v1',
                LLMProvider.OPENROUTER: 'https://openrouter.ai/api/v1',
                LLMProvider.ANTHROPIC: 'https://api.anthropic.com/v1',
                LLMProvider.OLLAMA: 'http://localhost:11434/v1',
            }
            self.base_url = base_urls.get(self.provider)


class LLM:
    """
    Multi-provider LLM client with vision support.
    Uses OpenAI-compatible API format for most providers.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None, **kwargs):
        """
        Initialize LLM client.
        
        Args:
            config: LLMConfig instance
            **kwargs: Override config values (model, api_key, etc.)
        """
        self.config = config or LLMConfig()
        
        # Apply overrides
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate client"""
        try:
            import openai
            
            if self.config.provider == LLMProvider.GOOGLE:
                # Use Google's generativeai library
                self._init_google()
            else:
                # Use OpenAI-compatible client
                self._client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout
                )
                logger.info(f"Initialized {self.config.provider.value} client with model {self.config.model}")
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    def _init_google(self):
        """Initialize Google Generative AI client"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self._google_model = genai.GenerativeModel(self.config.model.replace('google/', ''))
            logger.info(f"Initialized Google AI with model {self.config.model}")
        except ImportError:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
    
    @staticmethod
    def image_to_base64(image: Union[Image.Image, str, Path]) -> str:
        """Convert image to base64 string"""
        if isinstance(image, (str, Path)):
            with open(image, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        else:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    async def chat(
        self,
        prompt: str,
        image: Optional[Union[Image.Image, str, Path]] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = True
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.
        
        Args:
            prompt: User prompt text
            image: Optional image for vision models
            system_prompt: Optional system prompt
            json_response: If True, expect JSON response
            
        Returns:
            Parsed response dict or raw content
        """
        if self.config.provider == LLMProvider.GOOGLE:
            return await self._chat_google(prompt, image, json_response)
        else:
            return await self._chat_openai(prompt, image, system_prompt, json_response)
    
    async def _chat_openai(
        self,
        prompt: str,
        image: Optional[Union[Image.Image, str, Path]] = None,
        system_prompt: Optional[str] = None,
        json_response: bool = True
    ) -> Dict[str, Any]:
        """OpenAI-compatible chat completion"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Build user message content
        content = []
        content.append({"type": "text", "text": prompt})
        
        if image:
            b64_image = self.image_to_base64(image)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_image}"}
            })
        
        messages.append({"role": "user", "content": content})
        
        # Request parameters
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        if json_response:
            params["response_format"] = {"type": "json_object"}
        
        try:
            response = await self._client.chat.completions.create(**params)
            content = response.choices[0].message.content
            
            if json_response:
                return json.loads(content)
            return {"content": content}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"error": "Invalid JSON response", "raw": content}
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {"error": str(e)}
    
    async def _chat_google(
        self,
        prompt: str,
        image: Optional[Union[Image.Image, str, Path]] = None,
        json_response: bool = True
    ) -> Dict[str, Any]:
        """Google Generative AI chat"""
        import google.generativeai as genai
        
        content_parts = []
        
        # Add image first if provided
        if image:
            if isinstance(image, (str, Path)):
                img = Image.open(image)
            else:
                img = image
            content_parts.append(img)
        
        # Add text prompt
        if json_response:
            prompt = prompt + "\n\nRespond with valid JSON only, no markdown code blocks."
        content_parts.append(prompt)
        
        try:
            # Use sync API wrapped in asyncio
            import asyncio
            
            def sync_generate():
                return self._google_model.generate_content(
                    content_parts,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.config.temperature,
                        max_output_tokens=self.config.max_tokens,
                    )
                )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, sync_generate)
            
            content = response.text
            logger.info(f"Google raw response: {content[:500]}...")
            
            if json_response:
                # Extract JSON from response
                json_match = content.strip()
                if '```json' in content:
                    json_match = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    json_match = content.split('```')[1].split('```')[0]
                return json.loads(json_match.strip())
            
            return {"content": content}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {content}")
            return {"error": "Invalid JSON response", "raw": content}
        except Exception as e:
            logger.error(f"Google AI request failed: {e}")
            return {"error": str(e)}


# Convenience factory functions
def create_openai_llm(model: str = "gpt-4o-mini", api_key: str = None) -> LLM:
    """Create OpenAI LLM client"""
    return LLM(LLMConfig(
        provider=LLMProvider.OPENAI,
        model=model,
        api_key=api_key
    ))


def create_openrouter_llm(model: str = "openai/gpt-4o-mini", api_key: str = None) -> LLM:
    """Create OpenRouter LLM client"""
    return LLM(LLMConfig(
        provider=LLMProvider.OPENROUTER,
        model=model,
        api_key=api_key
    ))


def create_gemini_llm(model: str = "gemini-1.5-flash", api_key: str = None) -> LLM:
    """Create Google Gemini LLM client"""
    return LLM(LLMConfig(
        provider=LLMProvider.GOOGLE,
        model=f"google/{model}",
        api_key=api_key
    ))


def create_anthropic_llm(model: str = "claude-3-5-sonnet-20241022", api_key: str = None) -> LLM:
    """Create Anthropic LLM client"""
    return LLM(LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model=model,
        api_key=api_key
    ))
