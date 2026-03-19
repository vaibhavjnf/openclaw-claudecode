from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

DEFAULT_ENV = {
    "OPENCLAW_HOME": "/opt/openclaw",
    "OPENCLAW_SESSION_NAME": "openclaw",
    "CLAUDE_CMD": "claude",
    "LOG_LEVEL": "INFO",
    "TELEGRAM_BOT_TOKEN": "",
    "AUTHORIZED_TELEGRAM_USER_IDS": "",
    "ADMIN_CHAT_IDS": "",
    "TELEGRAM_POLL_TIMEOUT": "2",
    "MESSAGE_MAX_CHARS": "3000",
    "COMMAND_QUEUE_MAX_SIZE": "100",
    "PER_USER_MSGS_PER_MIN": "12",
    "RELAY_CHUNK_CHARS": "3500",
    "RELAY_POLL_INTERVAL_SEC": "0.5",
    "RETRIEVAL_TOP_K": "5",
    "BRIDGE_HEARTBEAT_STALE_SEC": "120",
    "SCHEDULER_HEARTBEAT_STALE_SEC": "180",
    "WATCHDOG_INTERVAL_SEC": "15",
    "RUNTIME_SERVICE_NAME": "openclaw-runtime.service",
    "BRIDGE_SERVICE_NAME": "openclaw-bridge.service",
    "SCHEDULER_SERVICE_NAME": "openclaw-scheduler.service",
}


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = []
    for key in DEFAULT_ENV:
        lines.append(f"{key}={values.get(key, DEFAULT_ENV[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prompt(current: str, label: str, required: bool = False) -> str:
    while True:
        value = input(f"{label} [{current}]: ").strip()
        if value:
            return value
        if current:
            return current
        if not required:
            return ""
        print("This value is required.")


def cmd_init(root: Path) -> int:
    env_example = root / ".env.example"
    env_path = root / ".env"
    if not env_path.exists() and env_example.exists():
        shutil.copy2(env_example, env_path)

    current = {**DEFAULT_ENV, **parse_env_file(env_path)}

    print("OpenClaw onboarding")
    print("Press enter to keep defaults.\n")
    current["OPENCLAW_HOME"] = prompt(current["OPENCLAW_HOME"], "OPENCLAW_HOME", required=True)
    current["OPENCLAW_SESSION_NAME"] = prompt(
        current["OPENCLAW_SESSION_NAME"], "OPENCLAW_SESSION_NAME", required=True
    )
    current["CLAUDE_CMD"] = prompt(current["CLAUDE_CMD"], "CLAUDE_CMD", required=True)
    current["TELEGRAM_BOT_TOKEN"] = prompt(
        current["TELEGRAM_BOT_TOKEN"], "TELEGRAM_BOT_TOKEN", required=True
    )
    current["AUTHORIZED_TELEGRAM_USER_IDS"] = prompt(
        current["AUTHORIZED_TELEGRAM_USER_IDS"], "AUTHORIZED_TELEGRAM_USER_IDS", required=True
    )
    current["ADMIN_CHAT_IDS"] = prompt(
        current["ADMIN_CHAT_IDS"] or current["AUTHORIZED_TELEGRAM_USER_IDS"],
        "ADMIN_CHAT_IDS",
        required=True,
    )
    write_env_file(env_path, current)

    auth_ids = [
        int(v.strip())
        for v in current["AUTHORIZED_TELEGRAM_USER_IDS"].split(",")
        if v.strip().isdigit()
    ]
    auth_path = root / "config" / "authorized_users.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(
        json.dumps({"authorized_user_ids": auth_ids}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {env_path}")
    print(f"Wrote {auth_path}")
    return 0


def _run_check(cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
            timeout=8,
        )
        ok = proc.returncode == 0
        output = (proc.stdout or proc.stderr).strip()
        return ok, output or f"exit={proc.returncode}"
    except Exception as exc:
        return False, str(exc)


def _check_telegram_token(token: str) -> tuple[bool, str]:
    if not token:
        return False, "TELEGRAM_BOT_TOKEN missing"
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ok = bool(data.get("ok"))
            if ok:
                name = data.get("result", {}).get("username", "unknown")
                return True, f"ok ({name})"
            return False, json.dumps(data)[:200]
    except Exception as exc:
        return False, str(exc)


def cmd_doctor(root: Path) -> int:
    env = parse_env_file(root / ".env")
    checks = [
        ("python3", ["python3", "--version"]),
        ("tmux", ["tmux", "-V"]),
        ("systemctl", ["systemctl", "--version"]),
        ("claude", [env.get("CLAUDE_CMD", "claude"), "--version"]),
    ]
    failed = 0
    print("OpenClaw doctor\n")
    for name, cmd in checks:
        ok, out = _run_check(cmd)
        status = "OK" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{status}] {name}: {out}")

    tok_ok, tok_msg = _check_telegram_token(env.get("TELEGRAM_BOT_TOKEN", ""))
    print(f"[{'OK' if tok_ok else 'FAIL'}] telegram: {tok_msg}")
    if not tok_ok:
        failed += 1

    if failed:
        print(f"\nDoctor found {failed} issue(s).")
        return 1
    print("\nAll checks passed.")
    return 0


def cmd_print_env(root: Path) -> int:
    env = parse_env_file(root / ".env")
    safe = dict(env)
    token = safe.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        safe["TELEGRAM_BOT_TOKEN"] = token[:8] + "..."
    print(json.dumps(safe, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw onboarding CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Interactive setup for .env and authorized users")
    sub.add_parser("doctor", help="Validate runtime dependencies and bot token")
    sub.add_parser("print-env", help="Print loaded env values (masked token)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    if args.cmd == "init":
        return cmd_init(root)
    if args.cmd == "doctor":
        return cmd_doctor(root)
    if args.cmd == "print-env":
        return cmd_print_env(root)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
