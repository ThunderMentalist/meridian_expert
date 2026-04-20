from __future__ import annotations

from copy import deepcopy
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


def openai_response_schema(schema_model: type[BaseModel]) -> dict[str, Any]:
    schema = deepcopy(schema_model.model_json_schema())
    _ensure_object_additional_properties(schema)
    return schema


def _ensure_object_additional_properties(node: Any) -> None:
    if isinstance(node, dict):
        is_object_schema = node.get("type") == "object" or "properties" in node
        if is_object_schema and "additionalProperties" not in node:
            node["additionalProperties"] = False

        for key, value in node.items():
            if key in {"$defs", "definitions", "properties"} and isinstance(value, dict):
                for child in value.values():
                    _ensure_object_additional_properties(child)
                continue
            if key in {"items", "not", "if", "then", "else"}:
                _ensure_object_additional_properties(value)
                continue
            if key in {"anyOf", "oneOf", "allOf"} and isinstance(value, list):
                for child in value:
                    _ensure_object_additional_properties(child)
                continue
            if isinstance(value, (dict, list)):
                _ensure_object_additional_properties(value)
    elif isinstance(node, list):
        for item in node:
            _ensure_object_additional_properties(item)
