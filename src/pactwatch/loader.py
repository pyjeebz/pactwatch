"""Spec loader — parse OpenAPI specs and resolve $ref chains."""

from __future__ import annotations

import json
from pathlib import Path

import prance
import yaml


class SpecLoadError(Exception):
    """Raised when a spec file cannot be loaded or is invalid."""


def load_spec(path: Path | str) -> dict:
    """Load and fully resolve an OpenAPI spec from a YAML or JSON file.

    Uses prance.ResolvingParser to chase every $ref down to a plain dict.
    Validates that the result looks like an OpenAPI 3.x spec.

    Args:
        path: Path to the OpenAPI spec file (YAML or JSON).

    Returns:
        Fully resolved spec as a plain dict.

    Raises:
        SpecLoadError: If the file is missing, unparseable, or not OpenAPI 3.x.
    """
    path = Path(path)

    if not path.exists():
        raise SpecLoadError(f"Spec file not found: {path}")

    if not path.is_file():
        raise SpecLoadError(f"Not a file: {path}")

    try:
        parser = prance.ResolvingParser(
            str(path),
            strict=False,
            backend="openapi-spec-validator",
        )
        spec = parser.specification
    except prance.ValidationError as exc:
        raise SpecLoadError(f"Invalid OpenAPI spec: {exc}") from exc
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise SpecLoadError(f"Failed to parse spec file: {exc}") from exc
    except Exception as exc:
        raise SpecLoadError(f"Failed to load spec: {exc}") from exc

    # Ensure it's OpenAPI 3.x
    openapi_version = spec.get("openapi", "")
    if not openapi_version.startswith("3."):
        raise SpecLoadError(
            f"Unsupported OpenAPI version: {openapi_version!r}. "
            "PactWatch requires OpenAPI 3.x."
        )

    return spec
