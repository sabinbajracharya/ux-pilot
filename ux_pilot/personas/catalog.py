"""Built-in persona catalog — 10 OCEAN-based archetypes.

Ported from backend/seed/templates.py for standalone CLI use.
"""

from __future__ import annotations

from dataclasses import dataclass, field


AGE_RANGE_LABELS = {0: "Teen", 1: "Young Adult", 2: "Adult", 3: "Middle-Aged", 4: "Senior"}


@dataclass(frozen=True)
class PersonaTemplate:
    """An immutable persona definition."""

    name: str
    description: str
    category: str
    traits: dict[str, int]
    demographics: dict[str, str | int] = field(default_factory=dict)
    goals: list[str] = field(default_factory=list)
    accessibility_needs: list[str] = field(default_factory=list)

    @property
    def age_label(self) -> str:
        return AGE_RANGE_LABELS.get(self.demographics.get("ageRange", 2), "Adult")

    @property
    def occupation(self) -> str:
        return str(self.demographics.get("occupation", "Various"))


CATALOG: list[PersonaTemplate] = [
    PersonaTemplate(
        name="Tech-Savvy Professional",
        description="Efficient power user who navigates quickly, uses keyboard shortcuts, and gets impatient with poor UX.",
        category="Professional",
        traits={
            "openness": 70, "conscientiousness": 60, "extraversion": 50,
            "agreeableness": 50, "neuroticism": 20,
            "tech_literacy": 95, "decision_speed": 80,
            "attention_span": 60, "price_sensitivity": 30,
        },
        demographics={"ageRange": 1, "occupation": "Software Engineer"},
        goals=["Complete tasks efficiently", "Find technical specifications"],
    ),
    PersonaTemplate(
        name="Careful Researcher",
        description="Methodical user who reads everything, compares all options, and checks reviews before making any decision.",
        category="Analytical",
        traits={
            "openness": 40, "conscientiousness": 95, "extraversion": 30,
            "agreeableness": 30, "neuroticism": 40,
            "tech_literacy": 60, "decision_speed": 20,
            "attention_span": 95, "price_sensitivity": 50,
        },
        demographics={"ageRange": 2, "occupation": "Analyst"},
        goals=["Make informed decisions", "Compare all available options"],
    ),
    PersonaTemplate(
        name="Impulse Shopper",
        description="Quick decision-maker attracted by visuals and deals. Skips fine print, clicks fast, easily distracted by promotions.",
        category="Consumer",
        traits={
            "openness": 60, "conscientiousness": 20, "extraversion": 80,
            "agreeableness": 70, "neuroticism": 30,
            "tech_literacy": 50, "decision_speed": 95,
            "attention_span": 30, "price_sensitivity": 20,
        },
        demographics={"ageRange": 1, "occupation": "Marketing"},
        goals=["Find exciting products", "Get the best deals quickly"],
    ),
    PersonaTemplate(
        name="Anxious First-Timer",
        description="Nervous, low-tech user who hesitates at every step, gets confused by modern UI, and abandons easily when frustrated.",
        category="Novice",
        traits={
            "openness": 30, "conscientiousness": 50, "extraversion": 20,
            "agreeableness": 40, "neuroticism": 90,
            "tech_literacy": 25, "decision_speed": 30,
            "attention_span": 50, "price_sensitivity": 40,
        },
        demographics={"ageRange": 2, "occupation": "Various"},
        goals=["Complete a specific task", "Not make mistakes"],
    ),
    PersonaTemplate(
        name="Price Hunter",
        description="Driven by cost. Always sorts by price, seeks coupons, compares across tabs, and is skeptical of upsells.",
        category="Consumer",
        traits={
            "openness": 50, "conscientiousness": 80, "extraversion": 40,
            "agreeableness": 20, "neuroticism": 50,
            "tech_literacy": 60, "decision_speed": 30,
            "attention_span": 80, "price_sensitivity": 95,
        },
        demographics={"ageRange": 2, "occupation": "Various"},
        goals=["Find the lowest price", "Use coupon codes"],
    ),
    PersonaTemplate(
        name="Brand Loyal Enthusiast",
        description="Trusts familiar brands, follows recommendations, engages with reviews, and prefers guided experiences.",
        category="Consumer",
        traits={
            "openness": 30, "conscientiousness": 50, "extraversion": 70,
            "agreeableness": 85, "neuroticism": 30,
            "tech_literacy": 55, "decision_speed": 60,
            "attention_span": 50, "price_sensitivity": 20,
        },
        demographics={"ageRange": 2, "occupation": "Various"},
        goals=["Find trusted products", "Follow brand recommendations"],
    ),
    PersonaTemplate(
        name="Senior User",
        description="Slower navigation, prefers larger text, trusts authority. Confused by modern UI patterns like hamburger menus.",
        category="Demographic",
        traits={
            "openness": 30, "conscientiousness": 70, "extraversion": 40,
            "agreeableness": 60, "neuroticism": 60,
            "tech_literacy": 20, "decision_speed": 25,
            "attention_span": 70, "price_sensitivity": 50,
        },
        demographics={"ageRange": 4, "occupation": "Retired"},
        goals=["Complete tasks at own pace", "Understand the interface"],
    ),
    PersonaTemplate(
        name="Accessibility User",
        description="Uses screen reader and keyboard navigation. Relies on ARIA labels, semantic HTML, and skip links.",
        category="Accessibility",
        traits={
            "openness": 50, "conscientiousness": 60, "extraversion": 40,
            "agreeableness": 50, "neuroticism": 40,
            "tech_literacy": 50, "decision_speed": 40,
            "attention_span": 60, "price_sensitivity": 40,
        },
        demographics={"ageRange": 2, "occupation": "Various"},
        goals=["Navigate using assistive technology", "Complete tasks independently"],
        accessibility_needs=["screen_reader"],
    ),
    PersonaTemplate(
        name="Enterprise B2B Buyer",
        description="Systematic evaluator comparing vendors. Reads all specs, checks compliance, needs procurement-friendly flows.",
        category="Professional",
        traits={
            "openness": 40, "conscientiousness": 90, "extraversion": 60,
            "agreeableness": 30, "neuroticism": 30,
            "tech_literacy": 75, "decision_speed": 20,
            "attention_span": 90, "price_sensitivity": 70,
        },
        demographics={"ageRange": 2, "occupation": "Procurement Manager"},
        goals=["Evaluate vendor capabilities", "Compare pricing tiers"],
    ),
    PersonaTemplate(
        name="First-Time Online Shopper",
        description="New to online shopping. Trusts easily but gets anxious at checkout. Confused by shipping options and payment forms.",
        category="Novice",
        traits={
            "openness": 50, "conscientiousness": 40, "extraversion": 50,
            "agreeableness": 70, "neuroticism": 70,
            "tech_literacy": 15, "decision_speed": 40,
            "attention_span": 40, "price_sensitivity": 60,
        },
        demographics={"ageRange": 3, "occupation": "Various"},
        goals=["Buy something online for the first time", "Understand the checkout process"],
    ),
]


def get_persona_by_name(name: str) -> PersonaTemplate | None:
    """Find persona by exact or case-insensitive partial name match."""
    lower = name.lower()
    for p in CATALOG:
        if p.name.lower() == lower:
            return p
    for p in CATALOG:
        if lower in p.name.lower():
            return p
    return None


def get_persona_by_index(index: int) -> PersonaTemplate | None:
    """Get persona by 1-based index."""
    if 1 <= index <= len(CATALOG):
        return CATALOG[index - 1]
    return None
