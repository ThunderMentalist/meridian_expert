from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from meridian_expert.llm.client import (
    DeterministicFakeBackend,
    LLMClient,
    OpenAIResponsesBackend,
    _backend_from_settings,
)
from meridian_expert.llm.profiles import ModelProfile, load_profiles
from meridian_expert.llm.structured import openai_response_schema
from meridian_expert.orchestration.runner import ReviewDecision
from meridian_expert.orchestration.triage import TriageModelOutput


class TriageOutput(BaseModel):
    task_family: str
    confidence: float
    rationale: str
    needs_clarification: bool = False


class ReviewerOutput(BaseModel):
    approved: bool
    issues: list[str] = []
    notes: str = ""


def _profiles() -> dict[str, ModelProfile]:
    return {
        "triage": ModelProfile(alias="triage", model="gpt-test", reasoning_effort="medium"),
        "reviewer": ModelProfile(alias="reviewer", model="gpt-test", reasoning_effort="medium"),
        "formatter": ModelProfile(alias="formatter", model="gpt-test", reasoning_effort="low"),
    }


def test_load_profiles_parses_aliases() -> None:
    profiles = load_profiles()
    assert "triage" in profiles
    assert profiles["triage"].alias == "triage"
    assert profiles["triage"].model


def test_fake_backend_text_generation() -> None:
    client = LLMClient(backend=DeterministicFakeBackend(), profiles=_profiles())
    out = client.generate_text("formatter", "Format this", "  hello world  ")
    assert out == "hello world"


def test_fake_backend_structured_generation() -> None:
    client = LLMClient(backend=DeterministicFakeBackend(), profiles=_profiles())
    triage = client.generate_structured(
        "triage",
        "Classify",
        "This request is ambiguous and needs clarify",
        TriageOutput,
    )
    assert triage.task_family == "clarification"
    assert triage.needs_clarification is True


def test_fake_triage_uses_request_section_not_fallback_blob() -> None:
    client = LLMClient(backend=DeterministicFakeBackend(), profiles=_profiles())
    structured_input = (
        "Classify and complete triage for the request.\n"
        "Request:\n"
        "Only search meridian/model/model.py. What defaults are used?\n\n"
        "## Clarification response\n"
        "Focus on meridian model paths only.\n"
        "\nFallback hint:\n"
        '{"notes":"ambiguous unclear clarify"}'
    )
    triage = client.generate_structured("triage", "Classify", structured_input, TriageOutput)
    assert triage.task_family == "theory"
    assert triage.needs_clarification is False


def test_openai_backend_interface_with_mocked_sdk() -> None:
    fake_response = SimpleNamespace(output_text=json.dumps({"task_family": "theory", "confidence": 0.9, "rationale": "ok", "needs_clarification": False}))

    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs["model"] == "gpt-test"
            assert kwargs["reasoning"] == {"effort": "medium"}
            assert kwargs["instructions"] == "Classify"
            assert kwargs["input"] == "body"
            return fake_response

    backend = OpenAIResponsesBackend(client=SimpleNamespace(responses=FakeResponses()))
    profile = ModelProfile(alias="triage", model="gpt-test", reasoning_effort="medium")
    parsed = backend.generate_structured(profile, "Classify", "body", TriageOutput)
    assert parsed.task_family == "theory"


def test_openai_backend_structured_payload_sets_strict_and_object_schema() -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=json.dumps({"status": "approve", "issues": [], "suggested_edits": []}))

    backend = OpenAIResponsesBackend(client=SimpleNamespace(responses=FakeResponses()))
    profile = ModelProfile(alias="reviewer", model="gpt-test", reasoning_effort="medium")
    parsed = backend.generate_structured(profile, "Review", "body", ReviewDecision)

    assert parsed.status == "approve"
    text_format = captured["text"]["format"]
    assert text_format["strict"] is True
    assert text_format["schema"]["additionalProperties"] is False


def test_openai_response_schema_sets_additional_properties_for_structured_models() -> None:
    review_schema = openai_response_schema(ReviewDecision)
    triage_schema = openai_response_schema(TriageModelOutput)

    assert review_schema["additionalProperties"] is False
    assert triage_schema["additionalProperties"] is False


def test_retry_backoff_for_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[int] = []

    class RateLimitError(Exception):
        pass

    class FakeResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise RateLimitError("slow down")
            return SimpleNamespace(output_text="ok")

    responses = FakeResponses()
    backend = OpenAIResponsesBackend(client=SimpleNamespace(responses=responses))

    monkeypatch.setattr("meridian_expert.llm.client.time.sleep", lambda s: sleeps.append(s))
    profile = ModelProfile(alias="formatter", model="gpt-test", reasoning_effort="low")
    out = backend.generate_text(profile, "I", "B")

    assert out == "ok"
    assert sleeps == [1, 2]


def test_model_call_logging(tmp_path: Path) -> None:
    log_path = tmp_path / "task/logs/model_calls.jsonl"
    client = LLMClient(
        backend=DeterministicFakeBackend(),
        profiles=_profiles(),
        model_call_log_path=log_path,
    )

    _ = client.generate_text(
        "formatter",
        "Format",
        "text",
        metadata={"task_id": "T-20260415-0001", "cycle_id": "C01", "stage": "triage"},
    )
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["task_id"] == "T-20260415-0001"
    assert event["backend_kind"] == "fake"
    assert event["success"] is True


def test_backend_selection_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MERIDIAN_EXPERT_LLM_BACKEND", "fake")
    assert isinstance(_backend_from_settings(), DeterministicFakeBackend)


def test_openai_backend_uses_configured_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, float] = {}

    class FakeOpenAI:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout
            self.responses = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text="ok"))

    monkeypatch.setenv("MERIDIAN_EXPERT_LLM_BACKEND", "openai")
    monkeypatch.setenv("MERIDIAN_EXPERT_OPENAI_TIMEOUT_S", "10800")
    monkeypatch.setattr("meridian_expert.llm.client.OpenAI", FakeOpenAI)

    backend = _backend_from_settings()
    assert isinstance(backend, OpenAIResponsesBackend)
    assert captured["timeout"] == 10800.0


def test_streaming_surface() -> None:
    client = LLMClient(backend=DeterministicFakeBackend(), profiles=_profiles())
    chunks = list(client.stream_text("formatter", "fmt", "hello world"))
    assert "".join(chunks).strip() == "hello world"
