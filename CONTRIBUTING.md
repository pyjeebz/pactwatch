# Contributing to breakwatch

Thanks for your interest in contributing. This document covers what you need to get a dev environment running and how to land a change.

## Dev setup

```bash
git clone https://github.com/pyjeebz/breakwatch.git
cd breakwatch
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

Run the CLI against the demo monorepo:

```bash
breakwatch check \
  --config examples/demo-monorepo/breakwatch.yaml \
  --producer user-api \
  --old examples/demo-monorepo/services/producer-api/openapi.yaml \
  --new examples/demo-monorepo/services/producer-api/openapi-breaking.yaml
```

## Project layout

The CLI lives in [src/breakwatch/](src/breakwatch/):

- `cli.py` — Typer entry points (`diff`, `check`)
- `loader.py` — OpenAPI spec loader (resolves `$ref` via prance)
- `diff.py` — structural diff engine producing `Change` records
- `classifier.py` — labels each change BREAKING / RISKY / SAFE
- `graph.py` + `filter.py` — consumer graph loader and per-consumer filtering
- `formatters/` — text, json, markdown output adapters
- `action.py` — GitHub Action entry point (PR comments + status checks)

## Adding a format adapter

breakwatch is OpenAPI 3.x today. The adapter architecture is open for AsyncAPI, GraphQL, and Protobuf contributions. The loader → diff → classifier pipeline is intentionally agnostic of the source format — `loader.py` returns a normalized dict and the rest of the pipeline operates on it. To add a new format, write a new loader module and wire it through `cli.py` based on file extension or an explicit flag.

If you're starting an adapter, please open an issue first so we can align on the normalization shape before you write code.

## Pull requests

- Match the existing commit style: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- Add tests for new behavior — every classifier rule and every diff path has a test
- Run `pytest` before pushing
- Keep PRs focused; one concern per branch

## License

By contributing you agree your work is licensed under the Apache 2.0 license that covers this project.
