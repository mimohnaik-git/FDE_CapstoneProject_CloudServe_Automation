import os
import pytest
from unittest.mock import patch
from src.config import AppConfig

def test_config_imports_without_api_key_and_live_provider_validation_fails_loudly():
    """Asserts that runtime execution terminates immediately if critical tokens are missing."""
    with patch.dict(os.environ, clear=True):
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
            
        config_instance = AppConfig()
        with pytest.raises(ValueError) as exception_context:
            config_instance.require_openrouter_api_key()
        assert "OPENROUTER_API_KEY" in str(exception_context.value)

def test_config_successful_type_parsing_and_defaults():
    """Asserts that configuration parameters successfully map into explicit target types."""
    mock_valid_env = {
        "OPENROUTER_API_KEY": "sk-openrouter-mock-validation-string-token",
        "CLASSIFICATION_CONFIDENCE_THRESHOLD": "0.85",
        "RETRIEVAL_ROUTING_THRESHOLD": "0.35",
        "RETRIEVAL_TOP_K": "3"
    }
    with patch.dict(os.environ, mock_valid_env, clear=True):
        config_instance = AppConfig()
        assert config_instance.OPENROUTER_API_KEY == "sk-openrouter-mock-validation-string-token"
        assert config_instance.require_openrouter_api_key() == "sk-openrouter-mock-validation-string-token"
        assert config_instance.CLASSIFICATION_CONFIDENCE_THRESHOLD == 0.85
        assert config_instance.CONFIDENCE_THRESHOLD == 0.85
        assert config_instance.RETRIEVAL_ROUTING_THRESHOLD == 0.35
        assert config_instance.RETRIEVAL_TOP_K == 3
        assert hasattr(config_instance.CHROMA_PATH, "mkdir")


def test_legacy_confidence_environment_name_remains_compatible():
    with patch.dict(os.environ, {"CONFIDENCE_THRESHOLD": "0.72"}, clear=True):
        config_instance = AppConfig()
        assert config_instance.CLASSIFICATION_CONFIDENCE_THRESHOLD == 0.72


def test_groq_configuration_and_credential_validation():
    groq_env = {
        "GROQ_API_KEY": "synthetic-groq-key",
        "GROQ_MODEL_NAME": "groq-test-model",
        "GROQ_BASE_URL": "https://groq.invalid/openai/v1/",
    }
    with patch.dict(os.environ, groq_env, clear=True):
        config_instance = AppConfig()
        assert config_instance.require_groq_api_key() == "synthetic-groq-key"
        assert config_instance.GROQ_MODEL_NAME == "groq-test-model"
        assert config_instance.GROQ_BASE_URL == "https://groq.invalid/openai/v1"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CLASSIFICATION_CONFIDENCE_THRESHOLD", "not-a-number"),
        ("CLASSIFICATION_CONFIDENCE_THRESHOLD", "1.1"),
        ("RETRIEVAL_ROUTING_THRESHOLD", "nan"),
        ("RETRIEVAL_ROUTING_THRESHOLD", "-0.1"),
    ],
)
def test_routing_threshold_configuration_fails_closed(name, value):
    with patch.dict(os.environ, {name: value}, clear=True):
        with pytest.raises(ValueError, match=name):
            AppConfig()

@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_retrieval_top_k_must_be_a_positive_integer(value):
    with patch.dict(os.environ, {"RETRIEVAL_TOP_K": value}, clear=True):
        with pytest.raises(ValueError, match="RETRIEVAL_TOP_K"):
            AppConfig()
