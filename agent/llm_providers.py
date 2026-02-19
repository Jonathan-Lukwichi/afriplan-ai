"""
LLM Provider Abstraction for AfriPlan Electrical v4.1

Supports multiple AI providers:
- Google Gemini (FREE tier available)
- Anthropic Claude (paid)

Usage:
    provider = get_provider("gemini")  # or "claude"
    response = provider.extract_with_vision(images, prompt)
"""

import os
import base64
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Provider selection
DEFAULT_PROVIDER = "gemini"  # Change to "claude" if you have Anthropic credits


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    cost_zar: float = 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def extract_with_vision(
        self,
        images: List[str],  # base64 encoded images
        prompt: str,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Extract data from images using vision capabilities."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider - FREE tier available!"""

    # Gemini models
    FLASH_MODEL = "gemini-1.5-flash"  # Fast, free tier
    PRO_MODEL = "gemini-1.5-pro"      # More capable, limited free

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None
        self._model = None

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
                self._model = genai.GenerativeModel(self.FLASH_MODEL)
            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Run: pip install google-generativeai"
                )
        return self._client, self._model

    def is_available(self) -> bool:
        """Check if Gemini is configured."""
        if not self.api_key:
            return False
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def extract_with_vision(
        self,
        images: List[str],
        prompt: str,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Extract data from images using Gemini Vision."""
        _, model = self._get_client()

        # Build content parts
        content_parts = [prompt]

        for img_base64 in images:
            # Gemini expects image data differently
            import PIL.Image
            import io

            # Decode base64 to bytes
            img_bytes = base64.b64decode(img_base64)
            img = PIL.Image.open(io.BytesIO(img_bytes))
            content_parts.append(img)

        # Generate response
        response = model.generate_content(
            content_parts,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.1,  # Low temperature for structured extraction
            }
        )

        # Extract token counts (Gemini provides these)
        input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
        output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0

        return LLMResponse(
            text=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.FLASH_MODEL,
            cost_zar=0.0,  # Free tier!
        )


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider - requires paid API."""

    SONNET_MODEL = "claude-sonnet-4-20250514"
    OPUS_MODEL = "claude-opus-4-20250514"
    HAIKU_MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Run: pip install anthropic"
                )
        return self._client

    def is_available(self) -> bool:
        """Check if Claude is configured."""
        if not self.api_key:
            return False
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def extract_with_vision(
        self,
        images: List[str],
        prompt: str,
        max_tokens: int = 8192,
        model: str = None,
    ) -> LLMResponse:
        """Extract data from images using Claude Vision."""
        client = self._get_client()
        model = model or self.SONNET_MODEL

        # Build content with images
        content = [{"type": "text", "text": prompt}]

        for img_base64 in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_base64,
                }
            })

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}]
        )

        # Calculate cost (ZAR)
        from agent.utils import estimate_cost_zar
        cost = estimate_cost_zar(
            model,
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return LLMResponse(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
            cost_zar=cost,
        )


# Provider registry
_providers: Dict[str, LLMProvider] = {}


def get_provider(name: str = None) -> LLMProvider:
    """
    Get an LLM provider by name.

    Args:
        name: Provider name ("gemini" or "claude").
              If None, uses DEFAULT_PROVIDER.

    Returns:
        Configured LLMProvider instance
    """
    name = name or DEFAULT_PROVIDER
    name = name.lower()

    if name not in _providers:
        if name == "gemini":
            _providers[name] = GeminiProvider()
        elif name == "claude":
            _providers[name] = ClaudeProvider()
        else:
            raise ValueError(f"Unknown provider: {name}. Use 'gemini' or 'claude'.")

    return _providers[name]


def get_available_provider() -> Tuple[str, LLMProvider]:
    """
    Get the first available provider.

    Returns:
        Tuple of (provider_name, provider_instance)
    """
    # Try Gemini first (free!)
    gemini = get_provider("gemini")
    if gemini.is_available():
        return "gemini", gemini

    # Fall back to Claude
    claude = get_provider("claude")
    if claude.is_available():
        return "claude", claude

    raise RuntimeError(
        "No LLM provider available. Please set either:\n"
        "- GEMINI_API_KEY for Google Gemini (free)\n"
        "- ANTHROPIC_API_KEY for Claude (paid)"
    )


def configure_provider(name: str, api_key: str) -> LLMProvider:
    """
    Configure a provider with an API key.

    Args:
        name: Provider name ("gemini" or "claude")
        api_key: API key for the provider

    Returns:
        Configured provider instance
    """
    name = name.lower()

    if name == "gemini":
        provider = GeminiProvider(api_key=api_key)
    elif name == "claude":
        provider = ClaudeProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown provider: {name}")

    _providers[name] = provider
    return provider
