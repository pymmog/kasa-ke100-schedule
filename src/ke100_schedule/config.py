"""Load hub credentials from environment variables or a local TOML file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "ke100-schedule" / "config.toml"

REQUIRED_ENV = ("KASA_HOST", "KASA_USERNAME", "KASA_PASSWORD")


@dataclass(frozen=True)
class HubCredentials:
    host: str
    username: str
    password: str


def _load_toml(path: Path) -> dict[str, str]:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with path.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config file: {path}")
    return {str(k): v for k, v in data.items() if isinstance(v, str)}


def load_credentials(config_path: Path | None = None) -> HubCredentials:
    """Resolve credentials: env vars override config file values."""
    path = config_path or CONFIG_PATH
    file_vals: dict[str, str] = {}
    if path.is_file():
        file_vals = _load_toml(path)

    def get(key: str, file_key: str) -> str | None:
        env_key = f"KASA_{key}" if key != "HOST" else "KASA_HOST"
        if key == "HOST":
            return os.environ.get("KASA_HOST") or file_vals.get("host")
        if key == "USERNAME":
            return os.environ.get("KASA_USERNAME") or file_vals.get("username")
        if key == "PASSWORD":
            return os.environ.get("KASA_PASSWORD") or file_vals.get("password")
        return os.environ.get(env_key) or file_vals.get(file_key)

    host = get("HOST", "host")
    username = get("USERNAME", "username")
    password = get("PASSWORD", "password")

    missing = []
    if not host:
        missing.append("KASA_HOST (or host in config)")
    if not username:
        missing.append("KASA_USERNAME (or username in config)")
    if not password:
        missing.append("KASA_PASSWORD (or password in config)")
    if missing:
        raise SystemExit(
            "Missing credentials: "
            + ", ".join(missing)
            + f". Set env vars or create {CONFIG_PATH} (see config.example.toml)."
        )

    return HubCredentials(host=host, username=username, password=password)
