from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    """Configuração da aplicação, validada uma vez na subida do processo."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ambiente: Literal["desenvolvimento", "producao", "teste"] = "desenvolvimento"

    provedor_llm: Literal["anthropic", "fake"] = "anthropic"
    # A chave nunca é lida de outro lugar além do ambiente, e nunca é logada:
    # SecretStr mascara o valor em repr(), logs e tracebacks.
    anthropic_api_key: SecretStr | None = None
    modelo_llm: str = "claude-opus-4-8"

    database_url: str = "postgresql+asyncpg://chatbot:chatbot@localhost:5437/chatbot"
    redis_url: str = "redis://localhost:6383/0"

    origens_permitidas: list[str] = Field(default_factory=lambda: ["http://localhost:8000"])

    @model_validator(mode="after")
    def exigir_chave_do_provedor(self) -> Self:
        if self.provedor_llm == "anthropic" and self.anthropic_api_key is None:
            raise ValueError(
                'ANTHROPIC_API_KEY é obrigatória quando PROVEDOR_LLM="anthropic". '
                'Defina a chave no .env ou use PROVEDOR_LLM="fake".'
            )
        return self


@lru_cache(maxsize=1)
def obter_configuracao() -> Configuracao:
    return Configuracao()
