# Readers -- Architecture

> A multi-agent reader simulation engine for indie authors.
> Simulates hundreds to thousands of AI-generated reader personas reacting to a book
> description across multiple rounds of social interaction.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [File Map](#file-map)
3. [High-Level Data Flow](#high-level-data-flow)
4. [Provider Abstraction Layer](#provider-abstraction-layer)
5. [Token Counter](#token-counter)
6. [Persona System](#persona-system)
7. [Batch Processing Pipeline](#batch-processing-pipeline)
8. [Multi-Round Simulation Engine](#multi-round-simulation-engine)
9. [Concurrent Processing Infrastructure](#concurrent-processing-infrastructure)
10. [Aggregation Engine](#aggregation-engine)
11. [Report Generation](#report-generation)
12. [Cost Estimation](#cost-estimation)
13. [Auto-Summarization](#auto-summarization)
14. [GUI Launcher](#gui-launcher)
15. [Scaling Characteristics](#scaling-characteristics)
16. [Dependencies](#dependencies)

---

## System Overview

Readers is a Python application that orchestrates large-scale simulated reader
reactions to a book description. It sends batched persona data and book
descriptions to an LLM, parses structured JSON responses, runs multiple rounds
of simulated social interaction, aggregates the results into statistical
summaries, and produces a standalone HTML report.

```
+------------------+     +-----------+     +------------+     +----------+
|  Book            |     |  Persona  |     |  LLM       |     |  Report  |
|  Description     +---->+  Batches  +---->+  Provider   +---->+  Output  |
|  (text or file)  |     |  (JSON)   |     |  (API)     |     |  (HTML)  |
+------------------+     +-----------+     +------------+     +----------+
        |                      ^                 |
        |                      |                 |
        v                      |                 v
+------------------+     +-----------+     +------------+
|  Auto-Summarize  |     |  Trending |     |  JSON      |
|  (>2,000 words)  |     |  Post     |     |  Parser    |
|                  |     |  Selector |<----+  + Repair  |
+------------------+     +-----------+     +------------+
                               |
                               v
                         +-----------+
                         | Rounds    |
                         | 2..N      |
                         | (social)  |
                         +-----------+
```

---

## File Map

```
Readers/
|-- readers.py              Main simulation engine (CLI entry point)
|-- report_generator.py     HTML report generation (single-file output)
|-- readers_gui.py          Tkinter GUI launcher for non-technical users
|-- generate_personas.py    Deterministic persona generator (PRISM demographics)
|-- pricing.json            User-editable cost-per-call estimates by provider/model
|-- requirements.txt        Python dependencies
|-- .env.example            Template for API keys
|
|-- personas.json           Default persona pool (~1,000 readers)
|-- personas_5000.json      5,000-reader pool
|-- personas_10000.json     10,000-reader pool
|-- personas_romance.json   Genre-tuned pool: romance
|-- personas_thriller.json  Genre-tuned pool: thriller
|-- personas_fantasy.json   Genre-tuned pool: fantasy
|-- personas_scifi.json     Genre-tuned pool: sci-fi
|-- personas_literary.json  Genre-tuned pool: literary fiction
|-- personas_nonfiction.json Genre-tuned pool: nonfiction
|-- personas_ya.json        Genre-tuned pool: young adult
|
|-- output/                 Generated reports (HTML + JSON)
|-- examples/               Sample book descriptions for testing
|-- swarm_visualization.html Animated wait-screen (optional eye candy)
```

---

## High-Level Data Flow

The simulation proceeds through a linear pipeline with an iterative loop for
social rounds:

```
1. INPUT
   User provides book description (text arg, --file, or GUI paste)
          |
          v
2. PRE-PROCESS
   If word count > 2,000: auto-summarize via the LLM provider
          |
          v
3. INITIALIZE
   Provider created (factory pattern), personas loaded (genre-aware),
   pre-run cost estimate displayed, confirmation prompt if > $1.00
          |
          v
4. ROUND 1 -- First Impressions
   All N readers --> split into batches of 5 --> LLM calls (parallel or
   sequential) --> parse JSON responses --> collect results
          |
          v
5. ROUNDS 2..N -- Social Simulation Loop
   For each round:
     a. Score & select trending posts from previous round
     b. Select active readers (~1/3 base; lurkers join gradually)
     c. Batch active readers --> LLM calls --> parse --> collect
     d. Feed results into next round
          |
          v
6. AGGREGATE
   Combine all rounds into unified statistics (ratings, emotions,
   demographics, purchase intent, confidence metrics, virality, etc.)
          |
          v
7. OUTPUT
   a. HTML report generated (single file, no external assets)
   b. Raw JSON export saved alongside
   c. Report auto-opens in browser
```

---

## Provider Abstraction Layer

All LLM interaction is mediated through a single abstract interface.

### Class Hierarchy

```
LLMProvider (base)
  |-- OllamaProvider       Local inference, free.  Default model: qwen3.5:0.8b
  |-- OpenAIProvider       Cloud API.              Default model: gpt-4o-mini
  |-- AnthropicProvider    Cloud API.              Default model: claude-haiku-4-5-20251001
  |-- GeminiProvider       Cloud API.              Default model: gemini-2.5-flash (recommended)
```

### Interface

```python
class LLMProvider:
    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        """Send a prompt and return the raw text response."""
        raise NotImplementedError
```

Every concrete provider:

1. Initializes its SDK client in `__init__`.
2. Looks up its per-call cost from `pricing.json` (falling back to hardcoded
   defaults).
3. Implements `chat()` to call the API with temperature 0.7-0.8.
4. Extracts token usage from the provider-specific response object and feeds it
   into the global `token_counter`.

### Factory Function

```python
def get_provider(provider_name, model=None, api_key=None, host=None) -> LLMProvider
```

Resolves the provider by name, sources API keys from arguments or environment
variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`), and returns
the instantiated provider.

### Provider-Specific Notes

| Provider  | JSON Mode              | Token Tracking Field                          |
|-----------|------------------------|-----------------------------------------------|
| Ollama    | `format="json"`, `think=False` | `response.prompt_eval_count`, `response.eval_count` |
| OpenAI    | Default (text)         | `response.usage.prompt_tokens`, `.completion_tokens`  |
| Anthropic | Default (text)         | `response.usage.input_tokens`, `.output_tokens`       |
| Gemini    | `response_mime_type="application/json"` | `response.usage_metadata.prompt_token_count`, `.candidates_token_count` |

---

## Token Counter

```python
class TokenCounter:
    """Thread-safe real-time token counter for tracking actual API usage."""
```

A global singleton (`token_counter`) shared by all provider instances and all
worker threads. Uses a `threading.Lock` to protect three accumulators:

- `input_tokens` -- total prompt tokens across all calls
- `output_tokens` -- total completion tokens across all calls
- `total_calls` -- number of LLM invocations

Updated by each provider's `chat()` method immediately after every API response.
Progress bars read from `token_counter.format_live()` during the simulation, and
the final summary reads from `token_counter.snapshot()`.

---

## Persona System

### Schema (per persona)

Each persona is a JSON object with the following fields:

| Field                | Type       | Description                                            |
|----------------------|------------|--------------------------------------------------------|
| `persona_id`         | int        | Unique identifier                                      |
| `name`               | string     | Full name (diverse, multicultural name pool)            |
| `age_range`          | string     | One of: `16-21`, `22-28`, `29-35`, `36-45`, `46-55`, `56+` |
| `platform`           | string     | `BookTok`, `Goodreads`, `Reddit`, `Bookstagram`, `X_Twitter`, `Lurker` |
| `primary_genre`      | string     | Main genre preference (40 genres)                       |
| `preferred_genres`   | list[str]  | Additional genre affinities                             |
| `trope_loves`        | list[str]  | Tropes this reader seeks out                            |
| `trope_hates`        | list[str]  | Tropes that trigger DNFs                                |
| `critical_level`     | int (1-10) | How harsh a critic (10 = most critical)                 |
| `review_style`       | string     | `emotional`, `analytical`, `snarky`, `cheerleader`, `lurker` |
| `dnf_threshold`      | string     | How easily they abandon books                           |
| `influence_level`    | string     | `micro`, `mid`, `macro` (affects trending score)        |
| `bio`                | string     | Platform-voiced bio blurb                               |
| `platform_voice`     | string     | Writing style description for that platform             |
| `demographic_segment`| string     | PRISM segment (see below)                               |
| `segment_data`       | object     | Contains `price_sensitivity`, `preferred_formats`       |

### PRISM Demographic Segments

The V3 persona generator assigns each reader to one of eight demographic
segments, modeled loosely on consumer segmentation frameworks:

| Segment              | Price Sensitivity | Key Trait                                  |
|----------------------|-------------------|--------------------------------------------|
| Affluent Bookworms   | Low               | Premium buyers, literary/award-focused      |
| Young Urban Readers  | Medium            | Trend-driven, BookTok-influenced            |
| Suburban Families    | Medium            | Escapist readers, book club members          |
| Academic Readers     | Low               | High critical standards, intellectually driven |
| Budget Readers       | High              | Kindle Unlimited, high volume, entertainment-first |
| Diverse Voices       | Medium            | Seek representation, own-voices narratives   |
| Retired Avid Readers | Low               | High volume, genre loyalists                 |
| Teen/YA Natives      | High              | Young, social-media-native, trend followers  |

### Persona Generation (`generate_personas.py`)

Personas are generated **deterministically** (no LLM needed). The generator:

1. Draws from multicultural name pools (~100 first names per gender, ~100 last
   names).
2. Assigns platform, age range, review style, and genres using weighted random
   distributions.
3. Assigns a PRISM demographic segment with weighted probability.
4. Generates platform-specific bios using templates.
5. Outputs JSON files for any count (1K, 5K, 10K) and any genre focus.

### Loading and Recycling

```python
def load_personas(path: Path, count: int = 1000) -> list
```

- If `count <= len(file)`: returns the first `count` personas.
- If `count > len(file)` (up to 500K): cycles through the pool with shuffled
  order and slight `critical_level` jitter (+/- 1) to avoid identical batches.
- `get_personas_path()` auto-selects the best file: genre-specific first, then
  exact size match, then largest available.

---

## Batch Processing Pipeline

### Batching

Readers are split into batches (default size: 5). Each batch is condensed into a
compact JSON payload via `create_batch_payload()`, which extracts the fields the
LLM needs and drops internal metadata.

```
1000 readers / 5 per batch = 200 LLM calls for Round 1
```

### Prompt Templates

Three prompt templates drive the simulation:

| Template              | Used In   | Purpose                                      |
|-----------------------|-----------|----------------------------------------------|
| `BATCH_PROMPT`        | Round 1   | Independent first-impression reactions         |
| `INTERACTION_PROMPT`  | Round 2   | Reactions to trending posts from Round 1       |
| `CONTINUATION_PROMPT` | Rounds 3+ | Evolving social conversation with history      |

Each prompt includes the book description, persona data, and detailed
instructions for realistic behavior (platform voice matching, critical level
adherence, minimum negative/DNF rates, demographic-aware purchase decisions).

### Expected LLM Output (Round 1)

The LLM returns a JSON array. Each element contains:

```json
{
  "persona_id": 42,
  "star_rating": 3.5,
  "first_impression": "...",
  "social_post": "...",
  "emotional_reaction": "intrigued",
  "would_dnf": false,
  "dnf_reason": null,
  "controversy_flag": "...",
  "quotable_line": "...",
  "recommend_to": "fans of domestic thrillers",
  "would_buy": true,
  "price_willing_to_pay": 14.99
}
```

### JSON Parsing and Repair (`_try_parse_batch`)

LLM JSON output is unreliable. The parser applies multiple fallback strategies:

```
  Raw LLM text
       |
       v
  clean_json_response()
    - Strip <think>...</think> tags (Qwen3 reasoning)
    - Strip markdown ```json fences
    - Try json.loads() directly (handles {"results": [...]} wrappers)
    - Extract [...] substring
    - Fix trailing commas
       |
       v
  json.loads(cleaned)  -- success? return
       |
       v
  Try appending common closers: }], "}], etc.  -- success? return
       |
       v
  Regex-extract individual {"persona_id": ...} objects  -- return partial
       |
       v
  Return None (truly unparseable; batch is skipped)
```

### Retry Logic (`run_batch`)

Each batch gets up to 3 retries with exponential backoff:

- **Parse failure**: 1s, 2s, 4s (max 10s)
- **Rate limit (429/quota)**: 5s, 15s, 30s (max 60s)
- After all retries exhausted: batch is skipped (returns `[]`)

---

## Multi-Round Simulation Engine

```
  Round 1: ALL readers react independently
       |
       v
  score_and_select_trending()  -->  top 15 posts by virality score
       |
       v
  Round 2: ~1/3 of readers react to trending posts (INTERACTION_PROMPT)
       |
       v
  Rounds 3..N: continued social dynamics (CONTINUATION_PROMPT)
       |         - conversation summary built from all previous rounds
       |         - lurkers join gradually (10% chance per round above 2, cap 50%)
       v
  Aggregation
```

### Trending Post Selection

`_score_and_select_trending()` scores each post on a composite virality metric:

| Factor                             | Points |
|------------------------------------|--------|
| Rating extremity (distance from 3) | 0-4    |
| Has controversy flag               | +3     |
| Macro influencer                   | +4     |
| Mid influencer                     | +2     |
| Strong emotion (obsessed/angry/moved) | +2  |
| Viral engagement (went_viral/argued/shared) | +3 |

The top 15 posts become the "trending feed" shown to the next round's readers.

### Active Reader Selection

`_select_active_readers()` determines who participates in social rounds:

- **Base pool**: Non-lurker readers with `critical_level >= 4`
- **Lurker escalation**: From Round 3 onward, lurkers join with probability
  `min(0.1 * (round_num - 2), 0.5)` -- reaching 50% by Round 7
- **Cap**: Active readers are capped at 50% of total reader count
- Pool is shuffled each round for variety

### Conversation Summary

For Rounds 3+, `build_conversation_summary()` builds a compact text digest of
all prior rounds, including dominant sentiment shift, viral post counts, and the
top trending post from each round. This is injected into the
`CONTINUATION_PROMPT` to give the LLM conversational context without exceeding
token limits.

---

## Concurrent Processing Infrastructure

### Thread Safety Classes

```
ThreadSafeResults       Collects batch results from parallel workers
                        Uses threading.Lock around a shared list

TokenCounter            Tracks input/output tokens from all threads
                        Uses threading.Lock around three integer accumulators

RateLimiter             Token-bucket rate limiter
                        Enforces min_interval between calls (default: 1/5s)
                        Adjusts to min(workers * 2, 15) requests/second
```

### Execution Model

```
  Sequential (workers=1, default):
    for batch in batches:
        run_batch(batch)

  Concurrent (workers=2..20):
    ThreadPoolExecutor(max_workers=N)
    rate_limiter = RateLimiter(max_per_second=min(N*2, 15))

    submit all batches --> futures
    as_completed(futures) --> progress updates
```

Round 1 supports both sequential (`run_simulation_round1`) and concurrent
(`run_simulation_round1_concurrent`) execution. Social rounds (2+) run
sequentially because each round depends on the previous round's results.

---

## Aggregation Engine

`aggregate_results()` combines Round 1 data and all social round data into a
single statistics dictionary. It computes:

### Core Metrics

| Metric              | Computation                                              |
|---------------------|----------------------------------------------------------|
| `avg_rating`        | Mean of all Round 1 star ratings (clamped 1.0-5.0)       |
| `rating_distribution` | Histogram bucketed to integers 1-5                     |
| `dnf_rate`          | `dnf_count / total_readers * 100`                        |
| `dnf_reasons`       | List of textual reasons from DNF readers                  |
| `emotions`          | Frequency map of 10 emotional reactions                   |
| `platform_avg_ratings` | Average rating per platform (BookTok, Goodreads, etc.) |

### Social Dynamics Metrics

| Metric              | Computation                                              |
|---------------------|----------------------------------------------------------|
| `sentiment_shifts`  | Accumulated counts: more_positive, more_negative, unchanged, polarized |
| `round_timeline`    | Per-round snapshot: avg_rating, active_readers, shifts, top posts |
| `all_social_posts`  | Every response post from Rounds 2+ with metadata          |

### Confidence Metrics

| Metric              | Computation                                              |
|---------------------|----------------------------------------------------------|
| `consensus_score`   | `max(0, min(100, (1 - stdev/2) * 100))`                  |
| `polarization_index`| `(high_ratings + low_ratings) / mid_ratings`              |
| `margin_of_error`   | `1.96 * (stdev / sqrt(n))` (95% confidence interval)     |

### PRISM Demographic Breakdown

Per demographic segment: average rating, count, DNF rate, top emotion, purchase
rate, and average price willing to pay.

### Virality Score

Composite score (0-100) combining four factors:

```
virality = (positive_pct * 0.35)
         + (emotion_intensity * 0.30)
         + controversy_boost           -- up to 20 points
         + social_boost                -- up to 20 points (from viral engagement)
```

### Purchase Intent

| Metric              | Computation                                              |
|---------------------|----------------------------------------------------------|
| `purchase_rate`     | % of readers who said `would_buy: true`                   |
| `avg_price_willing` | Mean of `price_willing_to_pay` among buyers               |

---

## Report Generation

`report_generator.py` produces a single self-contained HTML file with no
external dependencies. The design is a shadcn/ui-inspired black-and-white
minimal aesthetic with colorful data visualizations.

### Report Sections

| Section              | Content                                                |
|----------------------|--------------------------------------------------------|
| Hero                 | Title, rating, reader count, generation timestamp       |
| Key Stats            | Avg rating, DNF rate, virality score, purchase rate     |
| Book Description     | The input text (or auto-summary)                        |
| Rating Distribution  | Animated horizontal bar chart (1-5 stars)               |
| Emotions             | Frequency bars for 10 emotional reactions                |
| Platform Breakdown   | Per-platform average ratings and sample posts            |
| Demographics (PRISM) | Per-segment ratings, DNF, purchase rates                 |
| Confidence Metrics   | Consensus score, polarization index, margin of error     |
| Purchase Intent      | Buy rate, average price, price distribution               |
| Extremes             | Top 5 harshest reviews and top 5 biggest fans            |
| Social Feed          | Simulated social media timeline across all rounds        |
| Controversies        | Debate points flagged by readers                         |
| DNF Analysis         | DNF rate breakdown and top reasons                       |
| Round Timeline       | Canvas-based chart showing rating evolution per round     |
| Conversation         | Full social round thread with engagement indicators      |
| Virality Gauge       | SVG radial gauge (0-100)                                 |
| Recommendations      | Auto-generated, data-driven author advice                |
| Share Card           | Branded summary card for social sharing                  |

### Visual Features

- Scroll-reveal animations (IntersectionObserver)
- Count-up number animations on key stats
- Animated bar chart fills on scroll
- Canvas-rendered timeline chart for multi-round data
- SVG radial gauge for virality score
- All CSS/JS inline (zero external requests)

### Recommendations Engine

`_generate_recommendations()` analyzes the aggregated statistics and produces
actionable advice. It evaluates:

- Overall rating assessment (strong / polarizing / needs refinement)
- DNF risk analysis with top reasons
- Controversy as marketing opportunity
- Platform-specific targeting advice (strongest vs weakest audience)
- Emotional resonance profile
- Virality potential and launch strategy

---

## Cost Estimation

Before each run, `estimate_run()` calculates projected cost, time, and tokens:

```python
total_batches = ceil(readers / batch_size)                   # Round 1
              + ceil(readers/3 / batch_size) * (rounds - 1)  # Social rounds

est_cost      = total_batches * provider.cost_per_call
est_tokens_in = readers * 300 * rounds
est_tokens_out= readers * 200 * rounds
est_time      = total_batches * sec_per_batch / workers
```

### Pricing Source

`pricing.json` is user-editable and contains per-model cost-per-call estimates:

```json
{
  "ollama":    { "default": 0.000 },
  "gemini":    { "default": 0.001, "gemini-2.5-flash": 0.001 },
  "openai":    { "default": 0.003, "gpt-4o-mini": 0.003 },
  "anthropic": { "default": 0.004, "claude-haiku-4-5-20251001": 0.004 }
}
```

### Speed Benchmarks (seconds per batch)

| Provider  | sec/batch |
|-----------|-----------|
| Ollama    | 8.0       |
| OpenAI    | 3.0       |
| Anthropic | 4.0       |
| Gemini    | 2.5       |

### Confirmation Gate

If the estimated cost exceeds $1.00, the CLI prompts for confirmation before
proceeding.

---

## Auto-Summarization

Texts exceeding 2,000 words are automatically condensed before the simulation
begins. This saves token costs and avoids exceeding provider context limits.

```
  Input text
       |
       v
  Word count > 2,000?
       |
  No --+--> use as-is
       |
  Yes -+--> Truncate to ~15K words (first 7,500 + last 7,500 if longer)
       |
       v
  Send to LLM via SUMMARIZE_PROMPT
       |
       v
  400-600 word synopsis covering: genre, premise, characters,
  tone, themes, tropes, audience, comparables
       |
       v
  Use synopsis for all simulation rounds
```

If summarization fails, the engine falls back to the first 2,000 words of the
original text.

---

## GUI Launcher

`readers_gui.py` provides a Tkinter-based graphical interface for
non-technical users. It wraps the CLI with:

- File picker for book descriptions
- Dropdown selectors for provider, genre, reader count, rounds, workers
- Dependency checker (flags missing pip packages)
- `.env` file status indicator (API key presence)
- Live output log (subprocess stdout piped to a scrolled text widget)
- Themed UI matching the project brand colors (dark background, coral/gold
  accents)

The GUI constructs and spawns `readers.py` as a subprocess, capturing its
output in real time.

---

## Scaling Characteristics

### Projected Performance

| Readers | LLM Calls (2 rounds) | Ollama (local)     | Gemini Flash (cloud) |
|---------|----------------------|--------------------|----------------------|
| 100     | ~25                  | 8-15 min, $0       | ~2 min, ~$0.15       |
| 1,000   | ~270                 | 2-4 hrs, $0        | ~20 min, ~$1.50      |
| 10,000  | ~2,700               | 24-48 hrs, $0      | ~3 hrs, ~$14         |
| 100,000 | ~27,000              | Not practical       | ~30 hrs, ~$140       |

### Scaling Levers

| Parameter     | Range   | Effect                                            |
|---------------|---------|---------------------------------------------------|
| `--readers`   | 1-500K  | Linear increase in LLM calls                       |
| `--batch-size`| 1-20    | Larger batches = fewer calls but more parse failures |
| `--workers`   | 1-20    | Parallel Round 1 execution (social rounds stay sequential) |
| `--rounds`    | 1-100   | Each additional round adds ~1/3 reader-count of calls |

### Bottlenecks

- **Round 1**: Parallelizable. Scales with `--workers`.
- **Social rounds**: Sequential (each depends on previous). Cannot be
  parallelized.
- **JSON parsing**: Larger batches produce longer JSON, increasing parse failure
  rates. Batch size 5 is the recommended sweet spot.
- **Rate limits**: Cloud providers enforce request-per-second caps. The
  `RateLimiter` class throttles to stay under limits.

---

## Dependencies

```
rich>=13.0           Terminal UI (progress bars, panels, tables)
python-dotenv>=1.0   .env file loading for API keys
google-genai>=1.0    Google Gemini SDK
openai>=1.0          OpenAI SDK
anthropic>=0.30      Anthropic SDK
ollama>=0.3          Ollama local inference SDK
```

All provider SDKs are imported lazily inside their respective `__init__`
methods, so only the selected provider's SDK needs to be installed for a given
run. The `rich` and `python-dotenv` packages are soft dependencies: the engine
runs without them, falling back to plain `print` output and manual environment
variables.
