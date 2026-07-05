# Contributing to DICE

Thanks for helping improve DICE.

## Development Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Before Opening a PR

Run:

```powershell
python -m pytest
python -m compileall src tests
```

## Contribution Guidelines

- Keep job logic in plugins, not in the manager or UI.
- Keep chain-specific behavior in adapters.
- Do not log private keys, signed raw transactions, RPC secrets, or decrypted secrets.
- Prefer small, focused PRs.
- Add tests for new workflow, registry, storage, or execution behavior.

## License

Unless explicitly stated otherwise, contributions are submitted under the Apache License 2.0.
