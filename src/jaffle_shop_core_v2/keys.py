import os
from collections.abc import Mapping, MutableMapping
from pathlib import Path

DEFAULT_ENV_FILE = Path(".env")


def load_env_file(
    path: Path = DEFAULT_ENV_FILE,
    environ: MutableMapping[str, str] | None = None,
) -> None:
    env = os.environ if environ is None else environ
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        value = value.strip().strip('"').strip("'")
        env.setdefault(key, value)


def resolve_api_key(environ: Mapping[str, str] | None = None) -> str:
    if environ is None:
        load_env_file()
        env = os.environ
    else:
        env = environ
    key = env.get("JEV_API_KEY") or env.get("TYPESAFE_API_KEY")
    if not key:
        raise ValueError("Set JEV_API_KEY or TYPESAFE_API_KEY")
    return key
