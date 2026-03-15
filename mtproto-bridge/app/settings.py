import os


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


class Settings:
    def __init__(self) -> None:
        api_id = _get_env("API_ID")
        api_hash = _get_env("API_HASH")
        phone = _get_env("PHONE")
        session_string = _get_env("SESSION_STRING")

        if not api_id or not api_hash:
            missing = [k for k, v in {"API_ID": api_id, "API_HASH": api_hash}.items() if not v]
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

        if not session_string and not phone:
            raise RuntimeError("Missing required env var: PHONE (or provide SESSION_STRING)")

        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.phone = phone
        self.session_string = session_string

        self.session_name = _get_env("SESSION_NAME", "/data/mtproto")
        self.request_min_interval = float(_get_env("REQUEST_MIN_INTERVAL", "0.7"))
        self.log_level = _get_env("LOG_LEVEL", "info")


settings = Settings()
