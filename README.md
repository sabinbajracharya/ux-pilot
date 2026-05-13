# 🎭 UX Pilot

**AI personas that simulate real humans browsing your website — find UX friction from the command line.**

One command. Real users. Real friction. Real fixes.

```bash
ux-pilot run --url "https://shop.example.com" --task "Find a phone under $500" --persona "Anxious First-Timer"
```

Watch an AI persona — with a real personality, real frustrations, real hesitations — navigate your site. When it's done, get a crisp report: *"Here's where users struggle. Here's what to fix. Here's why."*

## Install

```bash
cd cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

After installation, the `ux-pilot` command is available whenever the venv is active.

## Quick Start

```bash
# Set your LLM API key
export OPENAI_API_KEY="sk-..."

# Run with a built-in persona
ux-pilot run --url "https://books.toscrape.com" --task "Find a mystery book under £20"

# Choose a specific persona
ux-pilot run --url "https://shop.example.com" --task "Buy a smartphone" --persona "Anxious First-Timer"

# Compare multiple personas
ux-pilot run --url "https://shop.example.com" --task "Buy a smartphone" \
  --persona "Tech-Savvy Professional" \
  --persona "Anxious First-Timer" \
  --persona "Senior User"

# Save results
ux-pilot run --url "https://example.com" --task "Sign up" --output ./results
```

## Built-in Personas

```bash
ux-pilot personas list
```

| # | Name | Category | Key Traits |
|---|------|----------|------------|
| 1 | Tech-Savvy Professional | Professional | 95 tech · 20 neuro · 80 speed |
| 2 | Careful Researcher | Analytical | 95 consc · 95 attn · 20 speed |
| 3 | Impulse Shopper | Consumer | 95 speed · 20 consc · 80 extra |
| 4 | Anxious First-Timer | Novice | 90 neuro · 25 tech · 30 open |
| 5 | Price Hunter | Consumer | 95 price · 80 consc · 80 attn |
| 6 | Brand Loyal Enthusiast | Consumer | 85 agree · 20 price · 70 extra |
| 7 | Senior User | Demographic | 20 tech · 25 speed · 60 neuro |
| 8 | Accessibility User | Accessibility | 60 consc · 50 tech · 40 neuro |
| 9 | Enterprise B2B Buyer | Professional | 90 consc · 90 attn · 20 speed |
| 10 | First-Time Online Shopper | Novice | 15 tech · 70 agree · 75 neuro |
| 11 | Social Media Scroller | Consumer | 90 extra · 20 attn · 75 open |
| 12 | Privacy-Conscious User | Privacy | 85 consc · 20 agree · 80 attn |
| 13 | Power Admin | Professional | 95 tech · 85 speed · 80 consc |
| 14 | Mobile-Only User | Demographic | 25 attn · 70 speed · 65 extra |
| 15 | Weekend Deal Hunter | Consumer | 85 price · 35 speed · 55 consc |

## Custom Personas

Create a YAML file:

```yaml
# my-persona.yaml
name: "Budget-Conscious Senior"
description: "Retired teacher, careful with money, slow with tech"
category: "Custom"
traits:
  openness: 25
  conscientiousness: 80
  extraversion: 35
  agreeableness: 70
  neuroticism: 55
  tech_literacy: 20
  decision_speed: 25
  attention_span: 70
  price_sensitivity: 95
demographics:
  age_range: senior
  occupation: "Retired teacher"
goals:
  - "Find the best value product"
  - "Make sure there are no hidden fees"
```

```bash
ux-pilot run --url "https://shop.example.com" --task "Buy groceries" --persona-file my-persona.yaml
```

Or override individual traits inline:

```bash
ux-pilot run --url "https://example.com" --task "Sign up" \
  --persona "Tech-Savvy Professional" \
  --trait neuroticism=80 --trait tech_literacy=30
```

## Commands

| Command | Description |
|---------|-------------|
| `ux-pilot run` | Run a persona against a website |
| `ux-pilot personas list` | List built-in personas |
| `ux-pilot personas show <name>` | Show persona details |
| `ux-pilot history list` | View past runs |
| `ux-pilot history show <id>` | Show details of a past run |

## Configuration

Settings are resolved with this priority: **CLI flags → env vars → config file → defaults**

Create `~/.ux-pilot/config.yaml` to set persistent defaults:

```yaml
llm_provider: openai
llm_model: gpt-4o
llm_api_key: sk-...        # or use env vars instead
headed: false
max_actions: 50
max_duration_minutes: 5
output_dir: ./results
ollama_base_url: http://localhost:11434
```

Environment variables use the `UX_PILOT_` prefix:

```bash
export UX_PILOT_LLM_PROVIDER=anthropic
export UX_PILOT_LLM_MODEL=claude-sonnet-4-20250514
export UX_PILOT_MAX_ACTIONS=30
```

CLI flags always win:

```bash
ux-pilot run --url ... --task ... --llm-model gpt-4o --max-actions 20
```

## LLM Providers

```bash
# OpenAI (default)
export OPENAI_API_KEY="sk-..."
ux-pilot run --url ... --task ...

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
ux-pilot run --url ... --task ... --llm-provider anthropic --llm-model claude-sonnet-4-20250514

# Groq
export GROQ_API_KEY="gsk_..."
ux-pilot run --url ... --task ... --llm-provider groq --llm-model llama-3.3-70b-versatile

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
ux-pilot run --url ... --task ... --llm-provider deepseek --llm-model deepseek-chat

# Ollama (local, free)
ux-pilot run --url ... --task ... --llm-provider ollama --llm-model llama3.2
```

### Statistical Runs

Run the same persona multiple times for statistical validity (LLM behavior is non-deterministic):

```bash
ux-pilot run --url "https://shop.example.com" --task "Buy a smartphone" \
  --persona "Anxious First-Timer" --instances 5
```

## How It Works

### Persona System (9 Traits, OCEAN + Browsing)

Each persona has 9 traits scored 0-100:

**OCEAN (Big Five):** Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism

**Browsing:** Tech Literacy, Decision Speed, Attention Span, Price Sensitivity

Traits map to concrete behaviors via a 4-tier system:
- **Behavioral Rules**: What the persona must/must not do
- **Monologue Triggers**: Inner thoughts based on situation
- **Compound Interactions**: 8 emergent behaviors from trait combinations

### 5-Layer Prompt Architecture

1. **Identity**: Who the persona is
2. **Personality**: OCEAN narrative descriptions
3. **Behavioral**: Must-do / must-not-do rules from trait tiers
4. **Goal**: Task + information scent guidance
5. **Constraint**: Anti-drift + domain boundary

### Humanization (Research-Backed)

- **Mouse**: Fitts' Law + cubic Bézier curves + jitter + overshoot
- **Typing**: QWERTY adjacency errors, 70-130ms dwell, 2-8% error rate
- **Scrolling**: NNGroup attention distribution (57% above fold)
- **Timing**: Hick's Law decision delays, page evaluation pauses
- **Frustration**: +15 per error × neuroticism multiplier, -5 per success

### Guardrails (6 Stop Conditions)

1. Max actions (default 50)
2. Max duration (default 5 min)
3. Consecutive failures (5)
4. Frustration threshold (70/100, Baymard-inspired)
5. Stuck on same page (4×)
6. Repeated identical actions (3×)

## Output

### Live Dashboard

Real-time Rich terminal display during runs showing persona actions, frustration bar, inner monologue, and stats.

### Post-Run Summary

- Task completion status + satisfaction score
- Emotion journey timeline
- Friction points detected
- 3-5 prioritized UX recommendations with evidence

### Export

```bash
ux-pilot run ... --output ./results
# Creates:
#   results/ux-pilot_20250101_120000.json   (structured data)
#   results/ux-pilot_20250101_120000.md     (readable report)
```

## Architecture

```
ux_pilot/
├── cli.py              # Typer CLI entry (run, personas, history)
├── config.py           # Settings cascade (CLI > env > file > defaults)
├── personas/           # 15 built-in personas, trait system, prompt builder
│   ├── catalog.py      # Persona archetype definitions
│   ├── rules.py        # 4-tier behavioral rules + 17 compound interactions
│   ├── translator.py   # Traits → behavioral rules engine
│   ├── prompt_builder.py  # 5-layer system prompt (PersonaLLM-validated)
│   └── state_generator.py # LLM-driven emotion + monologue generation
├── runner/             # Browser agent execution
│   ├── agent.py        # AgentRunner (browser-use wrapper)
│   ├── orchestrator.py # Parallel multi-persona execution
│   ├── commands.py     # CLI command implementations
│   ├── guardrails.py   # Persona-aware stop conditions + frustration
│   ├── hooks.py        # Human-like timing delays
│   ├── llm_factory.py  # Provider-agnostic LLM (OpenAI, Anthropic, DeepSeek, Groq, Ollama)
│   └── tracking.py     # Token usage tracking (composition pattern)
├── humanization/       # Research-backed human simulation
│   ├── profile.py      # Trait → behavioral parameter mapping
│   ├── mouse.py        # Bézier curves, Fitts' Law
│   ├── typing.py       # KeyRecs: dwell timing, error patterns
│   ├── scrolling.py    # NNGroup attention distribution
│   └── timing.py       # Hick's Law, page evaluation delays
├── analysis/           # Post-run AI analysis
├── output/             # Rich Live TUI, summary, export, comparison
└── storage/            # SQLite run history
```

**Key features:**
- 15 built-in personas with 9-trait OCEAN + browsing model
- 17 compound trait interactions for emergent behaviors
- LLM-driven persona state (contextual monologues every 2 steps)
- Persona-aware guardrails (thresholds scaled by neuroticism/conscientiousness)
- Implicit failure detection (frustration from stuck/repeated actions)
- `--instances N` for statistical validity across multiple runs
- Provider-agnostic: OpenAI, Anthropic, DeepSeek, Groq, Ollama
- 55 tests

**Dependencies (6 runtime):** browser-use, litellm, typer, rich, pydantic, openai

## License

MIT — free for personal and commercial use, modification, and redistribution.

UX Pilot is open-source. The enterprise platform (concurrent agents, dashboards,
video recordings, team collaboration) is a separate proprietary product. If you
need to run personas at scale, contact us for the hosted version.
