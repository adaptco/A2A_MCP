# tests/test_system_prompt.py
"""Unit tests for the SystemPrompt schema and pre-built instances."""
import json

import pytest

from schemas.system_prompt import (
    ARCHITECTURE_AGENT_PROMPT,
    CODING_AGENT_PROMPT,
    MANAGING_AGENT_PROMPT,
    ORCHESTRATION_AGENT_PROMPT,
    TESTING_AGENT_PROMPT,
    SystemPrompt,
)


class TestSystemPromptSchema:
    """Pydantic validation and serialisation."""

    def test_minimal_valid_prompt(self):
        sp = SystemPrompt(
            prompt_id="test-1",
            role="TestAgent",
            system_text="You are a test agent.",
        )
        assert sp.embedding_dim == 1536  # default per README
        assert sp.version == "1.0.0"

    def test_custom_embedding_dim(self):
        sp = SystemPrompt(
            prompt_id="test-2",
            role="Custom",
            system_text="Hello",
            embedding_dim=768,
        )
        assert sp.embedding_dim == 768

    def test_model_context_defaults_to_empty(self):
        sp = SystemPrompt(prompt_id="t", role="R", system_text="S")
        assert sp.model_context == {}

    def test_serialisation_round_trip(self):
        sp = SystemPrompt(
            prompt_id="rt-1",
            role="RoundTrip",
            system_text="trip",
            model_context={"repo": "adaptco/A2A_MCP"},
        )
        dumped = sp.model_dump_json()
        loaded = SystemPrompt.model_validate_json(dumped)
        assert loaded == sp

    def test_missing_required_fields_raises(self):
        with pytest.raises(Exception):
            SystemPrompt()  # type: ignore[call-arg]


class TestPreBuiltPrompts:
    """Verify the pre-built prompt constants are well-formed."""

    @pytest.mark.parametrize(
        "prompt",
        [
            MANAGING_AGENT_PROMPT,
            ORCHESTRATION_AGENT_PROMPT,
            ARCHITECTURE_AGENT_PROMPT,
            CODING_AGENT_PROMPT,
            TESTING_AGENT_PROMPT,
        ],
    )
    def test_prebuilt_has_non_empty_system_text(self, prompt):
        assert len(prompt.system_text) > 20

    @pytest.mark.parametrize(
        "prompt",
        [
            MANAGING_AGENT_PROMPT,
            ORCHESTRATION_AGENT_PROMPT,
            ARCHITECTURE_AGENT_PROMPT,
            CODING_AGENT_PROMPT,
            TESTING_AGENT_PROMPT,
        ],
    )
    def test_prebuilt_has_valid_role(self, prompt):
        assert "Agent" in prompt.role

    def test_all_prompt_ids_unique(self):
        ids = [
            MANAGING_AGENT_PROMPT.prompt_id,
            ORCHESTRATION_AGENT_PROMPT.prompt_id,
            ARCHITECTURE_AGENT_PROMPT.prompt_id,
            CODING_AGENT_PROMPT.prompt_id,
            TESTING_AGENT_PROMPT.prompt_id,
        ]
        assert len(ids) == len(set(ids))
