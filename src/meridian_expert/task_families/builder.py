def ensure_enabled(enabled: bool) -> None:
    if not enabled:
        raise RuntimeError("Builder path is disabled unless explicit")
