"""
Run once to generate SESSION_STRING for non-interactive server deployment.

Usage (inside Docker):
    docker compose -p localai run --rm mtproto-bridge python scripts/generate_session.py

Copy the printed string into MTBRIDGE_SESSION_STRING in your .env file.
"""
import os
from pyrogram import Client


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value


def main() -> None:
    api_id = int(_env("API_ID"))
    api_hash = _env("API_HASH")
    phone = _env("PHONE")

    with Client(name=":memory:", api_id=api_id, api_hash=api_hash, phone_number=phone) as app:
        session_string = app.export_session_string()

    print("\n=== SESSION STRING (copy to .env as MTBRIDGE_SESSION_STRING) ===")
    print(session_string)
    print("=================================================================\n")


if __name__ == "__main__":
    main()
