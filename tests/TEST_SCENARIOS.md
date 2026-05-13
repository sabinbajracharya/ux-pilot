# UX Pilot — Test Scenarios & Results

Test date: 2026-05-13
LLM: deepseek-v4-pro (75% discount)
CLI: ux-pilot 0.1.0

## Test 1: Simple e-commerce — books.toscrape.com

**Task:** Find a mystery book under £20 and tell me the title

| Persona | Steps | Time | Completed | Satisfaction | Frustration | Emotion Journey |
|---------|-------|------|-----------|-------------|-------------|-----------------|
| Anxious First-Timer | 2 | 57s | Yes | 75/100 | 0% | skeptical → skeptical |
| Careful Researcher | 2 | 58s | Yes | 85/100 | 0% | confident → confident |

**Note:** Site is too simple (static HTML catalog) to differentiate personas effectively.

## Test 2: Complex e-commerce — saucedemo.com (3 personas)

**Task:** Login, sort by price low-high, add 2 cheapest to cart, checkout as Jane Doe zip 90210, report total.

| Persona | Steps | Time | Completed | Satisfaction | Frustration | Emotion Journey | Stop Reason |
|---------|-------|------|-----------|-------------|-------------|-----------------|-------------|
| Impulse Shopper | 5 | 122s | No | — | 0% | delighted → delighted | Stuck on page |
| Careful Researcher | 6 | 202s | No | 58/100 | 0% | confident → confident | Same action repeated |
| Senior User | 5 | 134s | No | 45/100 | 0% | confident → confident | Same action repeated |

**Note:** All personas failed at the "add to cart" step. Saucedemo uses Shadow DOM for the sort dropdown.

## Test 3: Contrasting personas after emotion fix (saucedemo.com)

**Same task as Test 2**

| Persona | Steps | Time | Completed | Satisfaction | Frustration | Emotion Journey | Stop Reason |
|---------|-------|------|-----------|-------------|-------------|-----------------|-------------|
| Impulse Shopper | 5 | 137s | No | 65/100 | 0% | delighted → delighted | Stuck on page |
| Senior User | 5 | 158s | No | 25/100 | 0% | skeptical → skeptical | Same action repeated |

## Test 4: Enhanced persona prompt + frustration (books.toscrape.com)

**Task:** Browse mystery, look at 2 books, recommend one. **Persona:** Senior User

| Metric | Value |
|--------|-------|
| Steps | 5 |
| Time | 145s |
| Completed | No (frustration threshold exceeded) |
| Satisfaction | 30/100 |
| Frustration | 72% |
| Emotions | skeptical → skeptical → confused → anxious → frustrated |
| Stop reason | Frustration threshold exceeded |

**Key findings:**
- Emotion journey shows progressive degradation (5 distinct emotions)
- Frustration reaches 72% before guardrail triggers abandonment
- Notable thoughts visible: "Where do I go from here?...", "I hope I'm not making a mistake...", "Let's move on already..."
- Compound archetype "[Efficient Completionist]" detected

## Test 5: Careful Researcher with LLM-driven monologues (books.toscrape.com)

**Task:** Browse mystery+thriller, examine 3 books, pick best gift. **Persona:** Careful Researcher

| Metric | Value |
|--------|-------|
| Steps | 5 |
| Time | 161s |
| Completed | No (frustration threshold exceeded) |
| Satisfaction | 20/100 |
| Frustration | 80% |
| Emotions | confident → skeptical → confused → frustrated → frustrated |
| Stop reason | Frustration threshold exceeded |
| Compound archetype | Grumpy Loner |

**Key findings:**
- LLM-driven monologue detected: "I've been clicking through this mystery category page for far too long, and I still have a dozen more books to examine..." — contextual, specific, persona-appropriate
- Frustration accumulation works: implicit failure detection marks stuck actions as failures
- Guardrail properly triggered at 80% frustration

## Feature Verification Checklist

- [x] DeepSeek provider support (via --llm-provider deepseek)
- [x] Persona-aware guardrails (neuroticism + conscientiousness scaled)
- [x] Varied baseline emotions (6 OCEAN traits considered)
- [x] LLM-driven persona state generation (every 2 steps)
- [x] Implicit failure detection (stuck/repeated → frustration)
- [x] Notable monologue visibility in summary output
- [x] Compound archetype detection (8 → 13 rules)
- [x] 15 built-in personas (up from 10)
- [x] 17 compound trait interactions (up from 8, now covers browsing traits)
- [x] TokenTrackingWrapper extracted to runner/tracking.py (27 lines)
- [x] CLI helpers extracted to runner/commands.py (245 lines)
- [x] cli.py reduced 606→354 lines, agent.py reduced 449→395 lines
- [x] Parallel multi-persona orchestrator
- [x] --instances N flag for statistical runs
- [x] TokenTrackingWrapper (no monkey-patching)
- [x] Persona voice + frustration response patterns in prompt
- [x] 51 tests passing (up from 36)

**Task:** Same as Test 2

| Persona | Steps | Time | Completed | Satisfaction | Frustration | Emotion Journey | Stop Reason |
|---------|-------|------|-----------|-------------|-------------|-----------------|-------------|
| Impulse Shopper | 5 | 137s | No | 65/100 | 0% | **delighted** → delighted | Stuck on page |
| Senior User | 5 | 158s | No | 25/100 | 0% | **skeptical** → skeptical | Same action repeated |

**Key finding:** Emotion baselines now differentiate personas — Impulse Shopper (high extraversion + low conscientiousness) shows delighted, Senior User (moderate neuroticism + low tech literacy) shows skeptical. Satisfaction scores differ meaningfully (65 vs 25).

## Known Limitations

1. **Frustration stays at 0%** — actions on simple sites are always "successful" even when stuck
2. **Shadow DOM on saucedemo** — prevents agent from interacting with the sort dropdown and add-to-cart buttons
3. **All personas stop at same friction point** — the "add to cart" action fails for everyone, masking persona differences
4. **LLM state monologues not visible in summary output** — need to expose them in the Rich TUI or output

## Recommended Test Sites

| Site | Complexity | Good for |
|------|-----------|----------|
| books.toscrape.com | Low | Smoke tests, simple navigation |
| saucedemo.com | Medium | Login, sorting, cart, checkout (Shadow DOM caveat) |
| httpbin.org/forms/post | Low | Form interaction testing |
| wikipedia.org | Medium | Reading, scanning, search behavior |
| demoblaze.com | Medium | E-commerce with modals, no Shadow DOM |
