from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CanonProfile, CharacterState


SCHEMA = "character-canon-contract/1"
FEATURE_ALIASES = {
    "eye_shape": "eyes",
    "default_clothing": "clothing",
}


def _feature_name(name: str) -> str:
    return FEATURE_ALIASES.get(name, name)


def load_contract(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(raw)
    return raw


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != SCHEMA:
        raise ValueError(f"unsupported Canon contract schema: {contract.get('schema_version')!r}")
    provenance = contract.get("provenance", {})
    if provenance.get("contains_novel_passages") is not False:
        raise ValueError("Canon contract must be passage-free")
    character = contract.get("character", {})
    if not character.get("name"):
        raise ValueError("Canon contract is missing character.name")

    unresolved = {_feature_name(name) for name in contract.get("unresolved_visual_features", [])}
    locked = {_feature_name(item.get("feature", "")) for item in contract.get("locked_facts", [])}
    overlap = unresolved.intersection(locked)
    if overlap:
        raise ValueError(f"features cannot be both locked and unresolved: {sorted(overlap)}")

    for item in contract.get("locked_facts", []):
        feature = item.get("feature")
        if not feature:
            raise ValueError("locked Canon fact is missing feature")
        if not item.get("evidence"):
            raise ValueError(f"locked Canon feature {feature!r} has no evidence")
        for ref in item["evidence"]:
            for key in ("chapter_id", "chapter_title", "chunk_id", "line_start", "line_end"):
                if key not in ref:
                    raise ValueError(f"Canon evidence for {feature!r} is missing {key}")


def contract_to_canon_profile(contract: dict[str, Any]) -> CanonProfile:
    validate_contract(contract)
    hard_facts = {
        _feature_name(item["feature"]): item["value"]
        for item in contract.get("locked_facts", [])
    }
    soft_traits = [
        item["instruction"]
        for item in contract.get("soft_constraints", [])
        if item.get("instruction")
    ]
    evidence: list[dict[str, Any]] = []
    for group in ("locked_facts", "soft_constraints"):
        for item in contract.get(group, []):
            feature = _feature_name(str(item.get("feature", "")))
            for ref in item.get("evidence", []):
                evidence.append({"feature": feature, **ref})

    return CanonProfile(
        character=contract["character"]["name"],
        hard_facts=hard_facts,
        soft_traits=soft_traits,
        forbidden_interpretations=list(contract.get("forbidden_interpretations", [])),
        evidence=evidence,
    )


def apply_contract(
    contract: dict[str, Any],
    state: CharacterState | None = None,
) -> CharacterState:
    validate_contract(contract)
    character = contract["character"]["name"]
    state = state or CharacterState(character=character)
    if state.character != character:
        raise ValueError(
            f"state character {state.character!r} does not match Canon contract {character!r}"
        )

    for item in contract.get("locked_facts", []):
        feature = _feature_name(item["feature"])
        value = item["value"]
        if feature in state.locked and state.locked[feature] != value:
            raise ValueError(
                f"Canon conflict for {feature!r}: state={state.locked[feature]!r}, canon={value!r}"
            )
        state.locked[feature] = value
        if feature in state.modifiable:
            state.modifiable.remove(feature)
        state.canon_constraints[feature] = {
            "value": value,
            "confidence": item.get("confidence"),
            "source_fact_id": item.get("source_fact_id"),
        }
        state.evidence_refs[feature] = list(item.get("evidence", []))

    for item in contract.get("soft_constraints", []):
        feature = _feature_name(item["feature"])
        state.design_targets[feature] = {
            "instruction": item.get("instruction", ""),
            "confidence": item.get("confidence"),
        }
        state.evidence_refs[feature] = list(item.get("evidence", []))

    for feature in contract.get("unresolved_visual_features", []):
        normalized = _feature_name(feature)
        if normalized not in state.locked and normalized not in state.modifiable:
            state.modifiable.append(normalized)

    for item in contract.get("forbidden_interpretations", []):
        if item not in state.forbidden_interpretations:
            state.forbidden_interpretations.append(item)

    state.canon_source = {
        "schema_version": contract["schema_version"],
        "character_id": contract["character"].get("id"),
        **contract.get("provenance", {}),
    }
    return state
