# Readers V3 — User Guide
## Up to 500,000 AI Readers Judge Your Book Before You Publish

---

## What Is Readers?

Readers simulates thousands of AI reader personas reacting to your book description.
Each reader has a unique personality, genre preferences, PRISM demographic segment,
platform habits (BookTok, Goodreads, Reddit, etc.), and review style. After their initial
reactions, readers see what others posted and respond — creating realistic social dynamics
like pile-ons, controversy, and viral moments.

V3 adds real market research capabilities: PRISM demographic segmentation shows you which
reader segments love or hate your book, purchase intent prediction tells you if they'd
actually buy, confidence metrics show how reliable the results are, and genre-specific
personas give you feedback from readers who actually read your genre.

The result is a premium animated HTML report with predicted ratings, demographic breakdowns,
simulated social media posts, purchase intent data, controversy points, DNF analysis,
virality scoring, and actionable recommended next steps.

---

## Quick Start (5 Minutes)

### Easiest Way: GUI Launcher (Windows)

1. Make sure Python is installed (see Step 1 below if not)
2. Double-click **`START_HERE.bat`**
3. It will:
   - Check Python is installed
   - Auto-install any missing dependencies
   - Open the Readers GUI window
4. In the GUI:
   - Browse for your book file
   - Pick your AI provider
   - Choose a genre (optional — enhances persona relevance)
   - Set reader count and rounds
   - Click **START SIMULATION**
5. A swarm visualization opens in your browser while you wait
6. Your full report opens automatically when the simulation completes

**That's it!** No terminal commands needed.

---

### Manual Setup (Mac/Linux/Advanced Users)

### Step 1: Install Python

You need Python 3.10 or higher. Check with:
```bash
python3 --version
```

If you don't have it, download from https://python.org (check "Add Python to PATH" during install!)

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the minimum needed for your provider:
```bash
pip install rich python-dotenv    # Required for all providers
pip install google-genai          # For Gemini (recommended)
pip install openai                # For OpenAI
pip install anthropic             # For Anthropic Claude
pip install ollama                # For Ollama (free, local)
```

### Step 3: Configure API Key

Skip this step if using Ollama (it's free and local).

1. Copy `.env.example` to a new file called `.env`
2. Open `.env` in any text editor
3. Uncomment your provider's line and paste your key:

```
# For Gemini (recommended — fast, cheap, free tier available):
GOOGLE_API_KEY=AIzaSy_YOUR_KEY_HERE

# For OpenAI:
# OPENAI_API_KEY=sk-YOUR_KEY_HERE

# For Anthropic:
# ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

4. Save the file. Readers reads it automatically.

**Where to get API keys:**

| Provider | Get Key | Free Tier? |
|----------|---------|------------|
| **Google Gemini** (Recommended) | https://aistudio.google.com/apikey | Yes |
| OpenAI | https://platform.openai.com/api-keys | No |
| Anthropic | https://console.anthropic.com/ | No |

### Step 4: Write Your Book Description

Create a text file (e.g., `my_book.txt`) with **200-2,000 words** covering:
- Title
- Genre
- Premise (2-3 paragraphs)
- Key tropes
- Comp titles (books yours is similar to)
- Tone
- Target audience
- Heat level (if romance)

See `examples/sample_book.txt` for a template.

**Important: What about full manuscripts?**

You CAN upload an entire book or manuscript. If your text is over 2,000 words,
Readers will automatically summarize it into a ~500 word synopsis before
running the simulation. This keeps costs low and speed fast.

However, **we strongly recommend writing your own 200-500 word description instead**.
Why? Because YOU know what makes your book special. A 500-word description you write
will capture your unique selling points better than any auto-summary. Think of it like
writing your back-cover blurb — that's exactly what readers are reacting to.

**Do NOT upload your full manuscript just to test the tool.** It wastes API credits
on the summarization step. Write a blurb instead — it's a useful exercise anyway!

### Step 5: Run It!

```bash
python readers.py --file my_book.txt --provider gemini --readers 200 --rounds 3
```

This runs a 200-reader simulation in ~5 minutes with Gemini. The HTML report opens
automatically in your browser when done.

---

## Genre-Specific Simulations (NEW in V3)

Readers V3 includes persona packs tuned for specific genres. When you select a genre,
readers have genre-appropriate preferences, trope knowledge, and review expectations.

**Available genres:**
- `romance` — BookTok-heavy, spice-aware readers who know their tropes
- `thriller` — Pacing-focused, plot-hole-detecting, Reddit-heavy readers
- `fantasy` — Worldbuilding critics, series-potential evaluators
- `scifi` — Hard vs soft sci-fi readers, tech accuracy checkers
- `literary` — Style-over-plot readers, awards-focused, analytical
- `nonfiction` — Practical value seekers, credibility evaluators
- `ya` — Age-appropriate content aware, coming-of-age focused
- `general` — Default mixed pool (no genre flag needed)

**How to use:**
```bash
# GUI: Select from the Genre dropdown
# Command line:
python readers.py --file my_book.txt --provider gemini --genre romance --readers 1000
```

---

## PRISM Demographic Segmentation (NEW in V3)

Every simulation now includes PRISM demographic breakdown — 8 real market segments:

| Segment | Description |
|---------|-------------|
| **Affluent Bookworms** | Literary fiction lovers, hardcover buyers, high spend |
| **Young Urban Readers** | BookTok-driven, trend followers, ebook/audio |
| **Suburban Families** | Escapism readers, cozy/romance/thriller |
| **Academic Readers** | Critical, awards-focused, literary journals |
| **Budget Readers** | KU subscribers, price-sensitive, high volume |
| **Senior Traditionalists** | 55+, established authors, physical books |
| **Diverse Explorers** | Representation-focused, multicultural |
| **Genre Devotees** | Deep fans, convention-goers, subreddit-active |

Your report shows per-segment ratings, DNF rates, top emotions, and purchase intent.
This tells you exactly which reader demographics to target in your marketing.

---

## All Command-Line Options

```bash
python readers.py [OPTIONS]

Required (one of):
  "text"              Book description as text
  --file, -f PATH     Path to book description file

Provider Options:
  --provider, -p      ollama (default), openai, anthropic, gemini
  --model, -m         Model name (default depends on provider)
  --api-key, -k       API key for cloud providers

Simulation Options:
  --readers, -r       Number of readers: 50-500,000 (default: 1000)
  --batch-size, -b    Personas per LLM call (default: 5)
  --rounds            1-100 (default: 2)
  --genre, -g         Genre preset: romance, thriller, fantasy, scifi,
                      literary, nonfiction, ya, general (default: general)
  --workers, -w       Parallel API calls: 1-20 (default: 1, GUI default: 5)

Output Options:
  --output, -o        Custom output path for the report
  --no-open           Don't auto-open report in browser
  --ollama-host       Custom Ollama host URL
```

---

## Understanding the Report

### Average Rating
The mean star rating across all readers. A book rated 3.8+ by 1,000 diverse readers
is generally well-positioned. Below 3.0 signals significant audience mismatch.

### PRISM Demographic Breakdown (NEW)
Per-segment ratings and reactions. If Affluent Bookworms rate you 4.5 but Budget Readers
rate you 2.1, your book may be priced wrong or marketed to the wrong audience.

### Purchase Intent (NEW)
Would readers actually buy? What price would they pay? Per-segment purchase rates
help you set pricing and target your ads.

### Confidence Metrics (NEW)
- **Consensus Score** — How much readers agree (high = reliable prediction)
- **Polarization Index** — Love-it-or-hate-it factor
- **Margin of Error** — Statistical confidence range
- **Sample Confidence** — Based on reader count

### Genre Benchmark (NEW)
Your rating compared to the average for your genre on Goodreads. Green if you're above
average, red if below. Helps calibrate expectations.

### DNF Rate (Did Not Finish)
Percentage of readers who would quit before finishing. Under 10% is excellent.
10-20% is normal. Over 20% suggests structural or genre-fit problems.

### Virality Score (0-100)
Composite metric based on: percentage of high ratings, emotional intensity of reactions,
number of controversy points, and social round engagement. Above 70 = strong viral potential.

### Platform Breakdown
How each social media platform's readers reacted differently. BookTok skews emotional
and positive. Reddit skews critical and analytical. Useful for targeting your marketing.

### Multi-Round Social Simulation
After initial reactions, readers see each other's most viral posts and respond across
multiple rounds. This reveals whether your book creates consensus or polarization.
Polarization is often better for virality.

### Recommended Next Steps (NEW)
Data-driven action items based on your specific results. Includes targeting advice,
DNF fixes, controversy strategy, platform recommendations, and pricing guidance.

### Share Card
Screenshot-ready summary at the bottom of every report. Share on social media to
show your prediction results.

---

## Scaling Up

### Reader Count Recommendations

| Readers | Best For | Time (Gemini, 5 workers) | Cost (Gemini) |
|---------|----------|--------------------------|---------------|
| 100 | Quick test, iterating on blurbs | ~1-2 min | ~$0.03 |
| 500 | Solid directional signal | ~3-5 min | ~$0.12 |
| 1,000 | Standard simulation (default) | ~5-10 min | ~$0.25 |
| 5,000 | Deep demographic analysis | ~20-40 min | ~$1.25 |
| 10,000 | Deep statistical confidence | ~40-80 min | ~$2.50 |
| 50,000 | Enterprise-level analysis | ~3-6 hours | ~$12.50 |
| 100,000 | Large-scale simulation | ~6-12 hours | ~$25 |
| 500,000 | Maximum scale | ~1-3 days | ~$125 |

> **Speed tip:** Use `--workers 5` (default in GUI) to run 5 API calls in parallel. This is 3-5x faster than single-threaded mode. For 10K+ readers, try `--workers 10`.

### Worker Recommendations

| Workers | Best For |
|---------|----------|
| 1 | Troubleshooting, very slow connections |
| 3 | Conservative — safe for all providers and free tiers |
| **5** | **Recommended default — good balance of speed and reliability** |
| 10 | 5K-10K+ reader runs — fast with paid API tiers |
| 15-20 | 50K+ reader runs — only if your API quota supports it |

> **Note:** If you see lots of "Rate limited" warnings, reduce workers. The GUI defaults to 5 which works well for most users.

### Round Recommendations

| Rounds | Best For |
|--------|----------|
| 1 | Quick first impressions only |
| 2-3 | Standard (recommended for most users) |
| 5 | See how opinions evolve |
| 10 | Deep social dynamics analysis |
| 10+ | Diminishing returns — only if you're curious |

---

## Tips for Best Results

1. **More detail = better simulation.** Include tropes, comp titles, tone, and heat level.
2. **Use genre-specific personas.** `--genre romance` gives you readers who know romance tropes, not sci-fi readers confused by a love story.
3. **Run it multiple times.** LLMs have randomness. Run 2-3 times to see which patterns are consistent vs. random.
4. **Test different versions.** Change your blurb and run again. Compare reports to see which version resonates better.
5. **The harshest reviews are the most valuable.** They tell you exactly what a real critic would say, so you can address those issues before publishing.
6. **Check the demographic breakdown.** If one segment loves you and another hates you, that's valuable targeting intel — not a problem to fix.
7. **Purchase intent is directional, not exact.** Use it to compare versions of your blurb, not as a sales forecast.

---

## Troubleshooting

**"Connection refused" or "Ollama not found"**
Make sure Ollama is running: `ollama serve` in a separate terminal.

**JSON parse errors / reader dropout**
The LLM sometimes outputs invalid JSON. The script auto-retries failed batches up to 3 times
with exponential backoff. If you're still getting significant dropout (e.g., 1000 requested
but only 600 returned), try: (1) reducing batch size: `--batch-size 3`, (2) reducing workers
if you see "Rate limited" warnings: `--workers 3`, or (3) using Gemini 2.5 Pro instead of
Flash for better JSON compliance: `--model gemini-2.5-pro`.

**Out of memory**
Use a smaller model: `ollama pull qwen2.5:7b` and add `--model qwen2.5:7b`.

**Slow performance**
Use `--workers 5` (default in GUI) to parallelize API calls — this is 3-5x faster.
Ollama runs much faster with a GPU. On CPU-only, expect 3-5x slower.
Use a cloud API (Gemini recommended) for best speed.

**10,000+ reader runs taking forever**
Use parallel workers: `--workers 10`. This makes 10 API calls simultaneously instead of
one at a time. A 10K reader run with 5 workers takes ~40-80 minutes vs. 3-5 hours with 1 worker.

**GUI won't open**
Run `pip install rich python-dotenv google-genai` manually, then try again.
Or use the command-line: `python readers.py --file my_book.txt --provider gemini`

---

## File Structure

```
Readers/
├── START_HERE.bat           # GUI launcher (Windows) — double-click to start
├── run_readers.bat          # Command-line launcher with prompts
├── readers_gui.py           # Graphical user interface
├── readers.py               # Main simulation engine
├── report_generator.py      # Premium animated HTML report builder
├── generate_personas.py     # Persona generator (create custom counts/genres)
├── swarm_visualization.html # Animated swarm visualization
├── personas.json            # 1,000 general reader personas (default)
├── personas_5000.json       # 5,000 reader personas
├── personas_10000.json      # 10,000 reader personas
├── personas_romance.json    # 1,000 romance-tuned readers
├── personas_thriller.json   # 1,000 thriller-tuned readers
├── personas_fantasy.json    # 1,000 fantasy-tuned readers
├── personas_scifi.json      # 1,000 sci-fi-tuned readers
├── personas_literary.json   # 1,000 literary fiction-tuned readers
├── personas_nonfiction.json # 1,000 nonfiction-tuned readers
├── personas_ya.json         # 1,000 YA-tuned readers
├── .env.example             # API key template (copy to .env)
├── requirements.txt         # Python package list
├── examples/
│   ├── sample_book.txt      # Example book description
│   └── my_book_idea.txt     # Another example
├── output/                  # Reports saved here (auto-created)
├── README.md                # Quick start guide
└── USERGUIDE.md             # This file
```

---

## Security Note

Your `.env` file is gitignored and never included in any shared files. Your API keys
are only used for the duration of the simulation and passed directly to the provider.
Never share your `.env` file or paste keys into public places.

---

## Credits

Made by **Eeman Majumder**

You own your reports. Use them however you want.

---

*Readers simulates plausible reader reactions using AI. Results are predictions,
not guarantees. Real readers may react differently. Use as one data point among many
in your publishing decisions.*
