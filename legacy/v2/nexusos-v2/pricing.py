"""
NexusOS Pricing Model
OpenRouter-style pay-per-token pricing with BYOK support
"""

# Model Pricing (per 1M tokens) - based on OpenRouter rates
# Format: {"provider/model": {"input_price": X, "output_price": Y}}

PRICING = {
    # OpenAI Models
    "openai/gpt-4o": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "openai/gpt-4.1": {"input": 2.00, "output": 8.00, "provider": "openai"},
    "openai/gpt-4.1-mini": {"input": 0.40, "output": 1.60, "provider": "openai"},
    "openai/o1": {"input": 15.00, "output": 60.00, "provider": "openai"},
    "openai/o3-mini": {"input": 1.10, "output": 4.40, "provider": "openai"},
    
    # Anthropic Models
    "anthropic/claude-opus-4": {"input": 5.00, "output": 25.00, "provider": "anthropic"},
    "anthropic/claude-sonnet-4": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "anthropic/claude-haiku-4": {"input": 1.00, "output": 5.00, "provider": "anthropic"},
    "anthropic/claude-3-7-sonnet": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    
    # Google Models
    "google/gemini-2.5-pro": {"input": 0.50, "output": 2.50, "provider": "google"},
    "google/gemini-2.5-flash": {"input": 0.05, "output": 0.40, "provider": "google"},
    
    # DeepSeek Models
    "deepseek/deepseek-r1": {"input": 0.70, "output": 2.50, "provider": "deepseek"},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28, "provider": "deepseek"},
    
    # Local Models (free via Ollama)
    "ollama/phi3": {"input": 0, "output": 0, "provider": "ollama"},
    "ollama/llama3": {"input": 0, "output": 0, "provider": "ollama"},
    "ollama/mistral": {"input": 0, "output": 0, "provider": "ollama"},
    "ollama/codellama": {"input": 0, "output": 0, "provider": "ollama"},
    
    # Meta Models
    "meta/llama-3.1-405b": {"input": 5.00, "output": 15.00, "provider": "meta"},
    "meta/llama-3.1-70b": {"input": 0.65, "output": 0.90, "provider": "meta"},
    
    # Misc Models
    "mistralai/mistral-large": {"input": 2.00, "output": 6.00, "provider": "mistralai"},
    "x-ai/grok-2": {"input": 2.00, "output": 10.00, "provider": "x-ai"},
}

# NexusOS Platform Fee (percentage)
NEXUSOS_FEE_PERCENT = 5.0  # 5% on top of provider costs

# Default Rate Limits (requests per day)
DEFAULT_RATE_LIMITS = {
    "free": {"requests_per_day": 50, "tokens_per_day": 10000},
    "basic": {"requests_per_day": 1000, "tokens_per_day": 1000000},
    "pro": {"requests_per_day": 10000, "tokens_per_day": 10000000},
    "enterprise": {"requests_per_day": -1, "tokens_per_day": -1},  # Unlimited
}


class PricingCalculator:
    """Calculate costs for API usage"""
    
    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
        """
        Calculate cost for a request
        
        Returns:
            dict with input_cost, output_cost, total_cost, provider
        """
        if model not in PRICING:
            # Default to free if unknown
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": 0,
                "output_cost": 0,
                "total_cost": 0,
                "model": model,
                "provider": "unknown",
                "currency": "USD"
            }
        
        pricing = PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "model": model,
            "provider": pricing["provider"],
            "currency": "USD"
        }
    
    @staticmethod
    def calculate_with_fee(model: str, input_tokens: int, output_tokens: int) -> dict:
        """
        Calculate cost including NexusOS platform fee
        """
        base = PricingCalculator.calculate_cost(model, input_tokens, output_tokens)
        
        if base["total_cost"] > 0:
            fee = base["total_cost"] * (NEXUSOS_FEE_PERCENT / 100)
            base["platform_fee"] = round(fee, 6)
            base["total_with_fee"] = round(base["total_cost"] + fee, 6)
        else:
            base["platform_fee"] = 0
            base["total_with_fee"] = 0
        
        return base
    
    @staticmethod
    def format_cost(cost_info: dict) -> str:
        """Format cost for display"""
        if cost_info["total_with_fee"] == 0:
            return "Free"
        
        return f"${cost_info['total_with_fee']:.4f} USD"
    
    @staticmethod
    def get_all_prices() -> dict:
        """Get all model prices"""
        return {
            model: {
                "input_per_1m": f"${info['input']:.2f}",
                "output_per_1m": f"${info['output']:.2f}",
                "provider": info["provider"]
            }
            for model, info in PRICING.items()
        }
    
    @staticmethod
    def get_prices_by_provider(provider: str) -> dict:
        """Get prices filtered by provider"""
        return {
            model: {"input": info["input"], "output": info["output"]}
            for model, info in PRICING.items()
            if info["provider"] == provider
        }