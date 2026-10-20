import pytest

from jaffle_shop_core_v2.keys import load_env_file, resolve_api_key


def test_resolve_api_key_prefers_jev_over_typesafe() -> None:
    assert resolve_api_key({"JEV_API_KEY": "jev", "TYPESAFE_API_KEY": "ts"}) == "jev"
    assert resolve_api_key({"TYPESAFE_API_KEY": "ts"}) == "ts"


def test_resolve_api_key_requires_a_value() -> None:
    with pytest.raises(ValueError, match="JEV_API_KEY"):
        resolve_api_key({})


def test_load_env_file_skips_missing_path(tmp_path) -> None:
    load_env_file(tmp_path / "no-such.env")


def test_load_env_file_accepts_export_prefix(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('export JEV_API_KEY="from-file"\n', encoding="utf-8")
    loaded: dict[str, str] = {}
    load_env_file(env_file, environ=loaded)
    assert resolve_api_key(loaded) == "from-file"
