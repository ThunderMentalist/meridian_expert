from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def validate(model: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    return model.model_validate(payload)


def coerce_to_model(model: type[BaseModel], payload: dict[str, Any] | BaseModel) -> BaseModel:
    if isinstance(payload, BaseModel):
        if isinstance(payload, model):
            return payload
        return model.model_validate(payload.model_dump())
    return validate(model, payload)
