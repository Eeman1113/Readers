#!/usr/bin/env python3
"""
Readers — Up to 500,000 AI Readers Judge Your Book
Multi-agent reader simulation engine for indie authors.

Usage:
    # Quick test (100 readers, free via Ollama)
    python readers.py --file my_book.txt --readers 100

    # Full simulation (1,000 readers, high quality)
    python readers.py --file my_book.txt

    # With cloud API (set keys in .env file — see .env.example)
    python readers.py --file my_book.txt --provider gemini
    python readers.py --file my_book.txt --provider anthropic
    python readers.py --file my_book.txt --provider openai

    # Multi-round social simulation (1-30 rounds)
    python readers.py --file my_book.txt --rounds 5

    # Custom settings
    python readers.py --file my_book.txt --batch-size 5 --model qwen2.5:32b
"""

import json
import os  # paths
import sys
import time

# Force UTF-8 output on Windows to prevent cp1252 crashes with Unicode/emoji characters
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import argparse
import re
import webbrowser
import urllib.parse
import random
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Load .env file if present (keeps API keys out of terminal history)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — env vars still work

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("⚠️  Install 'rich' for beautiful terminal output: pip install rich")

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

DEFAULT_BATCH_SIZE = 5  # 5 = best balance of speed + reliability (10 causes dropouts with some providers)
DEFAULT_READER_COUNT = 1000
SCRIPT_DIR = Path(__file__).parent

def _load_pricing() -> dict:
    """Load cost-per-call estimates from pricing.json (editable by users)."""
    pricing_file = SCRIPT_DIR / "pricing.json"
    if pricing_file.exists():
        try:
            with open(pricing_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback defaults if file is missing or corrupt
    return {
        "ollama": {"default": 0.0},
        "gemini": {"default": 0.001},
        "openai": {"default": 0.003},
        "anthropic": {"default": 0.004}
    }

PRICING = _load_pricing()

def get_personas_path(reader_count: int, genre: str = None) -> Path:
    """Auto-detect the best persona file for the requested reader count and genre."""
    # Genre-specific files first
    if genre and genre != "general":
        genre_file = SCRIPT_DIR / f"personas_{genre}.json"
        if genre_file.exists():
            return genre_file
        genre_count_file = SCRIPT_DIR / f"personas_{genre}_{reader_count}.json"
        if genre_count_file.exists():
            return genre_count_file

    # Try exact match first (e.g., personas_5000.json)
    exact = SCRIPT_DIR / f"personas_{reader_count}.json"
    if exact.exists():
        return exact
    # Try the largest available file (for 500K+ we want the biggest pool)
    for size in [10000, 5000, 1000]:
        candidate = SCRIPT_DIR / f"personas_{size}.json" if size != 1000 else SCRIPT_DIR / "personas.json"
        if candidate.exists() and size >= reader_count:
            return candidate
    # For counts > 10K, use the largest file available (will be cycled in load_personas)
    for size in [10000, 5000]:
        candidate = SCRIPT_DIR / f"personas_{size}.json"
        if candidate.exists():
            return candidate
    # Fall back to default
    return SCRIPT_DIR / "personas.json"

console = Console() if HAS_RICH else None

# -------------------------------------------------------------------
# PROVIDER ABSTRACTION (Ollama, OpenAI, Anthropic, Gemini)
# -------------------------------------------------------------------

class LLMProvider:
    """Base class for LLM providers."""
    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "qwen3.5:0.8b", host: str = None):
        import ollama as _ollama
        self.client = _ollama
        self.model = model
        self.name = f"Ollama ({model})"
        prices = PRICING.get("ollama", {})
        self.cost_per_call = prices.get(model, prices.get("default", 0.0))
        if host:
            os.environ["OLLAMA_HOST"] = host
    
    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        # ORIGINAL:
        # response = self.client.chat(
        #     model=self.model,
        #     messages=[{"role": "user", "content": prompt}],
        #     options={"temperature": 0.8, "num_predict": max_tokens}
        # )
        # return response["message"]["content"]

        # FIX: Use think=False to disable Qwen3 reasoning (returns empty content otherwise)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a JSON generator. You MUST output ONLY valid JSON arrays. No explanation, no markdown. Output starts with [ and ends with ]."},
                {"role": "user", "content": prompt},
            ],
            format="json",
            think=False,
            options={"temperature": 0.7, "num_predict": max_tokens}
        )
        # Track tokens — Ollama returns prompt_eval_count / eval_count
        inp = getattr(response, 'prompt_eval_count', 0) or 0
        out = getattr(response, 'eval_count', 0) or 0
        token_counter.add(inp, out)
        return response.message.content


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.name = f"OpenAI ({model})"
        prices = PRICING.get("openai", {})
        self.cost_per_call = prices.get(model, prices.get("default", 0.003))

    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.8
        )
        # Track tokens — OpenAI returns usage.prompt_tokens / completion_tokens
        if response.usage:
            token_counter.add(response.usage.prompt_tokens or 0,
                              response.usage.completion_tokens or 0)
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.name = f"Anthropic ({model})"
        prices = PRICING.get("anthropic", {})
        self.cost_per_call = prices.get(model, prices.get("default", 0.004))

    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        # Track tokens — Anthropic returns usage.input_tokens / output_tokens
        if response.usage:
            token_counter.add(response.usage.input_tokens or 0,
                              response.usage.output_tokens or 0)
        return response.content[0].text


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.name = f"Gemini ({model})"
        prices = PRICING.get("gemini", {})
        self.cost_per_call = prices.get(model, prices.get("default", 0.001))

    def chat(self, prompt: str, max_tokens: int = 8192) -> str:
        from google.genai import types
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",  # Force valid JSON output
            )
        )
        # Track tokens — Gemini returns usage_metadata.prompt_token_count / candidates_token_count
        meta = getattr(response, 'usage_metadata', None)
        if meta:
            token_counter.add(getattr(meta, 'prompt_token_count', 0) or 0,
                              getattr(meta, 'candidates_token_count', 0) or 0)
        return response.text


def get_provider(provider_name: str, model: str = None, api_key: str = None, host: str = None) -> LLMProvider:
    """Factory to create the right provider."""
    if provider_name == "ollama":
        return OllamaProvider(model=model or "qwen3.5:0.8b", host=host)
    elif provider_name == "openai":
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI requires --api-key or OPENAI_API_KEY env var")
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
    elif provider_name == "anthropic":
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic requires --api-key or ANTHROPIC_API_KEY env var")
        return AnthropicProvider(api_key=api_key, model=model or "claude-haiku-4-5-20251001")
    elif provider_name == "gemini":
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Gemini requires --api-key or GOOGLE_API_KEY env var")
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use: ollama, openai, anthropic, gemini")


# -------------------------------------------------------------------
# PROMPT TEMPLATES
# -------------------------------------------------------------------

BATCH_PROMPT = """You are simulating {count} different book readers. Each has a unique personality, reading taste, and review style. For each reader, generate their authentic reaction to discovering this book.

BOOK DESCRIPTION:
---
{book_description}
---

READER PERSONAS:
{personas_json}

For EACH reader above, return a JSON object with these exact fields:
- "persona_id": (integer, from the input)
- "star_rating": (number 1.0-5.0, use decimals like 3.5, be REALISTIC)
- "first_impression": (1-2 sentences in their authentic voice and platform style)
- "social_post": (what they'd ACTUALLY post on their platform — match the platform voice exactly)
- "emotional_reaction": (ONE of: "excited", "bored", "angry", "moved", "confused", "meh", "obsessed", "disappointed", "intrigued", "uncomfortable")
- "would_dnf": (boolean true/false)
- "dnf_reason": (string if would_dnf is true, null otherwise)
- "controversy_flag": (string describing what might spark debate, or null)
- "quotable_line": (which phrase from the description they'd screenshot/share, or null)
- "recommend_to": (what type of reader they'd recommend this to, or "nobody")
- "would_buy": (boolean — would they actually purchase this book based on the description?)
- "price_willing_to_pay": (number 0-30 — max dollars they'd pay. 0 if they wouldn't buy. Consider their price_sensitivity and preferred_formats)

CRITICAL RULES — FOLLOW THESE OR THE SIMULATION IS USELESS:
1. DO NOT make everyone positive. Real books get 1-star reviews. At least 15-20% should rate below 3 stars.
2. At least 5-10% should DNF (would_dnf: true).
3. BookTok readers: ALL CAPS, emojis, dramatic ("this DESTROYED me")
4. Goodreads readers: measured, comparative ("reminiscent of [Author] but with more...")
5. Reddit readers: skeptical, discussion-oriented ("Am I the only one who thinks...")
6. Bookstagram readers: aesthetic/mood-focused ("perfect autumn read vibes")
7. X/Twitter readers: hot takes, punchy, quotable
8. Lurkers: just a star rating and maybe 3 words
9. Snarky reviewers should be GENUINELY funny and cutting, not mean-spirited
10. Match critical_level: a critic at 9/10 should be harsh. A 2/10 should love almost everything.
11. Each persona's reaction must feel DIFFERENT from the others.
12. Consider demographic_segment and price_sensitivity for purchase decisions. Budget Readers want KU or under $5. Affluent Bookworms will pay $25+ for hardcovers. Academic Readers buy based on literary merit.

Return ONLY a valid JSON array of objects. No markdown formatting, no ```json blocks, no explanation text. Just the raw JSON array starting with [ and ending with ]."""


INTERACTION_PROMPT = """You are simulating {count} book readers who have ALREADY read initial reactions from other readers about a book. Now they are responding to the social media conversation.

BOOK DESCRIPTION:
---
{book_description}
---

TRENDING POSTS FROM ROUND 1 (the posts these readers are reacting to):
---
{trending_posts}
---

READER PERSONAS FOR THIS BATCH:
{personas_json}

Each reader has now seen the trending posts above. Based on their personality and the social dynamics, generate their RESPONSE. They might:
- Agree with a popular opinion and amplify it
- Push back against a hot take they disagree with
- Pile onto a controversy
- Change their initial rating after seeing others' perspectives
- Quote-tweet or reply to a specific post

For EACH reader, return a JSON object:
- "persona_id": (integer)
- "updated_star_rating": (may shift from round 1 based on social influence, or stay the same)
- "response_post": (their social media response to the conversation — reference specific posts they're reacting to)
- "responding_to": (name of the reader whose post they're engaging with, or "general")
- "sentiment_shift": (one of: "more_positive", "more_negative", "unchanged", "polarized")
- "viral_engagement": (one of: "ignored", "liked", "shared", "argued", "went_viral")

RULES:
1. Social proof matters — some readers will shift toward the majority opinion
2. Contrarians will push HARDER against popular takes
3. BookTok readers pile on fast. Reddit readers debate.
4. At least 20% should disagree with the trending sentiment
5. Some lurkers will finally speak up if the controversy is juicy enough

Return ONLY a valid JSON array. No markdown, no explanation."""


CONTINUATION_PROMPT = """You are simulating {count} book readers in Round {round_num} of {total_rounds} of an ongoing social media conversation about a book. The conversation has been building for multiple rounds and opinions are evolving.

BOOK DESCRIPTION:
---
{book_description}
---

CONVERSATION SO FAR:
{conversation_summary}

LATEST TRENDING POSTS (from the previous round — these are what readers are reacting to NOW):
---
{trending_posts}
---

READER PERSONAS FOR THIS BATCH:
{personas_json}

This is Round {round_num}. The conversation has momentum. Generate each reader's LATEST response. At this point:
- Pile-ons may be growing — popular opinions attract more agreement
- Contrarians are digging in harder or finding new angles to argue
- NEW sub-controversies may emerge from the conversation itself (not just the book)
- Some readers who were quiet earlier may finally speak up
- Hot takes are getting hotter. Nuanced takes are getting more nuanced.
- Readers may reference earlier rounds ("I said this in Round 1 and I stand by it" or "I changed my mind after reading what [Name] said")

For EACH reader, return a JSON object:
- "persona_id": (integer)
- "updated_star_rating": (may shift further based on the evolving conversation)
- "response_post": (their social media response — must reference specific posts or trends from the conversation)
- "responding_to": (name of the reader whose post they're engaging with, or "general")
- "sentiment_shift": (one of: "more_positive", "more_negative", "unchanged", "polarized")
- "viral_engagement": (one of: "ignored", "liked", "shared", "argued", "went_viral")

RULES:
1. Do NOT just repeat earlier sentiments. Each round should add NEW perspectives or escalate existing ones.
2. At least 20% should push back against the dominant opinion.
3. Reference specific names and posts — make it feel like a real conversation thread.
4. Some readers may flip their opinion entirely based on compelling arguments they saw.
5. Platform voice must match: BookTok=dramatic, Reddit=debate, Goodreads=thoughtful, X=hot takes, Bookstagram=aesthetic.

Return ONLY a valid JSON array. No markdown, no explanation."""


# -------------------------------------------------------------------
# GENRE BENCHMARKS (real Goodreads averages for comparison)
# -------------------------------------------------------------------

GENRE_BENCHMARKS = {
    "romance": 3.82, "thriller": 3.65, "fantasy": 3.88, "scifi": 3.72,
    "literary": 3.55, "nonfiction": 3.68, "ya": 3.78, "general": 3.70,
    "Contemporary Romance": 3.82, "Dark Romance": 3.75, "Romantic Fantasy": 3.85,
    "Cozy Mystery": 3.80, "Psychological Thriller": 3.65, "Epic Fantasy": 3.90,
    "Sci-Fi": 3.72, "Literary Fiction": 3.55, "Horror": 3.60,
    "Historical Fiction": 3.78, "Memoir": 3.70, "Self-Help": 3.65,
    "YA Fantasy": 3.78, "YA Contemporary": 3.72, "Urban Fantasy": 3.75,
    "Dystopian": 3.68, "Crime Fiction": 3.62, "Women's Fiction": 3.75,
    "Mystery": 3.70, "Paranormal Romance": 3.72, "LitRPG": 3.80,
    "Romantasy": 3.85, "Sapphic Romance": 3.88, "MM Romance": 3.82,
    "Grimdark": 3.78, "Hard Sci-Fi": 3.68, "Space Opera": 3.75,
    "Cyberpunk": 3.70, "Steampunk": 3.68, "Magical Realism": 3.72,
    "Southern Gothic": 3.65, "Domestic Thriller": 3.62, "True Crime": 3.58,
    "Cozy Fantasy": 3.82, "Spicy Romance": 3.78,
}

PROVIDER_SPEED_BENCHMARKS = {
    "ollama": 8.0, "openai": 3.0, "anthropic": 4.0, "gemini": 2.5,
}


# -------------------------------------------------------------------
# CONCURRENT PROCESSING INFRASTRUCTURE
# -------------------------------------------------------------------

class ThreadSafeResults:
    """Thread-safe result collector for parallel batch processing."""
    def __init__(self):
        self._lock = threading.Lock()
        self._results = []
        self._completed = 0

    def add(self, batch_results: list):
        with self._lock:
            self._results.extend(batch_results)
            self._completed += 1

    @property
    def results(self):
        with self._lock:
            return list(self._results)

    @property
    def completed(self):
        with self._lock:
            return self._completed


class TokenCounter:
    """Thread-safe real-time token counter for tracking actual API usage."""
    def __init__(self):
        self._lock = threading.Lock()
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_calls = 0

    def add(self, input_tokens: int = 0, output_tokens: int = 0):
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_calls += 1

    @property
    def total_tokens(self):
        with self._lock:
            return self.input_tokens + self.output_tokens

    def snapshot(self):
        with self._lock:
            return {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
                "total_calls": self.total_calls,
            }

    def format_live(self):
        s = self.snapshot()
        return f"🔢 {s['total_tokens']:,} tokens (in: {s['input_tokens']:,} | out: {s['output_tokens']:,}) · {s['total_calls']} calls"


# Global token counter — updated by all providers in real-time
token_counter = TokenCounter()


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    def __init__(self, max_per_second: float = 5.0):
        self._lock = threading.Lock()
        self._min_interval = 1.0 / max_per_second
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.time()


def estimate_run(provider_name: str, provider, readers: int,
                 batch_size: int, rounds: int, workers: int) -> dict:
    """Estimate time, cost, and tokens for a simulation run."""
    total_batches_r1 = (readers + batch_size - 1) // batch_size
    active_r2_est = readers // 3
    batches_per_social = (active_r2_est + batch_size - 1) // batch_size
    social_rounds = max(0, rounds - 1)
    total_batches = total_batches_r1 + batches_per_social * social_rounds

    sec_per_batch = PROVIDER_SPEED_BENCHMARKS.get(provider_name, 5.0)
    effective_speed = sec_per_batch / max(workers, 1)
    est_seconds = total_batches * effective_speed

    est_cost = total_batches * provider.cost_per_call
    est_tokens_in = readers * 300 * rounds
    est_tokens_out = readers * 200 * rounds

    return {
        "total_batches": total_batches,
        "est_seconds": est_seconds,
        "est_cost": est_cost,
        "est_tokens_in": est_tokens_in,
        "est_tokens_out": est_tokens_out,
    }


# -------------------------------------------------------------------
# ENGINE
# -------------------------------------------------------------------

def load_personas(path: Path, count: int = 1000) -> list:
    """Load personas, cycling and diversifying if count exceeds file size.
    Supports up to 500,000 readers by recycling the persona pool with variation."""
    with open(path, encoding="utf-8") as f:
        all_personas = json.load(f)

    if count <= len(all_personas):
        return all_personas[:count]

    # For counts > persona file size: cycle through personas with slight variation
    # Each cycle gets shuffled differently so batches aren't identical
    result = []
    cycle = 0
    while len(result) < count:
        pool = list(all_personas)  # copy
        random.shuffle(pool)
        for p in pool:
            if len(result) >= count:
                break
            # Create a varied copy — new persona_id, slight critical_level jitter
            varied = dict(p)
            varied["persona_id"] = len(result) + 1
            varied["_cycle"] = cycle
            # Slight variation in critical level (+/- 1, clamped 1-10)
            crit = varied.get("critical_level", 5)
            varied["critical_level"] = max(1, min(10, crit + random.choice([-1, 0, 0, 1])))
            result.append(varied)
        cycle += 1

    return result


def create_batch_payload(personas: list) -> str:
    condensed = []
    for p in personas:
        entry = {
            "persona_id": p["persona_id"],
            "name": p["name"],
            "age_range": p["age_range"],
            "platform": p["platform"],
            "primary_genre": p["primary_genre"],
            "preferred_genres": p["preferred_genres"],
            "trope_loves": p["trope_loves"],
            "trope_hates": p["trope_hates"],
            "critical_level": p["critical_level"],
            "review_style": p["review_style"],
            "dnf_threshold": p["dnf_threshold"],
            "influence_level": p["influence_level"],
            "bio": p["bio"],
            "platform_voice": p["platform_voice"],
            # V3: PRISM demographic data
            "demographic_segment": p.get("demographic_segment", "General"),
            "price_sensitivity": p.get("segment_data", {}).get("price_sensitivity", "medium"),
            "preferred_formats": p.get("segment_data", {}).get("preferred_formats", []),
        }
        condensed.append(entry)
    return json.dumps(condensed, indent=1)


def clean_json_response(text: str) -> str:
    # ORIGINAL:
    # def clean_json_response(text: str) -> str:
    #     text = re.sub(r'```json\s*', '', text)
    #     text = re.sub(r'```\s*', '', text)
    #     text = text.strip()
    #
    #     start = text.find('[')
    #     end = text.rfind(']')
    #     if start != -1 and end != -1:
    #         text = text[start:end+1]
    #
    #     # Fix common LLM JSON issues
    #     text = re.sub(r',\s*}', '}', text)  # trailing commas in objects
    #     text = re.sub(r',\s*]', ']', text)  # trailing commas in arrays
    #
    #     return text

    # FIX: Strip Qwen3 <think>...</think> reasoning tags that corrupt JSON output
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # FIX: Handle JSON object wrapping an array (e.g. {"results": [...]} or {"readers": [...]})
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, list):
                    return json.dumps(v)
        if isinstance(obj, list):
            return json.dumps(obj)
    except (json.JSONDecodeError, ValueError):
        pass

    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1:
        text = text[start:end+1]

    # Fix common LLM JSON issues
    text = re.sub(r',\s*}', '}', text)  # trailing commas in objects
    text = re.sub(r',\s*]', ']', text)  # trailing commas in arrays

    return text


def _try_parse_batch(raw_text: str, batch_num: int) -> list:
    """Attempt to parse LLM JSON response with repair fallbacks."""
    cleaned = clean_json_response(raw_text)

    try:
        results = json.loads(cleaned)
        if isinstance(results, list):
            return results
        # FIX: Single object — wrap in list (small models sometimes return one object instead of array)
        # ORIGINAL: (not present — only checked for list)
        if isinstance(results, dict) and "persona_id" in results:
            return [results]
    except json.JSONDecodeError:
        pass

    # Try common repair closers
    for closer in ['}]', '"}]', '", "recommend_to": "nobody"}]', 'null}]',
                   '"nobody"}]', ': null}]', '": "nobody"}]']:
        try:
            results = json.loads(cleaned + closer)
            if isinstance(results, list):
                if console:
                    console.print(f"  [yellow]⚠ Batch {batch_num}: JSON repaired[/yellow]")
                return results
        except:
            continue

    # FIX: Last resort — regex-extract individual JSON objects from broken array
    # ORIGINAL: (not present — function returned None here)
    extracted = []
    for m in re.finditer(r'\{[^{}]*"persona_id"\s*:\s*\d+[^{}]*\}', cleaned):
        try:
            obj = json.loads(m.group())
            extracted.append(obj)
        except json.JSONDecodeError:
            continue
    if extracted:
        if console:
            console.print(f"  [yellow]⚠ Batch {batch_num}: Extracted {len(extracted)} objects from broken JSON[/yellow]")
        return extracted

    return None  # Truly unparseable


def run_batch(provider: LLMProvider, prompt: str, batch_num: int, total_batches: int,
              max_retries: int = 3) -> list:
    """Run a single batch through the LLM provider with retry + exponential backoff."""
    for attempt in range(1 + max_retries):
        try:
            raw_text = provider.chat(prompt)
            results = _try_parse_batch(raw_text, batch_num)

            if results is not None:
                return results

            # Failed to parse
            if attempt < max_retries:
                wait = min(2 ** attempt, 10)  # 1s, 2s, 4s, max 10s
                if console:
                    console.print(f"  [yellow]⚠ Batch {batch_num}: JSON parse failed, retry {attempt+1}/{max_retries} in {wait}s...[/yellow]")
                time.sleep(wait)
            else:
                if console:
                    console.print(f"  [red]✗ Batch {batch_num}: Could not parse after {1+max_retries} attempts. Skipping.[/red]")
                return []

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "rate" in err_str or "429" in err_str or "quota" in err_str or "resource" in err_str
            if attempt < max_retries:
                # Longer backoff for rate limits (5s, 15s, 30s), shorter for other errors (1s, 2s, 4s)
                if is_rate_limit:
                    wait = min(5 * (2 ** attempt), 60)
                    if console:
                        console.print(f"  [yellow]⚠ Batch {batch_num}: Rate limited, waiting {wait}s before retry {attempt+1}/{max_retries}...[/yellow]")
                else:
                    wait = min(2 ** attempt, 10)
                    if console:
                        console.print(f"  [yellow]⚠ Batch {batch_num} error, retry {attempt+1}/{max_retries} in {wait}s: {e}[/yellow]")
                time.sleep(wait)
            else:
                if console:
                    console.print(f"  [red]✗ Batch {batch_num} error after {1+max_retries} attempts: {e}[/red]")
                return []

    return []


def run_simulation_round1(provider: LLMProvider, book_description: str, personas: list, batch_size: int) -> list:
    """Round 1: Initial reader reactions to the book."""
    batches = [personas[i:i+batch_size] for i in range(0, len(personas), batch_size)]
    total = len(batches)
    all_results = []

    if console and HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[tokens]}[/dim]"),
            console=console
        ) as progress:
            task = progress.add_task("Round 1: First impressions...", total=total, tokens="0 tokens")

            for i, batch in enumerate(batches):
                sample = batch[0]
                progress.update(task, description=f"R1 [{i+1}/{total}] {sample['name']} ({sample['platform']})...")

                prompt = BATCH_PROMPT.format(
                    count=len(batch),
                    book_description=book_description,
                    personas_json=create_batch_payload(batch)
                )
                results = run_batch(provider, prompt, i+1, total)
                all_results.extend(results)
                progress.update(task, tokens=f"{token_counter.total_tokens:,} tokens")
                progress.advance(task)
    else:
        for i, batch in enumerate(batches):
            print(f"  Round 1 - Batch {i+1}/{total}... [{token_counter.total_tokens:,} tokens]", flush=True)
            prompt = BATCH_PROMPT.format(
                count=len(batch),
                book_description=book_description,
                personas_json=create_batch_payload(batch)
            )
            results = run_batch(provider, prompt, i+1, total)
            all_results.extend(results)

    return all_results


def run_simulation_round1_concurrent(provider: LLMProvider, book_description: str,
                                      personas: list, batch_size: int, workers: int = 5) -> list:
    """Round 1 with parallel batch processing for large reader counts."""
    batches = [personas[i:i+batch_size] for i in range(0, len(personas), batch_size)]
    total = len(batches)
    collector = ThreadSafeResults()
    rate_limiter = RateLimiter(max_per_second=min(workers * 2, 15))

    def process_batch(batch_idx, batch):
        rate_limiter.wait()
        prompt = BATCH_PROMPT.format(
            count=len(batch),
            book_description=book_description,
            personas_json=create_batch_payload(batch)
        )
        results = run_batch(provider, prompt, batch_idx + 1, total)
        collector.add(results)
        return len(results)

    if console and HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[tokens]}[/dim]"),
            console=console
        ) as progress:
            task = progress.add_task(f"Round 1: {workers} workers...", total=total, tokens="0 tokens")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(process_batch, i, batch): i for i, batch in enumerate(batches)}
                for future in as_completed(futures):
                    future.result()
                    progress.update(task, tokens=f"{token_counter.total_tokens:,} tokens")
                    progress.advance(task)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_batch, i, batch): i for i, batch in enumerate(batches)}
            for future in as_completed(futures):
                idx = futures[future]
                future.result()
                print(f"  Round 1 - Batch {idx+1}/{total} complete [{token_counter.total_tokens:,} tokens]", flush=True)

    return collector.results


def _score_and_select_trending(results: list, persona_map: dict, count: int = 15) -> tuple:
    """Score posts by virality potential and return top trending posts + formatted text."""
    scored_posts = []
    for r in results:
        p = persona_map.get(r.get("persona_id"), {})
        score = 0
        rating = r.get("star_rating") or r.get("updated_star_rating") or 3
        score += abs(rating - 3) * 2
        if r.get("controversy_flag"):
            score += 3
        if p.get("influence_level") == "macro":
            score += 4
        elif p.get("influence_level") == "mid":
            score += 2
        if r.get("emotional_reaction") in ("obsessed", "angry", "moved"):
            score += 2
        # For round 2+ posts, boost viral engagement
        if r.get("viral_engagement") in ("went_viral", "argued", "shared"):
            score += 3

        post_text = r.get("social_post", r.get("response_post", ""))
        scored_posts.append({
            "name": p.get("name", "Reader"),
            "platform": p.get("platform", ""),
            "rating": rating,
            "post": post_text,
            "controversy": r.get("controversy_flag"),
            "emotion": r.get("emotional_reaction", ""),
            "score": score
        })

    scored_posts.sort(key=lambda x: x["score"], reverse=True)
    trending = scored_posts[:count]
    trending_text = "\n\n".join([
        f"[{t['platform']}] {t['name']} (★{t['rating']}): {t['post']}"
        + (f"\n  ⚡ Controversy: {t['controversy']}" if t['controversy'] else "")
        for t in trending
    ])
    return trending, trending_text


def _select_active_readers(personas: list, round_num: int) -> list:
    """Select readers who will participate in a social round. Later rounds pull in more lurkers."""
    active_readers = [p for p in personas if p["review_style"] != "lurker" and p["critical_level"] >= 4]
    # From round 3+, lurkers start joining (10% chance per lurker per round above 2)
    if round_num >= 3:
        lurkers = [p for p in personas if p["review_style"] == "lurker"]
        lurker_chance = min(0.1 * (round_num - 2), 0.5)  # caps at 50% by round 7
        for lurker in lurkers:
            if random.random() < lurker_chance:
                active_readers.append(lurker)
    random.shuffle(active_readers)
    return active_readers[:min(len(active_readers), len(personas) // 2)]


def _run_social_round(provider: LLMProvider, prompt_template: str, prompt_kwargs: dict,
                      readers: list, batch_size: int, round_num: int, round_label: str) -> list:
    """Generic runner for social interaction rounds (2+)."""
    batches = [readers[i:i+batch_size] for i in range(0, len(readers), batch_size)]
    total = len(batches)
    all_results = []

    if console:
        console.print(f"\n🔄 Round {round_num}: {len(readers)} readers reacting to trending posts...")

    if console and HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[tokens]}[/dim]"),
            console=console
        ) as progress:
            task = progress.add_task(f"{round_label}...", total=total, tokens=f"{token_counter.total_tokens:,} tokens")

            for i, batch in enumerate(batches):
                sample = batch[0]
                progress.update(task, description=f"R{round_num} [{i+1}/{total}] {sample['name']} reacting...")

                prompt = prompt_template.format(
                    **prompt_kwargs,
                    count=len(batch),
                    personas_json=create_batch_payload(batch)
                )
                results = run_batch(provider, prompt, i+1, total)
                all_results.extend(results)
                progress.update(task, tokens=f"{token_counter.total_tokens:,} tokens")
                progress.advance(task)
    else:
        for i, batch in enumerate(batches):
            print(f"  Round {round_num} - Batch {i+1}/{total}... [{token_counter.total_tokens:,} tokens]", flush=True)
            prompt = prompt_template.format(
                **prompt_kwargs,
                count=len(batch),
                personas_json=create_batch_payload(batch)
            )
            results = run_batch(provider, prompt, i+1, total)
            all_results.extend(results)

    return all_results


def run_simulation_round2(provider: LLMProvider, book_description: str, personas: list,
                          round1_results: list, batch_size: int) -> tuple:
    """Round 2: Readers react to each other's posts (interaction round)."""
    persona_map = {p["persona_id"]: p for p in personas}
    trending, trending_text = _score_and_select_trending(round1_results, persona_map)
    active_readers = _select_active_readers(personas, 2)

    results = _run_social_round(
        provider, INTERACTION_PROMPT,
        {"book_description": book_description, "trending_posts": trending_text},
        active_readers, batch_size, 2, "Round 2: Social reactions"
    )
    return results, trending


def run_simulation_round_n(provider: LLMProvider, book_description: str, personas: list,
                           previous_results: list, round_num: int, total_rounds: int,
                           batch_size: int, conversation_summary: str = "") -> tuple:
    """Rounds 3+: Continued social conversation with evolving dynamics."""
    persona_map = {p["persona_id"]: p for p in personas}
    trending, trending_text = _score_and_select_trending(previous_results, persona_map)
    active_readers = _select_active_readers(personas, round_num)

    results = _run_social_round(
        provider, CONTINUATION_PROMPT,
        {
            "book_description": book_description,
            "trending_posts": trending_text,
            "round_num": round_num,
            "total_rounds": total_rounds,
            "conversation_summary": conversation_summary
        },
        active_readers, batch_size, round_num, f"Round {round_num}: Conversation evolving"
    )
    return results, trending


def build_conversation_summary(round_data: list) -> str:
    """Build a compact summary of the conversation across all rounds so far."""
    lines = []
    for rd in round_data:
        rn = rd["round"]
        results = rd["results"]
        shifts = {"more_positive": 0, "more_negative": 0, "unchanged": 0, "polarized": 0}
        for r in results:
            s = r.get("sentiment_shift", "unchanged")
            if s in shifts:
                shifts[s] += 1
        viral_count = sum(1 for r in results if r.get("viral_engagement") in ("went_viral", "argued", "shared"))
        dominant = max(shifts, key=shifts.get) if shifts else "unchanged"
        lines.append(f"Round {rn}: {len(results)} active readers. Dominant shift: {dominant}. {viral_count} viral/argued posts.")
        # Include top trending post
        if rd.get("trending") and len(rd["trending"]) > 0:
            top = rd["trending"][0]
            lines.append(f"  Top post: [{top.get('platform','')}] {top.get('name','')}: \"{top.get('post','')[:100]}...\"")
    return "\n".join(lines)


# -------------------------------------------------------------------
# AGGREGATION (same as before but enhanced with round 2 data)
# -------------------------------------------------------------------

def aggregate_results(round1: list, round_data: list, personas: list) -> dict:
    """Aggregate results from Round 1 and all subsequent social rounds."""
    persona_map = {p["persona_id"]: p for p in personas}

    # Enrich round 1
    for r in round1:
        pid = r.get("persona_id")
        if pid and pid in persona_map:
            r["_persona"] = persona_map[pid]

    # Sanitize ratings: coerce to float, discard non-numeric ("N/A", "Five stars", etc.)
    ratings = []
    for r in round1:
        raw = r.get("star_rating")
        if raw is None:
            continue
        try:
            val = float(raw)
            val = max(1.0, min(5.0, val))  # clamp to valid range
            r["star_rating"] = val  # write back the cleaned value
            ratings.append(val)
        except (TypeError, ValueError):
            r.pop("star_rating", None)  # remove junk so downstream code skips it

    # Rating distribution
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in ratings:
        bucket = max(1, min(5, round(rating)))
        rating_dist[bucket] += 1

    # DNF analysis
    dnf_count = sum(1 for r in round1 if r.get("would_dnf"))
    dnf_reasons = [r.get("dnf_reason", "unspecified") for r in round1 if r.get("would_dnf") and r.get("dnf_reason")]

    # Emotions
    emotions = {}
    for r in round1:
        em = r.get("emotional_reaction", "unknown")
        emotions[em] = emotions.get(em, 0) + 1

    # Platform breakdown
    platform_ratings = {}
    platform_posts = {}
    for r in round1:
        p = r.get("_persona", {})
        plat = p.get("platform", "Unknown")
        if plat not in platform_ratings:
            platform_ratings[plat] = []
            platform_posts[plat] = []
        if "star_rating" in r:
            platform_ratings[plat].append(r["star_rating"])
        if r.get("social_post"):
            platform_posts[plat].append({
                "name": p.get("name", "Anonymous"),
                "post": r["social_post"],
                "rating": r.get("star_rating", 0),
                "style": p.get("review_style", ""),
                "influence": p.get("influence_level", "micro")
            })

    platform_avg = {plat: sum(rats)/len(rats) for plat, rats in platform_ratings.items() if rats}

    # Controversies
    controversies = [r.get("controversy_flag") for r in round1 if r.get("controversy_flag")]

    # Extremes
    sorted_by_rating = sorted([r for r in round1 if "star_rating" in r], key=lambda x: x["star_rating"])
    harshest = sorted_by_rating[:5]
    biggest_fans = sorted_by_rating[-5:][::-1]

    # === Multi-round aggregation ===
    total_rounds = 1 + len(round_data)
    sentiment_shifts = {"more_positive": 0, "more_negative": 0, "unchanged": 0, "polarized": 0}
    all_social_posts = []  # Posts from all social rounds
    round_timeline = [{
        "round": 1,
        "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
        "active_readers": len(round1),
        "sentiment_shifts": None,
        "top_trending": []
    }]

    total_viral_posts = 0

    for rd in round_data:
        rn = rd["round"]
        results = rd["results"]
        trending = rd.get("trending", [])

        # Per-round sentiment
        round_shifts = {"more_positive": 0, "more_negative": 0, "unchanged": 0, "polarized": 0}
        round_ratings = []

        for r in results:
            shift = r.get("sentiment_shift", "unchanged")
            if shift in round_shifts:
                round_shifts[shift] += 1
                sentiment_shifts[shift] += 1

            # Sanitize updated_star_rating the same way we sanitize star_rating
            raw_usr = r.get("updated_star_rating")
            if raw_usr is not None:
                try:
                    val = float(raw_usr)
                    val = max(1.0, min(5.0, val))
                    r["updated_star_rating"] = val
                    round_ratings.append(val)
                except (TypeError, ValueError):
                    r.pop("updated_star_rating", None)

            if r.get("response_post"):
                p = persona_map.get(r.get("persona_id"), {})
                all_social_posts.append({
                    "round": rn,
                    "name": p.get("name", "Reader"),
                    "platform": p.get("platform", ""),
                    "post": r.get("response_post", ""),
                    "responding_to": r.get("responding_to", "general"),
                    "engagement": r.get("viral_engagement", "liked"),
                    "rating_shift": r.get("updated_star_rating")
                })

            if r.get("viral_engagement") in ("shared", "went_viral", "argued"):
                total_viral_posts += 1

        round_timeline.append({
            "round": rn,
            "avg_rating": sum(round_ratings) / len(round_ratings) if round_ratings else None,
            "active_readers": len(results),
            "sentiment_shifts": round_shifts,
            "top_trending": [t.get("post", "")[:80] for t in trending[:3]]
        })

    # Virality score (accumulated across all rounds)
    positive_pct = sum(1 for r in ratings if r >= 4.0) / max(len(ratings), 1) * 100
    controversy_boost = min(len(controversies) / max(len(round1), 1) * 200, 20)
    emotion_intensity = sum(1 for r in round1 if r.get("emotional_reaction") in ("obsessed", "excited", "angry", "moved")) / max(len(round1), 1) * 100
    total_social_readers = sum(len(rd["results"]) for rd in round_data) if round_data else 1
    social_boost = min(total_viral_posts / max(total_social_readers, 1) * 100, 20)
    virality_score = min(100, (positive_pct * 0.35) + (emotion_intensity * 0.3) + controversy_boost + social_boost)

    # Legacy compatibility: round2_posts for report (first social round's posts)
    round2_posts = [p for p in all_social_posts if p["round"] == 2][:20]
    round2_count = len(round_data[0]["results"]) if round_data else 0

    # === V3: PRISM DEMOGRAPHIC BREAKDOWN ===
    segment_ratings = {}
    segment_dnf = {}
    segment_emotions = {}
    segment_purchases = {}
    for r in round1:
        p = r.get("_persona", {})
        seg = p.get("demographic_segment", "General")
        if seg not in segment_ratings:
            segment_ratings[seg] = []
            segment_dnf[seg] = {"total": 0, "dnf": 0}
            segment_emotions[seg] = {}
            segment_purchases[seg] = {"would_buy": 0, "total": 0, "prices": []}

        if "star_rating" in r:
            segment_ratings[seg].append(r["star_rating"])
        segment_dnf[seg]["total"] += 1
        if r.get("would_dnf"):
            segment_dnf[seg]["dnf"] += 1
        em = r.get("emotional_reaction", "unknown")
        segment_emotions[seg][em] = segment_emotions[seg].get(em, 0) + 1
        segment_purchases[seg]["total"] += 1
        if r.get("would_buy"):
            segment_purchases[seg]["would_buy"] += 1
        if r.get("price_willing_to_pay") and r.get("would_buy"):
            segment_purchases[seg]["prices"].append(r["price_willing_to_pay"])

    demographic_breakdown = {}
    for seg in segment_ratings:
        rats = segment_ratings[seg]
        d = segment_dnf[seg]
        emos = segment_emotions[seg]
        top_emotion = max(emos, key=emos.get) if emos else "unknown"
        purchases = segment_purchases[seg]
        demographic_breakdown[seg] = {
            "avg_rating": round(sum(rats) / len(rats), 2) if rats else 0,
            "count": len(rats),
            "dnf_rate": round(d["dnf"] / max(d["total"], 1) * 100, 1),
            "top_emotion": top_emotion,
            "purchase_rate": round(purchases["would_buy"] / max(purchases["total"], 1) * 100, 1),
            "avg_price": round(sum(purchases["prices"]) / len(purchases["prices"]), 2) if purchases["prices"] else 0,
        }

    # === V3: CONFIDENCE METRICS ===
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    if len(ratings) >= 2:
        stddev = statistics.stdev(ratings)
        consensus_score = round(max(0, min(100, (1 - stddev / 2) * 100)), 1)
        se = stddev / (len(ratings) ** 0.5)
        margin_of_error = round(1.96 * se, 2)
        sample_confidence = round(max(0, min(100, (1 - margin_of_error) * 100)), 1)
    else:
        consensus_score = 0
        margin_of_error = 999
        sample_confidence = 0

    high_r = sum(1 for r in ratings if r >= 4.0)
    low_r = sum(1 for r in ratings if r <= 2.0)
    mid_r = sum(1 for r in ratings if 2.0 < r < 4.0)
    polarization_index = round((high_r + low_r) / max(mid_r, 1), 2) if mid_r > 0 else 0

    # === V3: PURCHASE INTENT ===
    total_buyers = sum(1 for r in round1 if r.get("would_buy"))
    purchase_rate = round(total_buyers / max(len(round1), 1) * 100, 1)
    buyer_prices = [r.get("price_willing_to_pay", 0) for r in round1 if r.get("would_buy") and r.get("price_willing_to_pay")]
    avg_price_willing = round(sum(buyer_prices) / len(buyer_prices), 2) if buyer_prices else 0

    return {
        "total_readers": len(round1),
        "avg_rating": avg_rating,
        "rating_distribution": rating_dist,
        "dnf_count": dnf_count,
        "dnf_rate": dnf_count / max(len(round1), 1) * 100,
        "dnf_reasons": dnf_reasons,
        "emotions": dict(sorted(emotions.items(), key=lambda x: -x[1])),
        "platform_avg_ratings": platform_avg,
        "platform_posts": platform_posts,
        "controversies": controversies[:20],
        "harshest_reviews": harshest,
        "biggest_fans": biggest_fans,
        "trending_posts": round_data[0]["trending"] if round_data else [],
        "round2_posts": round2_posts,
        "all_social_posts": all_social_posts,
        "sentiment_shifts": sentiment_shifts,
        "virality_score": round(virality_score, 1),
        "round2_count": round2_count,
        "total_rounds": total_rounds,
        "round_timeline": round_timeline,
        # V3: PRISM demographics
        "demographic_breakdown": demographic_breakdown,
        # V3: Confidence metrics
        "consensus_score": consensus_score,
        "polarization_index": polarization_index,
        "margin_of_error": margin_of_error,
        "sample_confidence": sample_confidence,
        # V3: Purchase intent
        "purchase_rate": purchase_rate,
        "avg_price_willing": avg_price_willing,
        "all_results": round1
    }


# -------------------------------------------------------------------
# REPORT GENERATION (imported from external file to keep this clean)
# -------------------------------------------------------------------

def generate_report(stats: dict, book_description: str, output_path: Path, provider_name: str) -> Path:
    """Generate the HTML report. Imports from report_generator.py if available, 
    otherwise falls back to inline generation."""
    
    report_module = SCRIPT_DIR / "report_generator.py"
    if report_module.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("report_generator", report_module)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.generate_report(stats, book_description, output_path, provider_name)
    
    # Fallback: minimal report
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Readers Report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:20px;background:#fafafa;color:#09090b;}}
h1{{color:#09090b;}}h2{{color:#09090b;border-bottom:1px solid #e4e4e7;padding-bottom:8px;}}
.stat{{display:inline-block;background:#fff;border:1px solid #e4e4e7;padding:16px;margin:8px;border-radius:12px;text-align:center;min-width:150px;}}
.stat-val{{font-size:2em;font-weight:bold;}}
.stat-label{{font-size:0.8em;color:#71717a;}}
.post{{background:#fff;border:1px solid #e4e4e7;border-radius:8px;padding:12px;margin:8px 0;}}
.post-meta{{font-size:0.8em;color:#71717a;margin-bottom:4px;}}</style></head>
<body>
<h1>Readers Report — {stats['total_readers']} Readers</h1>
<p style="color:#8888aa;">Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} via {provider_name}</p>

<div>
<div class="stat"><div class="stat-val">{stats['avg_rating']:.1f}</div><div class="stat-label">Avg Rating</div></div>
<div class="stat"><div class="stat-val">{stats['dnf_rate']:.0f}%</div><div class="stat-label">DNF Rate</div></div>
<div class="stat"><div class="stat-val">{stats['virality_score']:.0f}</div><div class="stat-label">Virality</div></div>
<div class="stat"><div class="stat-val">{len(stats['controversies'])}</div><div class="stat-label">Controversies</div></div>
</div>

<h2>Rating Distribution</h2>"""
    
    dist = stats["rating_distribution"]
    max_c = max(dist.values()) if dist.values() else 1
    for star in range(5, 0, -1):
        c = dist.get(star, 0)
        pct = c / max(stats["total_readers"], 1) * 100
        bar = "█" * int(c / max_c * 40)
        html += f"<p style='font-family:monospace;'>{star}★ {bar} {c} ({pct:.0f}%)</p>"
    
    html += "<h2>Simulated Social Feed</h2>"
    all_posts = []
    for plat, posts in stats["platform_posts"].items():
        for p in posts:
            p["platform"] = plat
            all_posts.append(p)
    for post in all_posts[:30]:
        html += f"""<div class="post"><div class="post-meta">{post.get('platform','')} · {post.get('name','')} · {'★'*round(post.get('rating',3))} {post.get('rating',0)}</div><div>{post.get('post','')}</div></div>"""
    
    if stats.get("round2_posts"):
        html += "<h2>Round 2: Social Reactions</h2>"
        html += f"<p style='color:#8888aa;'>After seeing trending posts, {stats['round2_count']} readers reacted:</p>"
        shifts = stats["sentiment_shifts"]
        html += f"<p>📈 More positive: {shifts.get('more_positive',0)} · 📉 More negative: {shifts.get('more_negative',0)} · ➡️ Unchanged: {shifts.get('unchanged',0)} · ⚡ Polarized: {shifts.get('polarized',0)}</p>"
        for rp in stats["round2_posts"][:15]:
            html += f"""<div class="post" style="border-left:3px solid #60a5fa;"><div class="post-meta">↩️ Responding to {rp.get('responding_to','general')} · {rp.get('platform','')} · {rp.get('name','')}</div><div>{rp.get('post','')}</div></div>"""
    
    if stats["controversies"]:
        html += "<h2>Controversy Radar</h2>"
        for c in stats["controversies"][:10]:
            html += f"<div class='post' style='border-left:3px solid #f59e0b;'>⚡ {c}</div>"
    
    html += f"""
<h2>Viral Potential: {stats['virality_score']:.0f}/100</h2>
<p style="font-size:3em;text-align:center;">{'🔥' if stats['virality_score'] >= 70 else '📈' if stats['virality_score'] >= 40 else '📉'} {stats['virality_score']:.0f}</p>

<div style="text-align:center;padding:40px;border-top:1px solid #2a2a3e;margin-top:40px;color:#8888aa;">
<p style="font-size:2em;">📖</p>
<p><strong>Readers</strong> — AI Reader Simulation Engine</p>
</div>
</body></html>"""
    
    with open(output_path, "w") as f:
        f.write(html)
    return output_path


# -------------------------------------------------------------------
# TEXT PREPROCESSING
# -------------------------------------------------------------------

MAX_DESCRIPTION_WORDS = 2000  # Anything longer gets auto-summarized

SUMMARIZE_PROMPT = """You are a book analysis assistant. The user has provided a very long text (possibly an entire book or manuscript). Your job is to create a comprehensive book description/synopsis that captures everything a reader would need to form an opinion.

TEXT TO SUMMARIZE:
---
{text}
---

Create a 400-600 word book description that includes:
1. Title and genre (if apparent)
2. Main premise and plot summary (no major spoilers, but cover the key arcs)
3. Main characters and their dynamics
4. Tone, writing style, and pacing
5. Key themes and tropes
6. Target audience
7. Comparable titles (if you can identify them)
8. Any notable elements (heat level for romance, violence level for thrillers, etc.)

Write it as a cohesive book description, NOT a bullet list. This will be used to simulate reader reactions, so make it detailed enough that someone could form a genuine opinion about whether they'd enjoy the book.

Return ONLY the description text. No preamble, no "Here's the summary", just the description."""


def auto_summarize_if_needed(text: str, provider: LLMProvider) -> tuple:
    """If text exceeds MAX_DESCRIPTION_WORDS, auto-summarize it using the LLM.
    Returns (processed_text, was_summarized, original_word_count)."""
    word_count = len(text.split())

    if word_count <= MAX_DESCRIPTION_WORDS:
        return text, False, word_count

    # Text is too long — summarize it
    if console:
        console.print(f"\n[bold yellow]📝 Input text is {word_count:,} words — auto-summarizing to save costs...[/bold yellow]")
        console.print(f"[dim]   (Texts over {MAX_DESCRIPTION_WORDS:,} words are automatically condensed into a synopsis)[/dim]")

    # Truncate to ~15K words for the summarizer prompt (avoid hitting context limits)
    words = text.split()
    if len(words) > 15000:
        truncated = " ".join(words[:7500]) + "\n\n[...middle section omitted for length...]\n\n" + " ".join(words[-7500:])
    else:
        truncated = text

    try:
        summary = provider.chat(SUMMARIZE_PROMPT.format(text=truncated), max_tokens=2000)
        summary = summary.strip()
        summary_words = len(summary.split())

        if console:
            console.print(f"[green]✅ Summarized {word_count:,} words → {summary_words} word synopsis[/green]")
            console.print()

        return summary, True, word_count

    except Exception as e:
        if console:
            console.print(f"[red]⚠ Auto-summary failed: {e}[/red]")
            console.print(f"[yellow]  Falling back to first {MAX_DESCRIPTION_WORDS} words...[/yellow]")

        # Fallback: just use the first MAX_DESCRIPTION_WORDS words
        truncated_text = " ".join(words[:MAX_DESCRIPTION_WORDS])
        return truncated_text, True, word_count


# -------------------------------------------------------------------
# TERMINAL DISPLAY HELPERS
# -------------------------------------------------------------------

PLATFORM_EMOJI = {
    "BookTok": "📱", "Goodreads": "📚", "Reddit": "💬",
    "Bookstagram": "📸", "X_Twitter": "𝕏", "Lurker": "👻"
}

BANNER_ART = """[bold bright_yellow]
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   📖  [bold white]R E A D E R S[/bold white]                                       ║
    ║   [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]   ║
    ║   [#fbbf24]Up to 500,000 AI Readers Judge Your Book[/#fbbf24]                ║
    ║   [dim]Multi-Round Social Simulation Engine[/dim]                     ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝[/bold bright_yellow]"""


def show_persona_breakdown(personas: list):
    """Display a cinematic demographic breakdown of loaded personas."""
    if not (console and HAS_RICH):
        print(f"Loaded {len(personas)} personas.")
        return

    # Platform counts
    plat_counts = {}
    age_counts = {}
    style_counts = {}
    total_crit = 0
    for p in personas:
        plat_counts[p["platform"]] = plat_counts.get(p["platform"], 0) + 1
        age_counts[p["age_range"]] = age_counts.get(p["age_range"], 0) + 1
        style_counts[p["review_style"]] = style_counts.get(p["review_style"], 0) + 1
        total_crit += p["critical_level"]

    table = Table(title=f"[bold]👥 {len(personas):,} Reader Personas Loaded[/bold]",
                  border_style="bright_yellow", show_header=True, header_style="bold")
    table.add_column("Platform", style="bold")
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("", width=1)
    table.add_column("Age Range", style="bold")
    table.add_column("Count", justify="right", style="cyan")

    plat_sorted = sorted(plat_counts.items(), key=lambda x: -x[1])
    age_sorted = sorted(age_counts.items())

    max_rows = max(len(plat_sorted), len(age_sorted))
    for i in range(max_rows):
        plat_name = ""
        plat_ct = ""
        age_name = ""
        age_ct = ""
        if i < len(plat_sorted):
            p, c = plat_sorted[i]
            emoji = PLATFORM_EMOJI.get(p, "📖")
            plat_name = f"{emoji} {p.replace('_', '/')}"
            plat_ct = f"{c:,}"
        if i < len(age_sorted):
            a, c = age_sorted[i]
            age_name = a
            age_ct = f"{c:,}"
        table.add_row(plat_name, plat_ct, "│", age_name, age_ct)

    table.add_section()
    avg_crit = total_crit / len(personas) if personas else 0
    table.add_row("Avg Critical Level", f"{avg_crit:.1f}/10", "│",
                  "Review Styles", str(len(style_counts)))

    console.print()
    console.print(table)
    console.print()


def show_round_summary(round_num: int, results: list, elapsed: float, persona_map: dict):
    """Show a cinematic between-round summary panel."""
    if not (console and HAS_RICH):
        print(f"Round {round_num}: {len(results)} responses in {elapsed:.0f}s")
        return

    shifts = {"more_positive": 0, "more_negative": 0, "unchanged": 0, "polarized": 0}
    ratings = []
    for r in results:
        s = r.get("sentiment_shift", "unchanged")
        if s in shifts:
            shifts[s] += 1
        rat = r.get("updated_star_rating", r.get("star_rating"))
        if rat is not None:
            try:
                ratings.append(float(rat))
            except (ValueError, TypeError):
                pass

    avg = sum(ratings) / len(ratings) if ratings else 0
    stars = "★" * int(avg) + ("½" if (avg - int(avg)) >= 0.25 else "") + "☆" * (5 - int(avg) - (1 if (avg - int(avg)) >= 0.25 else 0))

    tc = token_counter.snapshot()
    summary = f"[bold]{stars} {avg:.2f}[/bold] avg rating  ·  {len(results)} responses  ·  {elapsed:.0f}s\n"
    summary += f"📈 [green]+{shifts['more_positive']}[/green]  📉 [red]-{shifts['more_negative']}[/red]  ➡️ {shifts['unchanged']}  ⚡ [yellow]{shifts['polarized']}[/yellow] polarized\n"
    summary += f"🔢 [bold]{tc['total_tokens']:,}[/bold] tokens (in: {tc['input_tokens']:,} | out: {tc['output_tokens']:,})"

    panel_title = f"Round {round_num} Complete"
    color = "bright_yellow" if round_num == 1 else "cyan" if round_num == 2 else "magenta"
    console.print()
    console.print(Panel(summary, title=f"[bold]✅ {panel_title}[/bold]", border_style=color))


def show_final_reveal(stats: dict, total_time: float, est_cost: float, provider_name: str,
                      total_calls: int, report_path: Path, json_path: Path, no_open: bool):
    """Cinematic post-simulation reveal."""
    if not (console and HAS_RICH):
        print(f"\nAvg Rating: {stats['avg_rating']:.2f}")
        print(f"DNF Rate: {stats['dnf_rate']:.1f}%")
        print(f"Virality: {stats['virality_score']:.0f}/100")
        print(f"Report: {report_path}")
        return

    console.print()
    console.print("[bold bright_yellow]" + "━" * 60 + "[/bold bright_yellow]")
    console.print("[bold bright_yellow]  📖  SIMULATION COMPLETE  [/bold bright_yellow]")
    console.print("[bold bright_yellow]" + "━" * 60 + "[/bold bright_yellow]")
    console.print()

    time.sleep(0.3)

    # Big rating reveal
    avg = stats["avg_rating"]
    stars = "★" * int(avg) + ("½" if (avg - int(avg)) >= 0.25 else "") + "☆" * (5 - int(avg) - (1 if (avg - int(avg)) >= 0.25 else 0))
    console.print(f"  [bold #fbbf24]{stars}[/bold #fbbf24]")
    console.print(f"  [bold #fbbf24 on default]{avg:.2f}[/bold #fbbf24 on default] [dim]average rating across {stats['total_readers']:,} readers[/dim]")
    time.sleep(0.3)

    console.print()
    console.print(f"  📉 [bold]{stats['dnf_rate']:.1f}%[/bold] DNF rate [dim]({stats['dnf_count']} would quit)[/dim]")
    time.sleep(0.2)

    vs = stats["virality_score"]
    vl = "🔥 VIRAL" if vs >= 70 else "📈 Moderate Buzz" if vs >= 40 else "📉 Niche Appeal"
    console.print(f"  {vl} [bold]{vs:.0f}[/bold]/100 virality score")
    time.sleep(0.2)

    console.print(f"  ⚡ [bold]{len(stats['controversies'])}[/bold] controversy points")
    console.print(f"  🔄 [bold]{stats['total_rounds']}[/bold] rounds of social simulation")
    time.sleep(0.2)

    console.print()

    # Summary table
    table = Table(title="[bold]📊 Full Results[/bold]", border_style="yellow", show_header=True)
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_row("Average Rating", f"{stars} {avg:.2f}")
    table.add_row("Total Readers", f"{stats['total_readers']:,}")
    table.add_row("Rounds", str(stats["total_rounds"]))
    table.add_row("Social Reactions", str(sum(len(rd) for rd in [stats.get("all_social_posts", [])])))
    table.add_row("DNF Rate", f"{stats['dnf_rate']:.1f}%")
    table.add_row("Virality Score", f"{vs:.0f}/100")
    table.add_row("Controversies", str(len(stats["controversies"])))
    table.add_row("Provider", provider_name)
    table.add_row("Total Time", f"{total_time:.0f}s ({total_time/60:.1f} min)")
    if est_cost > 0:
        table.add_row("Est. Cost", f"${est_cost:.2f}")
    table.add_row("LLM Calls", str(total_calls))
    tc = token_counter.snapshot()
    table.add_row("Total Tokens", f"{tc['total_tokens']:,}")
    table.add_row("  Input Tokens", f"{tc['input_tokens']:,}")
    table.add_row("  Output Tokens", f"{tc['output_tokens']:,}")
    console.print(table)

    console.print()
    console.print(f"  🎨 [bold green]Report saved:[/bold green] {report_path}")
    console.print(f"  📄 [dim]Raw data:[/dim] {json_path}")

    if not no_open:
        console.print()
        for i in range(3, 0, -1):
            console.print(f"  [dim]Opening report in browser... {i}[/dim]", end="\r")
            time.sleep(0.4)
        console.print("  [bold]🌐 Opening report in browser...    [/bold]")


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="📖 Readers — Up to 500,000 AI Readers Judge Your Book"
    )
    parser.add_argument("description", nargs="?", help="Book description text")
    parser.add_argument("--file", "-f", help="Path to book description file")
    parser.add_argument("--provider", "-p", default="ollama",
                        choices=["ollama", "openai", "anthropic", "gemini"],
                        help="LLM provider (default: ollama)")
    parser.add_argument("--model", "-m", default=None, help="Model name (provider-specific)")
    parser.add_argument("--api-key", "-k", default=None, help="API key for cloud providers (BYOK)")
    parser.add_argument("--batch-size", "-b", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Personas per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--readers", "-r", type=int, default=DEFAULT_READER_COUNT,
                        help=f"Number of readers (default: {DEFAULT_READER_COUNT})")
    parser.add_argument("--rounds", type=int, default=2,
                        help="Simulation rounds 1-100: 1=reactions, 2+=social interaction (default: 2)")
    parser.add_argument("--genre", "-g", default=None,
                        choices=["romance", "thriller", "fantasy", "scifi", "literary", "nonfiction", "ya", "general"],
                        help="Use genre-tuned persona pool with PRISM demographics")
    parser.add_argument("--workers", "-w", type=int, default=1,
                        help="Parallel workers for batch processing (1-20, default: 1)")
    parser.add_argument("--output", "-o", default=None, help="Output report path")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open report")
    parser.add_argument("--ollama-host", default=None, help="Ollama host URL")

    args = parser.parse_args()

    if args.rounds < 1 or args.rounds > 100:
        parser.error("--rounds must be between 1 and 100")
    if args.workers < 1 or args.workers > 20:
        parser.error("--workers must be between 1 and 20")

    # Get book description
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            book_description = f.read().strip()
    elif args.description:
        book_description = args.description
    else:
        print("Error: Provide a book description or use --file")
        sys.exit(1)

    # Initialize provider
    try:
        provider = get_provider(args.provider, args.model, args.api_key, args.ollama_host)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Auto-summarize long texts (e.g., full manuscripts)
    book_description, was_summarized, original_word_count = auto_summarize_if_needed(book_description, provider)

    # Output path — reports go to output/ folder to keep project clean
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = SCRIPT_DIR / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"readers_report_{timestamp}.html"

    # === CINEMATIC BANNER ===
    if console and HAS_RICH:
        console.print(BANNER_ART)
        console.print()
    elif console:
        console.print(Panel.fit(
            "[bold]📖 Readers[/bold]\n[dim]Up to 500,000 AI Readers Judge Your Book[/dim]",
            border_style="bright_yellow"
        ))
    else:
        print("📖 Readers — Up to 500,000 AI Readers Judge Your Book")

    # Load personas (genre-aware)
    genre = args.genre if args.genre != "general" else None
    personas_path = get_personas_path(args.readers, genre=genre)
    personas = load_personas(personas_path, args.readers)
    show_persona_breakdown(personas)

    # Pre-run estimate
    est = estimate_run(args.provider, provider, len(personas), args.batch_size, args.rounds, args.workers)
    total_calls = est["total_batches"]
    est_cost = est["est_cost"]

    if console:
        console.print(f"📖 Book: [dim]{book_description[:80]}{'...' if len(book_description) > 80 else ''}[/dim]")
        console.print(f"🤖 Provider: [bold]{provider.name}[/bold]")
        console.print(f"👥 Readers: [bold]{len(personas):,}[/bold] | Batch size: [bold]{args.batch_size}[/bold]" +
                       (f" | Workers: [bold]{args.workers}[/bold]" if args.workers > 1 else ""))
        if genre:
            console.print(f"📚 Genre: [bold magenta]{genre}[/bold magenta] (PRISM demographics enabled)")
        rounds_desc = "reactions only" if args.rounds == 1 else f"reactions + {args.rounds - 1} social round{'s' if args.rounds > 2 else ''}"
        console.print(f"🔄 Rounds: [bold]{args.rounds}[/bold] ({rounds_desc})")
        console.print(f"⏱️  Est. time: [bold]{est['est_seconds']/60:.1f} minutes[/bold]")
        console.print(f"📊 Est. LLM calls: [bold]~{total_calls}[/bold]")
        if est_cost > 0:
            console.print(f"💰 Estimated cost: [bold]${est_cost:.2f}[/bold]")
        else:
            console.print(f"💰 Cost: [bold green]FREE (local Ollama)[/bold green]")
        console.print()

        # Confirmation for expensive runs
        if est_cost > 1.0 and not args.no_open:
            confirm = input("Proceed? (Y/n): ").strip().lower()
            if confirm in ("n", "no"):
                console.print("[yellow]Aborted.[/yellow]")
                sys.exit(0)
    else:
        print(f"Provider: {provider.name} | Readers: {len(personas)} | Rounds: {args.rounds} | Est. calls: ~{total_calls}")

    # Open swarm visualization while simulation runs (eye candy for the wait)
    # swarm_viz = SCRIPT_DIR / "swarm_visualization.html"
    # if not args.no_open and swarm_viz.exists():
    #     if console:
    #         console.print("🐝 [dim]Opening swarm visualization while you wait...[/dim]")
    #     genre = getattr(args, 'genre', 'general') or 'general'
    #     viz_params = urllib.parse.urlencode({
    #         "readers": len(personas), "rounds": args.rounds,
    #         "genre": genre, "provider": provider.name
    #     })
    #     viz_url = swarm_viz.resolve().as_uri() + "?" + viz_params
    #     webbrowser.open(viz_url)

    # Reset token counter for this run
    global token_counter
    token_counter = TokenCounter()

    # ━━━ ROUND 1: First Impressions ━━━
    start_time = time.time()

    if console:
        console.print("\n[bold yellow]━━━ ROUND 1: First Impressions ━━━[/bold yellow]\n")
    else:
        print("--- ROUND 1: First Impressions ---")

    if args.workers > 1:
        round1_results = run_simulation_round1_concurrent(
            provider, book_description, personas, args.batch_size, args.workers)
    else:
        round1_results = run_simulation_round1(provider, book_description, personas, args.batch_size)

    r1_time = time.time() - start_time

    # Build persona map for summaries
    persona_map = {p["persona_id"]: p for p in personas}

    if not round1_results:
        if console:
            console.print("\n[bold red]⚠ Round 1 returned 0 valid responses. Check your API key and provider.[/bold red]")
        else:
            print("\nERROR: Round 1 returned 0 valid responses. Check your API key and provider.")
        sys.exit(1)

    show_round_summary(1, round1_results, r1_time, persona_map)

    # ━━━ SOCIAL ROUNDS 2..N ━━━
    round_data = []
    previous_results = round1_results
    round_start = time.time()

    for round_num in range(2, args.rounds + 1):
        round_start = time.time()
        round_colors = {2: "cyan", 3: "magenta", 4: "green", 5: "bright_red"}
        color = round_colors.get(round_num, "bright_yellow")

        if console:
            label = "Social Interaction" if round_num == 2 else "Conversation Evolving" if round_num <= 5 else "Deep Social Dynamics"
            console.print(f"\n[bold {color}]━━━ ROUND {round_num}: {label} ━━━[/bold {color}]\n")
        else:
            print(f"\n--- ROUND {round_num} ---")

        if round_num == 2:
            results, trending = run_simulation_round2(
                provider, book_description, personas, previous_results, args.batch_size
            )
        else:
            conversation_summary = build_conversation_summary(round_data)
            results, trending = run_simulation_round_n(
                provider, book_description, personas, previous_results,
                round_num, args.rounds, args.batch_size, conversation_summary
            )

        round_time = time.time() - round_start
        round_data.append({"round": round_num, "results": results, "trending": trending})
        show_round_summary(round_num, results, round_time, persona_map)

        previous_results = results  # Next round reacts to THIS round

    total_time = time.time() - start_time

    # Aggregate
    if console:
        console.print("\n📊 Aggregating results across all rounds...")
    else:
        print("\nAggregating results...")
    stats = aggregate_results(round1_results, round_data, personas)

    # Generate report
    if console:
        console.print("🎨 Generating premium report...")
    else:
        print("Generating report...")
    report_path = generate_report(stats, book_description, output_path, provider.name)

    # Save raw JSON
    json_path = output_path.with_suffix('.json')
    clean_r1 = [{k: v for k, v in r.items() if k != "_persona"} for r in round1_results]
    export_stats = {k: v for k, v in stats.items() if k not in ("all_results", "platform_posts")}
    with open(json_path, 'w', encoding="utf-8") as f:
        json.dump({
            "stats": export_stats,
            "round1": clean_r1,
            "rounds": [{"round": rd["round"], "results": rd["results"],
                         "trending": rd["trending"]} for rd in round_data]
        }, f, indent=2)

    # === CINEMATIC REVEAL ===
    show_final_reveal(stats, total_time, est_cost, provider.name, total_calls,
                      report_path, json_path, args.no_open)

    # Open in browser
    if not args.no_open:
        webbrowser.open(report_path.resolve().as_uri())


if __name__ == "__main__":
    main()
