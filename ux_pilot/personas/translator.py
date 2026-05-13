"""TraitTranslator — converts persona traits (0-100) to behavioral rules.

Research basis: PersonaGym (2024) shows specific behavioral rules produce
76.1% correlation with human judgment, much better than trait labels alone.

Ported from backend/worker/traits/translator.py for standalone CLI use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ux_pilot.personas.rules import TRAIT_TIERS, COMPOUND_RULES, TraitTier


@dataclass
class BehavioralRule:
    trait: str
    level: str
    must_do: list[str] = field(default_factory=list)
    must_not_do: list[str] = field(default_factory=list)
    monologue_triggers: list[str] = field(default_factory=list)


@dataclass
class PersonaRuleset:
    rules: list[BehavioralRule] = field(default_factory=list)
    compound_label: str | None = None

    def to_prompt_sections(self) -> dict[str, list[str]]:
        """Aggregate all rules into prompt-ready sections."""
        must_do: list[str] = []
        must_not_do: list[str] = []
        monologue_triggers: list[str] = []

        for rule in self.rules:
            must_do.extend(rule.must_do)
            must_not_do.extend(rule.must_not_do)
            monologue_triggers.extend(rule.monologue_triggers)

        return {
            "must_do": must_do,
            "must_not_do": must_not_do,
            "monologue_triggers": monologue_triggers,
        }


class TraitTranslator:
    """Converts 9 numeric traits into concrete behavioral rules."""

    def translate(self, traits: dict[str, int]) -> PersonaRuleset:
        rules: list[BehavioralRule] = []

        for trait_name, tiers in TRAIT_TIERS.items():
            value = traits.get(trait_name, 50)
            tier = self._find_tier(tiers, value)
            if tier:
                rules.append(BehavioralRule(
                    trait=trait_name,
                    level=tier.label,
                    must_do=list(tier.must_do),
                    must_not_do=list(tier.must_not_do),
                    monologue_triggers=list(tier.monologue_triggers),
                ))

        compound_label = None
        for label, rule_data in self._get_compound_rules(traits):
            compound_label = label
            rules.append(BehavioralRule(
                trait=f"compound:{label}",
                level=label,
                must_do=list(rule_data.get("must_do", [])),
                must_not_do=list(rule_data.get("must_not_do", [])),
            ))

        return PersonaRuleset(rules=rules, compound_label=compound_label)

    def _find_tier(self, tiers: list[TraitTier], value: int) -> TraitTier | None:
        for tier in tiers:
            if tier.min_value <= value <= tier.max_value:
                return tier
        return tiers[-1] if tiers else None

    def _get_compound_rules(self, traits: dict[str, int]) -> list[tuple[str, dict]]:
        """Determine which compound trait interactions apply."""
        results = []

        def _level(trait: str) -> str:
            value = traits.get(trait, 50)
            if value >= 70:
                return "high"
            elif value <= 30:
                return "low"
            return "mid"

        trait_levels = {
            "openness": _level("openness"),
            "conscientiousness": _level("conscientiousness"),
            "extraversion": _level("extraversion"),
            "agreeableness": _level("agreeableness"),
            "neuroticism": _level("neuroticism"),
            "tech_literacy": _level("tech_literacy"),
            "decision_speed": _level("decision_speed"),
            "attention_span": _level("attention_span"),
            "price_sensitivity": _level("price_sensitivity"),
        }

        for (key1, key2), rule_data in COMPOUND_RULES.items():
            level1, trait1 = key1.split("_", 1)
            level2, trait2 = key2.split("_", 1)

            if trait_levels.get(trait1) == level1 and trait_levels.get(trait2) == level2:
                results.append((str(rule_data["label"]), rule_data))

        return results
