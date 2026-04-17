# Model routing and OpenAI

## Semantic model aliases

Model profiles are loaded from `config/model_profiles.yaml` by alias, including:

- `router`, `triage`, `theory`, `usage`, `updates`, `reviewer`, `formatter`
- scaffolded but disabled: `builder_spec`, `builder_codegen`

Each alias resolves to a model name plus reasoning effort.

## Backend selection

`MERIDIAN_EXPERT_LLM_BACKEND` selects backend:

- `openai` (default): uses OpenAI Responses API backend
- `fake`: deterministic offline backend for tests and notebooks

The fake backend provides stable text + structured outputs and supports deterministic streaming.

## OpenAI Responses path

The OpenAI backend uses `client.responses.create(...)` with:

- model from alias profile
- reasoning effort from profile
- instructions + input text
- request timeout defaulting to `10800` seconds (3 hours)
- retry on transient errors

Timeout can be configured with `MERIDIAN_EXPERT_OPENAI_TIMEOUT_S`; invalid/non-positive values fall back to `10800`.

Structured calls request JSON schema output and are validated/coerced into Pydantic models.

## Structured outputs

Review and triage paths consume structured Pydantic outputs rather than untyped text where possible. The client validates/coerces structured payloads into schema models before returning data to orchestration.

## Streaming

Text generation supports stream mode:

- backend returns token deltas
- client consumes and joins stream events
- call metadata is logged the same way as non-stream calls

## Model-call logging

Each call can be logged as JSONL with metadata including:

- timestamp
- task/cycle/stage identifiers
- prompt spec name
- alias and resolved model
- reasoning effort
- backend kind
- call kind (`text`, `structured`, `stream`)
- success/failure and error type

This keeps model behavior auditable during prototype iterations.
