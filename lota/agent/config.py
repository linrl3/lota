"""LLM configuration for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from lota.core.errors import LotaError


class ConfigurationError(LotaError):
    """Configuration related errors."""

    pass


@dataclass
class LLMConfig:
    """Configuration for the LLM."""

    provider: str = "openai"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str = "gpt-5-mini"
    temperature: float = 0.7

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigurationError(
                f"Temperature must be between 0.0 and 2.0, got {self.temperature}"
            )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables."""
        load_dotenv()

        temp_str = os.getenv("LOTA_TEMPERATURE", "0.7")
        try:
            temperature = float(temp_str)
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid LOTA_TEMPERATURE value '{temp_str}': {e}"
            ) from e

        return cls(
            provider=os.getenv("LOTA_LLM_PROVIDER", "openai"),
            api_key=os.getenv("LOTA_API_KEY") or os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("LOTA_API_BASE") or os.getenv("OPENAI_API_BASE"),
            model=os.getenv("LOTA_MODEL", "gpt-5-mini"),
            temperature=temperature,
        )

    def validate_api_key(self) -> None:
        """Validate that API key is configured."""
        if not self.api_key:
            raise ConfigurationError(
                "API key not configured. "
                "Set LOTA_API_KEY or OPENAI_API_KEY environment variable."
            )


def get_llm(config: Optional[LLMConfig] = None) -> ChatOpenAI:
    """Create a ChatOpenAI instance from configuration."""
    if config is None:
        config = LLMConfig.from_env()

    config.validate_api_key()

    kwargs = {
        "model": config.model,
        "temperature": config.temperature,
    }

    if config.api_key:
        kwargs["api_key"] = config.api_key

    if config.api_base:
        kwargs["base_url"] = config.api_base

    return ChatOpenAI(**kwargs)
