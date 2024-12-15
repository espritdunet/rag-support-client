"""
Test configuration settings module.

This module contains tests for verifying the correct loading and parsing
of application settings.

Returns:
    None: These tests verify configuration settings behavior
"""

import pytest

from rag_support_client.config.config import Settings


def test_settings_load() -> None:
    """
    Test that settings can be loaded correctly.

    Returns:
        None: Verifies basic settings are loaded with expected values
    """
    settings = Settings()
    assert settings.APP_NAME == "RAG Support Client"
    assert isinstance(settings.stop_sequences, list)
    assert len(settings.stop_sequences) == 2
    assert "\nHuman:" in settings.stop_sequences
    assert "\nAssistant:" in settings.stop_sequences


@pytest.mark.parametrize(
    "input_sequences,expected",
    [
        ("\nHuman:,\nAssistant:", ["\nHuman:", "\nAssistant:"]),
        ("", ["\nHuman:", "\nAssistant:"]),
        ("\nHuman:", ["\nHuman:"]),
        ("\nHuman:,\nAssistant:,\nAI:", ["\nHuman:", "\nAssistant:", "\nAI:"]),
    ],
)
def test_stop_sequences_parsing(input_sequences: str, expected: list[str]) -> None:
    """
    Test stop sequences parsing with different inputs.

    Args:
        input_sequences: String of comma-separated sequences to test
        expected: List of expected parsed sequences

    Returns:
        None: Verifies stop sequences are correctly parsed for various inputs
    """
    settings = Settings(LLM_STOP_SEQUENCES=input_sequences)
    assert settings.stop_sequences == expected
