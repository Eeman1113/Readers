# Readers

**Up to 500,000 AI Readers Judge Your Book**

A multi-agent reader simulation engine for indie authors. Simulate hundreds to thousands of AI-generated reader personas reacting to your book description across multiple rounds of social interaction.

Made by **Eeman Majumder**

## Features

- **Multi-Provider Support** — Ollama (free, local), Gemini, OpenAI, Anthropic
- **1,000+ Unique Personas** — Each with distinct personality, platform voice, and reading taste
- **Multi-Round Social Simulation** — Readers react to each other across up to 100 rounds
- **PRISM Demographics** — 8 real market segments with purchase intent prediction
- **Real-Time Token Counter** — Track actual API usage across all providers
- **Premium Reports** — Clean, minimal shadcn-inspired HTML reports with colorful charts
- **Genre-Specific Pools** — Romance, thriller, fantasy, sci-fi, literary, nonfiction, YA
- **Concurrent Processing** — Up to 20 parallel workers for large simulations

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with local Ollama (free)
python readers.py --file examples/my_book_idea.txt --readers 100

# Run with Gemini (recommended, cheapest cloud)
python readers.py --file examples/my_book_idea.txt --provider gemini --readers 1000

# Multi-round with parallel workers
python readers.py --file examples/my_book_idea.txt --provider gemini --readers 1000 --rounds 5 --workers 5
```

## Providers

| Provider | Default Model | Cost/Batch | Speed |
|----------|---------------|------------|-------|
| Ollama | qwen3.5:0.8b | Free | Slow |
| Gemini | gemini-2.5-flash | ~$0.001 | Fast |
| OpenAI | gpt-4o-mini | ~$0.003 | Fast |
| Anthropic | claude-haiku-4-5 | ~$0.004 | Fast |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full technical documentation.

## License

MIT
