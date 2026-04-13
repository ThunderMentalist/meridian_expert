from pydantic import BaseModel


def validate(model: type[BaseModel], payload: dict) -> BaseModel:
    return model.model_validate(payload)
