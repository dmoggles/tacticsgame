from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..models.ability import Ability
from . import resolution

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "abilities.yaml"

_VALID_ATTRIBUTES = {"might", "focus", "resolve", "agility"}
_VALID_KINDS = {"damage", "heal"}
_VALID_APPLIES_TO = {"target", "caster"}
_PROFILE_FIELDS = (
    "base_flat",
    "base_per_attack",
    "baseline_quality",
    "margin_sensitivity",
    "quality_floor",
    "quality_cap",
)

_cache: dict[str, Ability] | None = None  # ability id -> Ability


def load_abilities() -> list[Ability]:
    """Every ability defined in data/abilities.yaml, freshly loaded once
    and shared thereafter (Ability is frozen/stateless, safe to share)."""
    return list(_load_by_id().values())


def load_ability_ids() -> dict[str, str]:
    """Ability id -> display name, for cross-referencing from
    class_track_library.py (which only knows ids, not the built objects)."""
    return {ability_id: ability.name for ability_id, ability in _load_by_id().items()}


def _load_by_id() -> dict[str, Ability]:
    global _cache
    if _cache is None:
        _cache = _load()
    return _cache


def _load() -> dict[str, Ability]:
    with _DATA_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    profiles = _build_damage_profiles(data.get("damage_profiles") if isinstance(data, dict) else None)
    raw_abilities = data.get("abilities") if isinstance(data, dict) else None
    if not isinstance(raw_abilities, list) or not raw_abilities:
        raise ValueError(f"{_DATA_PATH}: expected a non-empty top-level 'abilities' list")

    abilities: dict[str, Ability] = {}
    for entry in raw_abilities:
        if not isinstance(entry, dict):
            raise ValueError(f"{_DATA_PATH}: each ability entry must be a mapping")
        ability_id = _require_str(entry, "id", context="<ability>")
        if ability_id in abilities:
            raise ValueError(f"{_DATA_PATH}: duplicate ability id '{ability_id}'")
        abilities[ability_id] = _build_ability(ability_id, entry, profiles)
    return abilities


def _build_damage_profiles(raw_profiles: Any) -> dict[str, resolution.DamageProfile]:
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ValueError(f"{_DATA_PATH}: expected a non-empty top-level 'damage_profiles' mapping")

    profiles: dict[str, resolution.DamageProfile] = {}
    for profile_name, raw_profile in raw_profiles.items():
        if not isinstance(profile_name, str) or not profile_name:
            raise ValueError(f"{_DATA_PATH}: damage profile names must be non-empty strings")
        profiles[profile_name] = _build_damage_profile(
            f"damage profile '{profile_name}'", raw_profile
        )
    return profiles


def _build_damage_profile(context: str, raw: Any) -> resolution.DamageProfile:
    if not isinstance(raw, dict):
        raise ValueError(f"{_DATA_PATH}: {context} must be a mapping")
    values = {
        field: float(_require(raw, field, (int, float), context=context))
        for field in _PROFILE_FIELDS
    }
    if values["base_flat"] < 0 or values["base_per_attack"] < 0:
        raise ValueError(f"{_DATA_PATH}: {context} base terms must be non-negative")
    if values["quality_floor"] <= 0 or values["quality_cap"] < values["quality_floor"]:
        raise ValueError(f"{_DATA_PATH}: {context} has an invalid quality floor/cap")
    return resolution.DamageProfile(**values)


def _build_ability(
    ability_id: str, entry: dict[str, Any], profiles: dict[str, resolution.DamageProfile] | None = None
) -> Ability:
    name = _require_str(entry, "name", context=ability_id)
    targets_ally = _require(entry, "targets_ally", bool, context=ability_id)
    range_ = _require(entry, "range", int, context=ability_id)
    min_range = int(entry.get("min_range", 0))
    cooldown = int(entry.get("cooldown", 0))
    raw_cost = entry.get("cost")
    cost = int(raw_cost) if raw_cost is not None else None

    raw_effect = entry.get("effect")
    if raw_effect is None:
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' is missing 'effect'")
    if isinstance(raw_effect, dict):
        raw_effect = [raw_effect]
    if not isinstance(raw_effect, list) or not raw_effect:
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' has an invalid 'effect'")

    components = [_build_component(ability_id, component, profiles) for component in raw_effect]

    return Ability(
        name=name,
        range=range_,
        targets_ally=targets_ally,
        effect=resolution.make_effect(components),
        cost=cost,
        min_range=min_range,
        cooldown=cooldown,
    )


def _build_component(
    ability_id: str, raw: Any, profiles: dict[str, resolution.DamageProfile] | None = None
) -> resolution.EffectComponent:
    if not isinstance(raw, dict):
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' has a non-mapping effect entry")
    kind = _require_str(raw, "kind", context=ability_id)
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"{_DATA_PATH}: ability '{ability_id}' has unknown effect kind '{kind}' "
            f"(expected one of {sorted(_VALID_KINDS)})"
        )
    base = _require(raw, "base", (int, float), context=ability_id)
    verb = _require_str(raw, "verb", context=ability_id)
    applies_to = raw.get("applies_to", "target")
    if applies_to not in _VALID_APPLIES_TO:
        raise ValueError(
            f"{_DATA_PATH}: ability '{ability_id}' has unknown applies_to '{applies_to}' "
            f"(expected one of {sorted(_VALID_APPLIES_TO)})"
        )

    raw_scaling = raw.get("scaling", [])
    if not isinstance(raw_scaling, list):
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' has a non-list 'scaling'")
    scaling = [_build_scaling_term(ability_id, term) for term in raw_scaling]
    contested = raw.get("contested", True)
    if not isinstance(contested, bool):
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' field 'contested' must be bool")
    automatic_variance_width = raw.get("automatic_variance_width", 0.0)
    if not isinstance(automatic_variance_width, (int, float)) or automatic_variance_width < 0:
        raise ValueError(
            f"{_DATA_PATH}: ability '{ability_id}' field 'automatic_variance_width' "
            "must be a non-negative number"
        )

    profile: resolution.DamageProfile | None = None
    if profiles is not None:
        profile_name = _require_str(raw, "profile", context=ability_id)
        if profile_name not in profiles:
            raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' references unknown profile '{profile_name}'")
        profile = _profile_with_overrides(ability_id, profiles[profile_name], raw.get("profile_overrides"))
    elif "profile" in raw:
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' needs loaded damage profiles")

    if kind == "damage" and contested:
        try:
            resolution.primary_attack_attribute(scaling)
        except ValueError as error:
            raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' has invalid attack scaling: {error}") from error

    return resolution.EffectComponent(
        kind=kind,
        base=float(base),
        scaling=scaling,
        verb=verb,
        applies_to=applies_to,
        contested=contested,
        profile=profile,
        automatic_variance_width=float(automatic_variance_width),
    )


def _profile_with_overrides(
    ability_id: str, profile: resolution.DamageProfile, raw_overrides: Any
) -> resolution.DamageProfile:
    if raw_overrides is None:
        return profile
    if not isinstance(raw_overrides, dict):
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' profile_overrides must be a mapping")
    unknown_fields = set(raw_overrides) - set(_PROFILE_FIELDS)
    if unknown_fields:
        raise ValueError(
            f"{_DATA_PATH}: ability '{ability_id}' has unknown profile override(s): "
            f"{sorted(unknown_fields)}"
        )
    values = {field: getattr(profile, field) for field in _PROFILE_FIELDS}
    for field, value in raw_overrides.items():
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"{_DATA_PATH}: ability '{ability_id}' profile override '{field}' must be numeric"
            )
        values[field] = float(value)
    return _build_damage_profile(f"ability '{ability_id}' profile override", values)


def _build_scaling_term(ability_id: str, raw: Any) -> resolution.ScalingTerm:
    if not isinstance(raw, dict):
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' has a non-mapping scaling term")
    attribute = _require_str(raw, "attribute", context=ability_id)
    if attribute not in _VALID_ATTRIBUTES:
        raise ValueError(
            f"{_DATA_PATH}: ability '{ability_id}' has unknown scaling attribute "
            f"'{attribute}' (expected one of {sorted(_VALID_ATTRIBUTES)})"
        )
    multiplier = _require(raw, "multiplier", (int, float), context=ability_id)
    return resolution.ScalingTerm(attribute=attribute, multiplier=float(multiplier))


def _require(
    entry: dict[str, Any], key: str, expected_type: type | tuple[type, ...], *, context: str
) -> Any:
    if key not in entry:
        raise ValueError(f"{_DATA_PATH}: '{context}' is missing required field '{key}'")
    value = entry[key]
    if not isinstance(value, expected_type):
        raise ValueError(
            f"{_DATA_PATH}: '{context}' field '{key}' must be {expected_type}, "
            f"got {type(value).__name__}"
        )
    return value


def _require_str(entry: dict[str, Any], key: str, *, context: str) -> str:
    value = _require(entry, key, str, context=context)
    assert isinstance(value, str)
    return value
