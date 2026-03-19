# QA Report

## Date
2026-03-19

## Executed Checks
- `python scripts/smoke_test.py` ✅
- `pytest -q` ✅ (3 passed)
- `ruff check app bridge tests` ✅
- `pip-audit -r requirements.txt -r dev-requirements.txt` ✅ (no known vulns)
- BotFather public endpoint check (`https://t.me/BotFather`) ✅ reachable and serving profile page

## Security Tool Note
- `bandit -r app bridge` failed due Python 3.14 compatibility issue in Bandit internals (`ast.Num` usage).
- Mitigation for this run: dependency vulnerability audit with `pip-audit`.
- Recommended CI hardening: run Bandit under Python 3.11 until upstream compatibility lands.
