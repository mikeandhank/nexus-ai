"""
Lipaira Providers Package
=========================
Unified LLM routing - replaces OpenRouter with direct provider integrations

Environment Variables Required:
--------------------------------
Each provider needs its API key set as environment variable:

OPENAI_API_KEY         - OpenAI (https://platform.openai.com)
ANTHROPIC_API_KEY     - Anthropic Claude (https://console.anthropic.com)
GOOGLE_API_KEY        - Google Gemini (https://aistudio.google.com)
MISTRAL_API_KEY       - Mistral AI (https://console.mistral.ai)
COHERE_API_KEY        - Cohere (https://dashboard.cohere.com)
DEEPSEEK_API_KEY      - DeepSeek (https://platform.deepseek.com)
DASHSCOPE_API_KEY     - Alibaba Qwen (https://dashscope.console.aliyun.com)
AZURE_OPENAI_API_KEY  - Microsoft Azure (https://azure.microsoft.com)
NVIDIA_API_KEY        - Nvidia NIM (https://build.nvidia.com)
PERPLEXITY_API_KEY    - Perplexity (https://www.perplexity.ai)
ZEROONE_API_KEY       - 01.AI Yi (https://platform.01.ai)
MINIMAX_API_KEY       - MiniMax (https://platform.minimaxi.com)
TOGETHER_API_KEY      - Together AI (https://together.ai)

OLLAMA_URL            - Ollama endpoint (default: http://localhost:11434)

Usage:
------
from lipaira_providers import LipairaRouter

router = LipairaRouter()
response = router.chat([Message(role="user", content="Hello")], "gpt-4o")
print(response.content)
"""

from .router import LipairaRouter, LLMResponse, Message, Provider
from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider,
    MistralProvider,
    CohereProvider,
    DeepSeekProvider,
    QwenProvider,
    MicrosoftProvider,
    PerplexityProvider,
    ZeroOneProvider,
    MinimaxProvider,
    TogetherProvider,
    NvidiaProvider,
)

__all__ = [
    "LipairaRouter",
    "LLMResponse", 
    "Message",
    "Provider",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "OllamaProvider",
    "MistralProvider",
    "CohereProvider",
    "DeepSeekProvider",
    "QwenProvider",
    "MicrosoftProvider",
    "PerplexityProvider",
    "ZeroOneProvider",
    "MinimaxProvider",
    "TogetherProvider",
    "NvidiaProvider",
]

__version__ = "0.1.0"
