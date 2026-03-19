from __future__ import annotations

from app.onboarding_cli import parse_env_file, write_env_file


def test_env_round_trip(tmp_path):
    env_path = tmp_path / ".env"
    write_env_file(
        env_path,
        {
            "OPENCLAW_HOME": "/opt/openclaw",
            "TELEGRAM_BOT_TOKEN": "123:abc",
            "AUTHORIZED_TELEGRAM_USER_IDS": "1,2",
        },
    )
    data = parse_env_file(env_path)
    assert data["OPENCLAW_HOME"] == "/opt/openclaw"
    assert data["TELEGRAM_BOT_TOKEN"] == "123:abc"
    assert data["AUTHORIZED_TELEGRAM_USER_IDS"] == "1,2"
