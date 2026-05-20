# Contributing to Vision

Vision is a solo-developer portfolio project. External contributions aren't expected, but the repo is public so others can read it. This file documents how the project is built locally.

## Local development quickstart

Install [uv](https://docs.astral.sh/uv/) (Linux/macOS):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sync the project environment from `pyproject.toml` + `uv.lock`:

```bash
uv sync
```

Run the quality gates (lint, type-check, tests):

```bash
uv run ruff check . && uv run mypy lib tests && uv run pytest -q
```

## Repo conventions

- Python 3.12 only (MediaPipe has no 3.13 wheels as of 2026-05).
- All linting, type-checking, and tests go through `uv run`. Don't use the system Python.
- Filename and code conventions are tracked in `CLAUDE.md` and inherited from `.planning/research/STACK.md`.

## Never commit secrets

- Service-account JSON files: never. ADC via `gcloud auth application-default login` is the only auth path in v1 (D-11).
- `.env` files: never. Use `scripts/bootstrap-gcp.env.example` as the template; copy to `scripts/bootstrap-gcp.env` locally (gitignored).
- Raw `.fit`, `.tcx`, `.gpx` ride files: never. They often contain GPS home coordinates.
- If you've accidentally committed a secret: rotate the credential immediately, then use `git filter-repo` or BFG to scrub history. Force-push only after coordinating.

## Bug reports and issues

Open a GitHub issue; this is a portfolio project, response time is best-effort.
