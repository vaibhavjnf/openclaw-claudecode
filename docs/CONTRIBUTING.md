# Contributing

## Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m compileall app bridge
```

## Style
- Keep dependencies minimal.
- Prioritize reliability and operational clarity.
- Add comments only where logic is not obvious.

## PR Checklist
1. `python -m compileall app bridge` passes.
2. README/docs updated for behavior changes.
3. No secrets committed.
4. New config keys reflected in `.env.example`.
