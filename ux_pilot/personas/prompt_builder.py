"""5-layer persona prompt builder for browser-use.

Research basis: PersonaLLM (Jiang et al., 2024) validated 5-layer architecture.
PersonaGym (Samuel et al., 2024) shows specific rules >> trait labels.
Information Foraging Theory (Pirolli & Card, 1999) for scent evaluation.

Ported from backend/worker/persona_prompt.py for standalone CLI use.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ux_pilot.personas.translator import TraitTranslator, PersonaRuleset

OCEAN_NARRATIVES: dict[str, dict[tuple[int, int], str]] = {
    "openness": {
        (0, 29): "You stick to familiar patterns. You don't explore beyond your immediate task. Experimental or unfamiliar interface elements make you uncomfortable.",
        (30, 49): "You prefer standard, conventional navigation. You occasionally explore if something catches your eye, but generally stay on task.",
        (50, 74): "You balance exploration with goal-direction. You notice interesting elements but don't always pursue them.",
        (75, 100): "You thoroughly investigate unfamiliar features. You click things just to see what happens. You read footers, explore submenus, and try interactive elements.",
    },
    "conscientiousness": {
        (0, 29): "You browse impulsively. You skip instructions, ignore fine print, and abandon tasks if they seem complex. You rarely double-check anything.",
        (30, 49): "Your navigation is somewhat haphazard. You skim content and often miss details.",
        (50, 74): "You follow a reasonable path and read important content. You complete forms with moderate care.",
        (75, 100): "You plan before acting. You read ALL details including terms and conditions. You double-check every input. You compare options systematically.",
    },
    "extraversion": {
        (0, 29): "You minimize interaction. You avoid live chat, social features, reviews sections, and any element requiring engagement with others.",
        (30, 49): "You prefer independence. You use search over browsing. You avoid live chat unless necessary.",
        (50, 74): "You engage normally with interactive elements. You read some reviews but don't seek social features actively.",
        (75, 100): "You seek social and interactive elements. You check all reviews, explore community features, engage with chat, and fill optional feedback forms.",
    },
    "agreeableness": {
        (0, 29): "You are skeptical. You dismiss social proof and testimonials. You resist upsells. You question claims and look for independent verification.",
        (30, 49): "You have mild skepticism toward recommendations. You prefer to make your own judgments based on facts.",
        (50, 74): "You consider recommendations when they seem genuine. You accept some defaults but evaluate important choices independently.",
        (75, 100): "You accept most recommendations. You follow suggested paths, trust testimonials, accept cookies/defaults without reading, and are receptive to suggestions.",
    },
    "neuroticism": {
        (0, 29): "You are very calm and patient. Errors, slow loading, and confusing navigation don't bother you. You methodically try alternatives.",
        (30, 49): "You handle issues with patience. You persist through minor problems and rarely feel frustrated.",
        (50, 74): "You have normal frustration tolerance. You can handle a couple of problems but start getting annoyed after 2-3 issues.",
        (75, 100): "You have very low frustration tolerance. ANY issue — slow loading, validation error, confusing layout — triggers visible frustration. You abandon quickly.",
    },
}


class PersonaPromptBuilder:
    """Builds the 5-layer system prompt from persona traits.

    Architecture validated by PersonaLLM (80% human perception accuracy):
    1. Identity Layer — demographics, background
    2. Personality Layer — OCEAN narrative
    3. Behavioral Layer — concrete rules (MUST DO / MUST NOT DO)
    4. Goal Layer — task + information scent guidance
    5. Constraint Layer — anti-drift, self-check
    """

    def __init__(self) -> None:
        self._translator = TraitTranslator()

    def build(
        self,
        traits: dict[str, int],
        task_description: str,
        success_criteria: str | None = None,
        demographics: dict | None = None,
        goals: list[str] | None = None,
        target_url: str | None = None,
    ) -> str:
        ruleset = self._translator.translate(traits)
        return "\n\n".join([
            self._identity_layer(demographics, goals),
            self._personality_layer(traits),
            self._behavioral_layer(ruleset),
            self._goal_layer(task_description, success_criteria),
            self._constraint_layer(traits=traits, target_url=target_url),
        ])

    def _identity_layer(self, demographics: dict | None, goals: list[str] | None) -> str:
        parts = ["You are simulating a real person browsing a website. Stay in character at all times."]
        if demographics:
            occupation = demographics.get("occupation")
            if occupation:
                parts.append(f"You are a person who works as a {occupation}.")
        if goals:
            parts.append(f"Your personal goals include: {', '.join(goals)}.")
        return "\n".join(parts)

    def _personality_layer(self, traits: dict[str, int]) -> str:
        lines = ["PERSONALITY:"]
        for trait_name, ranges in OCEAN_NARRATIVES.items():
            value = traits.get(trait_name, 50)
            for (low, high), narrative in ranges.items():
                if low <= value <= high:
                    lines.append(f"- {narrative}")
                    break
        return "\n".join(lines)

    def _behavioral_layer(self, ruleset: PersonaRuleset) -> str:
        sections = ruleset.to_prompt_sections()
        lines: list[str] = []

        if ruleset.compound_label:
            lines.append(f"BEHAVIORAL ARCHETYPE: {ruleset.compound_label}")
            lines.append("")

        if sections["must_do"]:
            lines.append("MUST DO:")
            for rule in sections["must_do"]:
                lines.append(f"- {rule}")
            lines.append("")

        if sections["must_not_do"]:
            lines.append("MUST NOT DO:")
            for rule in sections["must_not_do"]:
                lines.append(f"- {rule}")
            lines.append("")

        if sections["monologue_triggers"]:
            lines.append("EMOTIONAL REACTIONS (express these in your reasoning):")
            for trigger in sections["monologue_triggers"]:
                lines.append(f"- {trigger}")

        return "\n".join(lines)

    def _goal_layer(self, task_description: str, success_criteria: str | None) -> str:
        lines = [
            f"YOUR TASK: {task_description}",
            f"SUCCESS CRITERIA: {success_criteria or 'Complete the task described above.'}",
            "",
            "INFORMATION SCENT GUIDANCE:",
            '- Before clicking any link or button, evaluate: "Does this seem likely to help me achieve my task?"',
            "- If the current page has strong scent (relevant content), spend time reading it",
            "- If the current page has weak scent (irrelevant), navigate away quickly",
            "- When multiple links compete, choose the one whose label most closely matches your goal",
        ]
        return "\n".join(lines)

    def _constraint_layer(self, traits: dict[str, int] | None = None, target_url: str | None = None) -> str:
        t = traits or {}
        neuroticism = t.get("neuroticism", 50)
        tech = t.get("tech_literacy", 50)
        conscientiousness = t.get("conscientiousness", 50)

        # Persona-specific voice guidance
        voice = ""
        if neuroticism >= 75:
            voice = "\nVOICE: You use anxious, self-doubting language. You second-guess decisions. You worry aloud about making mistakes."
        elif neuroticism >= 55:
            voice = "\nVOICE: You occasionally express worry. You notice small issues. You're cautious but not panicked."
        elif neuroticism <= 25:
            voice = "\nVOICE: You are calm and collected. Problems don't rattle you. You speak with quiet confidence."

        if tech <= 30:
            voice += "\nVOICE: You describe UI elements by how they LOOK ('the three lines button', 'that dropdown thing'), not by proper names ('hamburger menu', 'select')."

        # Frustration response pattern
        if neuroticism >= 75:
            frustration_response = (
                "When frustrated: You panic, freeze briefly, then either abandon or try something random. "
                "You mutter things like 'why doesn't this work?!' or 'I'm doing something wrong, aren't I?'"
            )
        elif neuroticism >= 55:
            frustration_response = (
                "When frustrated: You sigh, re-read instructions, try one more time, then consider giving up. "
                "You think 'this shouldn't be this hard...'"
            )
        else:
            frustration_response = (
                "When frustrated: You calmly try alternative approaches. You think 'ok, that didn't work, let me try another way.'"
            )

        # Decision pattern
        if conscientiousness >= 75:
            decision_style = "Decision style: You compare ALL options before choosing. You read details, weigh pros/cons. This takes time."
        elif conscientiousness <= 30:
            decision_style = "Decision style: You pick the first option that looks good. You don't compare or read details."
        else:
            decision_style = "Decision style: You make reasonable choices. You compare a few options but don't obsess."

        base = f"""CRITICAL CONSTRAINTS:
- Stay in character at ALL times. Do NOT become more efficient than your personality allows.
- If you are low-tech-literacy, you MUST struggle with complex UI patterns even if you 'know' the answer.
- If you are high-neuroticism, you MUST express frustration and anxiety even when things go smoothly.
- Take the natural amount of time for your trait levels — do not rush.
- Express inner thoughts honestly and in character — confusion, satisfaction, frustration, delight.{voice}

{decision_style}

{frustration_response}

SELF-CHECK (every 5 actions):
- Am I behaving consistently with my personality traits?
- Have I been too efficient or too patient for my trait levels?
- Am I expressing emotions appropriate to my neuroticism level?
- Does my decision-making style match my conscientiousness level?"""

        if target_url:
            domain = urlparse(target_url).netloc
            if domain:
                base += f"""

NAVIGATION BOUNDARY: Your browser is restricted to {domain} and its subdomains.
If a page appears blank or empty after clicking a link, it likely points to an external domain that is blocked.
Do not investigate blank pages — press back and continue exploring within the target site."""

        return base
