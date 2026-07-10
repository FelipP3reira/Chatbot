import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsConfigDict

from app.config import Configuracao


class ConfiguracaoIsolada(Configuracao):
    """Ignora o .env do desenvolvedor: cada teste declara o que precisa."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")


def test_provedor_anthropic_sem_chave_falha_na_subida() -> None:
    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
        ConfiguracaoIsolada(provedor_llm="anthropic", anthropic_api_key=None)


def test_provedor_fake_dispensa_chave() -> None:
    configuracao = ConfiguracaoIsolada(provedor_llm="fake", anthropic_api_key=None)

    assert configuracao.provedor_llm == "fake"


def test_chave_nao_aparece_ao_imprimir_a_configuracao() -> None:
    configuracao = ConfiguracaoIsolada(
        provedor_llm="anthropic", anthropic_api_key=SecretStr("sk-ant-segredo")
    )

    assert "sk-ant-segredo" not in repr(configuracao)
    assert configuracao.anthropic_api_key is not None
    assert configuracao.anthropic_api_key.get_secret_value() == "sk-ant-segredo"
