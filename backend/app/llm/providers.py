"""Model providers an admin can register. Calls go through LiteLLM, keyed by `prefix`."""

PROVIDERS: dict[str, dict] = {
    "anthropic": {"label": "Anthropic", "prefix": "anthropic", "needs_base": False,
                  "example": "claude-opus-5-5"},
    "openai": {"label": "OpenAI", "prefix": "openai", "needs_base": False, "example": "gpt-5"},
    "azure": {"label": "Azure OpenAI", "prefix": "azure", "needs_base": True,
              "example": "my-deployment-name"},
    "bedrock": {"label": "AWS Bedrock", "prefix": "bedrock", "needs_base": False,
                "example": "anthropic.claude-sonnet-5-5"},
    "vertex_ai": {"label": "Google Vertex AI", "prefix": "vertex_ai", "needs_base": False,
                  "example": "gemini-2.5-pro"},
    "openai_compatible": {"label": "OpenAI-compatible URL (vLLM, Ollama, gateways)", "prefix": "openai",
                          "needs_base": True, "example": "llama-3.3-70b"},
    "demo": {"label": "Demo (sample answers, no AI)", "prefix": None, "needs_base": False,
             "example": "demo"},
}

# Ordered from least to most sensitive. A model may receive data up to its own level.
DATA_LEVELS = ["public", "code", "production"]

STAGES = ["knowledge", "impact", "plan", "build", "document"]
