"""Persona loader — resolves persona from catalog, YAML file, or inline overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ux_pilot.personas.catalog import (
    CATALOG,
    PersonaTemplate,
    get_persona_by_index,
    get_persona_by_name,
)
from ux_pilot.personas.traits import validate_traits


def load_persona(
    name: str | None = None,
    persona_file: str | None = None,
    trait_overrides: list[str] | None = None,
) -> PersonaTemplate:
    """Resolve a persona from multiple sources.

    Priority: persona_file > name (catalog lookup) > default.
    Trait overrides (--trait key=value) are applied on top.
    """
    if persona_file:
        template = _load_from_yaml(persona_file)
    elif name:
        template = _resolve_from_catalog(name)
    else:
        # Default: balanced user
        template = PersonaTemplate(
            name="Default User",
            description="A balanced user with average traits across all dimensions.",
            category="General",
            traits={t: 50 for t in [
                "openness", "conscientiousness", "extraversion", "agreeableness",
                "neuroticism", "tech_literacy", "decision_speed", "attention_span",
                "price_sensitivity",
            ]},
        )

    # Apply trait overrides
    if trait_overrides:
        traits = dict(template.traits)
        for override in trait_overrides:
            if "=" not in override:
                raise ValueError(f"Invalid trait override '{override}'. Use format: trait_name=value")
            key, val = override.split("=", 1)
            key = key.strip()
            try:
                traits[key] = int(val.strip())
            except ValueError:
                raise ValueError(f"Trait value must be an integer: '{override}'")
        validated = validate_traits(traits)
        template = PersonaTemplate(
            name=template.name,
            description=template.description,
            category=template.category,
            traits=validated,
            demographics=template.demographics,
            goals=list(template.goals),
            accessibility_needs=list(template.accessibility_needs),
        )

    return template


def _resolve_from_catalog(name: str) -> PersonaTemplate:
    """Look up persona by name or index number."""
    # Try as index first
    try:
        idx = int(name)
        result = get_persona_by_index(idx)
        if result:
            return result
        raise ValueError(f"Persona index {idx} out of range (1-{len(CATALOG)})")
    except ValueError:
        pass

    result = get_persona_by_name(name)
    if result:
        return result

    available = ", ".join(f'"{p.name}"' for p in CATALOG)
    raise ValueError(f"Persona '{name}' not found. Available: {available}")


def _load_from_yaml(path: str) -> PersonaTemplate:
    """Load persona definition from a YAML file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    with open(filepath) as f:
        data: dict[str, Any] = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        raise ValueError(f"Invalid persona file: {path}")

    name = data.get("name", filepath.stem)
    traits = validate_traits(data.get("traits", {}))

    return PersonaTemplate(
        name=name,
        description=data.get("description", "Custom persona"),
        category=data.get("category", "Custom"),
        traits=traits,
        demographics=data.get("demographics", {}),
        goals=data.get("goals", []),
        accessibility_needs=data.get("accessibility_needs", []),
    )
