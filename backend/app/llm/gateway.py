"""One entry point for every model call: picks an allowed model, enforces data levels, falls back on failure."""

from dataclasses import dataclass

from .. import vault
from ..models import ModelConfig
from .providers import DATA_LEVELS, PROVIDERS


class NoModelAvailable(Exception):
    pass


@dataclass
class LLMResult:
    text: str
    model_name: str


def _rank(level: str) -> int:
    return DATA_LEVELS.index(level) if level in DATA_LEVELS else len(DATA_LEVELS)


def candidates(models: list[ModelConfig], stage: str, data_level: str,
               preferred_id: int | None = None) -> list[ModelConfig]:
    """Models allowed to receive `data_level` data, in the order they should be tried:
    the user's choice, then models set as default for the stage, then the rest by priority."""
    allowed = [m for m in models if m.enabled and _rank(m.data_level) >= _rank(data_level)]

    def order(m: ModelConfig) -> tuple[int, int]:
        if preferred_id is not None and m.id == preferred_id:
            return (0, m.priority)
        return (1 if stage in (m.stages or []) else 2, m.priority)

    return sorted(allowed, key=order)


class Gateway:
    def __init__(self, models: list[ModelConfig]):
        self.models = models

    def complete(self, stage: str, system: str, prompt: str, data_level: str = "code",
                 preferred_id: int | None = None) -> LLMResult:
        options = candidates(self.models, stage, data_level, preferred_id)
        if not options:
            raise NoModelAvailable(
                f"No enabled model is allowed to receive '{data_level}' data. Add or enable one under Models."
            )
        errors = []
        for model in options:
            try:
                return LLMResult(call_model(model, system, prompt, stage), model.name)
            except Exception as exc:  # try the next allowed model
                errors.append(f"{model.name}: {exc}")
        raise NoModelAvailable("All allowed models failed. " + " | ".join(errors))


def call_model(model: ModelConfig, system: str, prompt: str, stage: str) -> str:
    if model.provider == "demo":
        from ..demo.answers import demo_answer

        return demo_answer(stage, prompt)

    provider = PROVIDERS.get(model.provider)
    if provider is None:
        raise ValueError(f"Unknown provider '{model.provider}'")

    import litellm  # imported lazily: it is slow to load

    kwargs: dict = {
        "model": f"{provider['prefix']}/{model.model}",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "timeout": 180,
    }
    if model.api_base:
        kwargs["api_base"] = model.api_base
    key = vault.resolve(model.secret_ref)
    if key:
        kwargs["api_key"] = key
    response = litellm.completion(**kwargs)
    return response.choices[0].message.content or ""
