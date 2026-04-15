from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol

from openai import OpenAI
from pydantic import BaseModel

from meridian_expert.llm.profiles import ModelProfile, load_profiles
from meridian_expert.llm.structured import coerce_to_model
from meridian_expert.logging_utils import append_jsonl
from meridian_expert.settings import llm_backend_kind


class LLMBackend(Protocol):
    backend_kind: str

    def generate_text(self, profile: ModelProfile, instructions: str, input_text: str) -> str: ...

    def generate_structured(
        self,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        schema_model: type[BaseModel],
    ) -> BaseModel: ...

    def stream_text(self, profile: ModelProfile, instructions: str, input_text: str) -> Iterable[str]: ...


class OpenAIResponsesBackend:
    backend_kind = "openai"

    def __init__(self, *, client: OpenAI | None = None, max_attempts: int = 3, timeout_s: float = 30.0) -> None:
        self.client = client or OpenAI(timeout=timeout_s)
        self.max_attempts = max_attempts

    def _create_response(self, *, model: str, effort: str, instructions: str, input_text: str, stream: bool = False, text: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "reasoning": {"effort": effort},
                    "instructions": instructions,
                    "input": input_text,
                    "stream": stream,
                }
                if text:
                    kwargs["text"] = text
                return self.client.responses.create(**kwargs)
            except Exception as err:
                last_error = err
                if attempt == self.max_attempts - 1 or not _is_transient_error(err):
                    raise
                time.sleep(2**attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Response creation failed")

    def generate_text(self, profile: ModelProfile, instructions: str, input_text: str) -> str:
        resp = self._create_response(
            model=profile.model,
            effort=profile.reasoning_effort,
            instructions=instructions,
            input_text=input_text,
        )
        return getattr(resp, "output_text", "") or ""

    def generate_structured(
        self,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        schema_name = schema_model.__name__
        text = {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema_model.model_json_schema(),
            }
        }
        resp = self._create_response(
            model=profile.model,
            effort=profile.reasoning_effort,
            instructions=instructions,
            input_text=input_text,
            text=text,
        )
        payload_text = getattr(resp, "output_text", "") or "{}"
        payload = json.loads(payload_text)
        return coerce_to_model(schema_model, payload)

    def stream_text(self, profile: ModelProfile, instructions: str, input_text: str) -> Iterable[str]:
        stream = self._create_response(
            model=profile.model,
            effort=profile.reasoning_effort,
            instructions=instructions,
            input_text=input_text,
            stream=True,
        )
        for event in stream:
            delta = getattr(event, "delta", None)
            if delta:
                yield str(delta)


class DeterministicFakeBackend:
    backend_kind = "fake"

    def generate_text(self, profile: ModelProfile, instructions: str, input_text: str) -> str:
        alias = profile.alias
        lowered = input_text.lower()
        if alias == "formatter":
            return input_text.strip()
        if alias in {"theory", "usage", "updates"}:
            title = alias.capitalize()
            risk = "high" if "risk" in lowered else "normal"
            return f"## {title} response\n\n- Summary: deterministic draft\n- Risk: {risk}\n- Evidence: {input_text[:180]}"
        return f"[{alias}] {instructions[:60]} :: {input_text[:200]}"

    def generate_structured(
        self,
        profile: ModelProfile,
        instructions: str,
        input_text: str,
        schema_model: type[BaseModel],
    ) -> BaseModel:
        alias = profile.alias
        lowered = input_text.lower()
        payload: dict[str, Any]
        fields = schema_model.model_fields

        if alias == "triage":
            family = "clarification" if any(k in lowered for k in ["unclear", "clarify", "ambiguous"]) else "theory"
            payload = _payload_for_fields(
                fields,
                {
                    "task_family": family,
                    "confidence": 0.8,
                    "rationale": "Deterministic triage from keyword rules.",
                    "needs_clarification": family == "clarification",
                },
            )
        elif alias == "reviewer":
            has_content = bool(input_text.strip())
            has_evidence = "evidence" in lowered or "source" in lowered
            approved = has_content and has_evidence
            payload = _payload_for_fields(
                fields,
                {
                    "approved": approved,
                    "status": "approve" if approved else "revise",
                    "issues": [] if approved else ["Missing evidence or empty answer."],
                    "notes": "Deterministic reviewer decision.",
                    "suggested_edits": [] if approved else ["Add concrete evidence references."],
                },
            )
        else:
            payload = _payload_for_fields(
                fields,
                {"result": self.generate_text(profile, instructions, input_text), "confidence": 0.7},
            )

        return coerce_to_model(schema_model, payload)

    def stream_text(self, profile: ModelProfile, instructions: str, input_text: str) -> Iterable[str]:
        text = self.generate_text(profile, instructions, input_text)
        for token in text.split(" "):
            yield f"{token} "


class LLMClient:
    def __init__(
        self,
        *,
        backend: LLMBackend | None = None,
        profiles: dict[str, ModelProfile] | None = None,
        model_call_log_path: Path | None = None,
    ) -> None:
        self.profiles = profiles or load_profiles()
        self.backend = backend or _backend_from_settings()
        self.model_call_log_path = model_call_log_path

    def generate_text(
        self,
        alias: str,
        instructions: str,
        input_text: str,
        *,
        stream: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if stream:
            return "".join(self.stream_text(alias, instructions, input_text, metadata=metadata))
        return self._call_with_logging(
            call_kind="text",
            alias=alias,
            metadata=metadata,
            fn=lambda profile: self.backend.generate_text(profile, instructions, input_text),
        )

    def generate_structured(
        self,
        alias: str,
        instructions: str,
        input_text: str,
        schema_model: type[BaseModel],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> BaseModel:
        return self._call_with_logging(
            call_kind="structured",
            alias=alias,
            metadata=metadata,
            fn=lambda profile: self.backend.generate_structured(profile, instructions, input_text, schema_model),
        )

    def stream_text(
        self,
        alias: str,
        instructions: str,
        input_text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        return self._call_with_logging(
            call_kind="stream",
            alias=alias,
            metadata=metadata,
            fn=lambda profile: _consume_stream(self.backend.stream_text(profile, instructions, input_text)),
        )

    def _call_with_logging(self, *, call_kind: str, alias: str, metadata: dict[str, Any] | None, fn: Any) -> Any:
        profile = self.profiles[alias]
        start = time.perf_counter()
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": (metadata or {}).get("task_id"),
            "cycle_id": (metadata or {}).get("cycle_id"),
            "stage": (metadata or {}).get("stage"),
            "prompt_spec_name": (metadata or {}).get("prompt_spec_name"),
            "alias": alias,
            "resolved_model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "backend_kind": self.backend.backend_kind,
            "call_kind": call_kind,
            "success": False,
        }
        try:
            out = fn(profile)
            event["success"] = True
            return out
        except Exception as err:
            event["error_type"] = type(err).__name__
            raise
        finally:
            event["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            self._write_log(event, metadata=metadata)

    def _write_log(self, event: dict[str, Any], *, metadata: dict[str, Any] | None = None) -> None:
        if metadata and metadata.get("model_call_log_path"):
            path = Path(str(metadata["model_call_log_path"]))
        elif self.model_call_log_path is not None:
            path = self.model_call_log_path
        elif metadata and metadata.get("task_dir"):
            path = Path(str(metadata["task_dir"])) / "logs" / "model_calls.jsonl"
        else:
            return
        append_jsonl(path, event)


def _consume_stream(parts: Iterable[str]) -> Iterator[str]:
    for p in parts:
        yield p


def _payload_for_fields(fields: dict[str, Any], preferred: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for name, field in fields.items():
        if name in preferred:
            payload[name] = preferred[name]
        elif field.default is not None:
            payload[name] = field.default
        else:
            payload[name] = _default_for_annotation(field.annotation)
    return payload


def _default_for_annotation(annotation: Any) -> Any:
    origin = getattr(annotation, "__origin__", None)
    if annotation is bool:
        return False
    if annotation in (int, float):
        return 0
    if annotation is str:
        return ""
    if origin is list or annotation is list:
        return []
    if origin is dict or annotation is dict:
        return {}
    return None


def _is_transient_error(err: Exception) -> bool:
    name = type(err).__name__.lower()
    if any(t in name for t in ("timeout", "ratelimit", "apierror", "connection", "unavailable")):
        return True
    status = getattr(err, "status_code", None)
    return status in {408, 409, 429, 500, 502, 503, 504}


def _backend_from_settings() -> LLMBackend:
    kind = llm_backend_kind()
    if kind == "fake":
        return DeterministicFakeBackend()
    return OpenAIResponsesBackend()
