#!/usr/bin/env python3
"""
Readers Persona Generator v3
Generates diverse reader personas with PRISM demographic segmentation
and genre-specific tuning. No LLM needed — deterministic generation.

Usage:
    python generate_personas.py                    # 1,000 general personas
    python generate_personas.py 5000               # 5,000 general personas
    python generate_personas.py 1000 --genre romance  # 1,000 romance-tuned personas
    python generate_personas.py 10000 --genre thriller # 10,000 thriller-tuned personas
"""

import json
import random
import os
import argparse

random.seed(42)  # Reproducible

# ==========================================================================
# NAME POOLS
# ==========================================================================

FIRST_NAMES_F = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Ella", "Elizabeth", "Camila", "Luna",
    "Sofia", "Avery", "Mila", "Aria", "Scarlett", "Penelope", "Layla", "Chloe",
    "Victoria", "Madison", "Eleanor", "Grace", "Nora", "Riley", "Zoey", "Hannah",
    "Hazel", "Lily", "Ellie", "Violet", "Lillian", "Zoe", "Stella", "Aurora",
    "Natalie", "Emilia", "Everly", "Leah", "Aubrey", "Willow", "Addison", "Lucy",
    "Audrey", "Bella", "Nova", "Brooklyn", "Paisley", "Savannah", "Claire", "Skylar",
    "Jade", "Priya", "Aisha", "Yuki", "Mei", "Fatima", "Aaliyah", "Zara",
    "Ximena", "Valentina", "Catalina", "Esperanza", "Luz", "Carmen", "Rosa", "Ana",
    "Keiko", "Sakura", "Hana", "Min-ji", "Soo-yeon", "Wei", "Lin", "Jing",
    "Amara", "Nia", "Imani", "Zuri", "Kira", "Sana", "Riya", "Devi",
    "Ingrid", "Astrid", "Freya", "Sienna", "Margot", "Celeste", "Ivy", "Daphne",
    "Thea", "Iris", "Wren", "Sage", "Briar", "Fern", "Coral", "Juniper"
]

FIRST_NAMES_M = [
    "Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas",
    "Henry", "Alexander", "Mason", "Michael", "Ethan", "Daniel", "Jacob", "Logan",
    "Jackson", "Levi", "Sebastian", "Mateo", "Jack", "Owen", "Theodore", "Aiden",
    "Samuel", "Joseph", "John", "David", "Wyatt", "Matthew", "Luke", "Asher",
    "Carter", "Julian", "Grayson", "Leo", "Jayden", "Gabriel", "Isaac", "Lincoln",
    "Anthony", "Hudson", "Dylan", "Ezra", "Thomas", "Charles", "Christopher", "Jaxon",
    "Maverick", "Josiah", "Isaiah", "Andrew", "Elias", "Joshua", "Nathan", "Caleb",
    "Ryan", "Adrian", "Miles", "Raj", "Amit", "Omar", "Hassan", "Tariq",
    "Diego", "Carlos", "Miguel", "Alejandro", "Rafael", "Javier", "Luis", "Marco",
    "Kenji", "Hiroshi", "Taro", "Jun-ho", "Min-woo", "Wei", "Hao", "Chen",
    "Kwame", "Kofi", "Jabari", "Malik", "Darius", "Idris", "Rohan", "Arjun",
    "Erik", "Lars", "Finn", "Declan", "Callum", "Rhys", "Silas", "Jasper",
    "Felix", "Oscar", "Hugo", "Arlo", "Milo", "Atlas", "Orion", "Sterling"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Chen", "Kim", "Park", "Tanaka", "Yamamoto",
    "Singh", "Patel", "Shah", "Khan", "Ali", "Ahmed", "Okafor", "Mensah",
    "Johansson", "Mueller", "Schmidt", "Rossi", "Dubois", "Laurent", "Moreau",
    "Santos", "Silva", "Costa", "Ferreira", "Reeves", "Blackwood", "Ashford",
    "Thornton", "Whitfield", "Hawkins", "Preston", "Sterling", "Calloway", "Winters",
    "Frost", "Blake", "Reed", "Fox", "Wolf", "Stone", "Rivers", "Cross",
    "Chase", "Drake", "Hayes", "Flynn", "Quinn", "Nash", "Cole", "West"
]

# ==========================================================================
# ATTRIBUTE POOLS
# ==========================================================================

PLATFORMS = {
    "BookTok": 300, "Goodreads": 250, "Reddit": 150,
    "Bookstagram": 150, "X_Twitter": 100, "Lurker": 50
}

GENRES = [
    "Contemporary Romance", "Dark Romance", "Romantic Fantasy", "Cozy Mystery",
    "Psychological Thriller", "Epic Fantasy", "Sci-Fi", "Literary Fiction",
    "Horror", "Historical Fiction", "Memoir", "Self-Help", "YA Fantasy",
    "YA Contemporary", "Urban Fantasy", "Dystopian", "Crime Fiction",
    "Women's Fiction", "Mystery", "Paranormal Romance", "LitRPG",
    "Romantasy", "Sapphic Romance", "MM Romance", "Reverse Harem",
    "Clean Romance", "Spicy Romance", "Cozy Fantasy", "Grimdark",
    "Hard Sci-Fi", "Space Opera", "Cyberpunk", "Steampunk",
    "Magical Realism", "Southern Gothic", "Domestic Thriller",
    "True Crime", "Poetry", "Graphic Novels", "Nonfiction Narrative"
]

TROPE_LOVES = [
    "enemies to lovers", "forced proximity", "second chance romance",
    "found family", "slow burn", "friends to lovers", "grumpy x sunshine",
    "one bed", "fake dating", "forbidden love", "chosen one", "morally grey hero",
    "unreliable narrator", "locked room mystery", "time loop", "portal fantasy",
    "heist", "revenge plot", "redemption arc", "strong female lead",
    "dual timeline", "epistolary format", "small town setting",
    "academic/dark academia", "villain origin story", "secret identity",
    "bodyguard romance", "age gap", "workplace romance", "royal romance",
    "marriage of convenience", "who done it", "haunted house",
    "road trip", "summer romance", "winter setting", "island setting",
    "survival story", "underdog story", "mentor figure", "reluctant hero",
    "love triangle", "secret baby", "billionaire", "mafia romance"
]

TROPE_HATES = [
    "love triangle", "miscommunication", "secret baby", "insta-love",
    "chosen one", "mary sue", "deus ex machina", "fridging",
    "not like other girls", "big misunderstanding", "cheating",
    "cliffhanger ending", "open ending", "first person present tense",
    "multiple POV", "dream sequences", "prologues", "epilogue babies",
    "age gap", "power imbalance", "amnesia plot", "evil ex",
    "toxic masculinity played straight", "slut shaming", "dead parents trope",
    "bully romance", "kidnapping romance", "too many characters",
    "excessive world building", "info dumps", "purple prose"
]

REVIEW_STYLES = {
    "emotional": 250, "analytical": 200, "snarky": 150,
    "cheerleader": 200, "lurker": 200
}

PLATFORM_VOICE_NOTES = {
    "BookTok": "Uses ALL CAPS for emphasis, lots of emojis, 'this book WRECKED me', 'POV: you just finished [book]', references crying, screaming, throwing the book",
    "Goodreads": "Writes 2-3 paragraph reviews, uses star ratings precisely (3.5 stars rounded up), references other books for comparison, structured thoughts",
    "Reddit": "Skeptical tone, references subreddit culture ('just finished X and I have thoughts'), asks questions, contrarian takes welcome",
    "Bookstagram": "Aesthetic-focused, mentions cover design, reading setup/ambiance, uses hashtags, 'currently reading' vibes, mood-based recommendations",
    "X_Twitter": "Hot takes in under 280 characters, quote-tweets style, thread potential, uses ratio/main character language",
    "Lurker": "Rates on Goodreads but rarely reviews. If they do review, it's 1-2 sentences max. Represents the silent majority."
}

AGE_RANGES = {
    "16-21": 150, "22-28": 250, "29-35": 200,
    "36-45": 200, "46-55": 120, "56+": 80
}

BIO_TEMPLATES = {
    "BookTok": [
        "reads {speed}. will fight you about {genre}. {trope_love} supremacy.",
        "tbr pile: infinite. currently in my {genre} era. {trope_love} or die.",
        "bookish content creator. {genre} addict. anti-{trope_hate} agenda.",
        "read {books_per_year} books last year. {genre} is my personality.",
        "spicy book recs. {trope_love} enthusiast. DNFs without guilt."
    ],
    "Goodreads": [
        "Avid reader, {books_per_year} books/year. Primarily {genre}. I appreciate {trope_love} when done well.",
        "Librarian by day, voracious reader always. {genre} specialist. Fair but honest reviewer.",
        "Reading challenge: {books_per_year} books. {genre} fan. I rate harshly because I care.",
        "Book club organizer. {genre} evangelist. Will DNF if {trope_hate} shows up.",
        "PhD student who reads {genre} to decompress. Analytical reviews. No spoilers."
    ],
    "Reddit": [
        "lurks r/books and r/{subreddit}. contrarian by nature. {genre} defender.",
        "DNFs more than I finish. {genre} snob. fight me about {trope_hate}.",
        "longtime lurker, occasional poster. {genre} is the hill I die on.",
        "reads {speed}. posts hot takes about {genre}. {trope_hate} is lazy writing.",
        "mod energy. {genre} purist. will write a 2000-word rant about {trope_hate}."
    ],
    "Bookstagram": [
        "aesthetic reader. {genre} moods. flat lays and fairy lights.",
        "bookish corner curator. {genre} vibes. {trope_love} is *chef's kiss*.",
        "pastel shelves, dark books. {genre} obsessed. cover art matters.",
        "reading nook goals. {genre} is my comfort zone. pretty books only.",
        "monthly book hauls. {genre} collector. judging books by covers since forever."
    ],
    "X_Twitter": [
        "hot takes about {genre}. {trope_love} apologist. ratio me.",
        "books and opinions. {genre} threads. anti-{trope_hate} propaganda.",
        "reading is my personality. {genre} discourse. subtweeting authors since 2019.",
        "book twitter veteran. {genre} takes. will quote tweet your bad opinion.",
        "{genre} defender. {trope_love} truther. my tbr is a cry for help."
    ],
    "Lurker": [
        "reads {speed}. rates on Goodreads. never reviews. {genre} mostly.",
        "quiet reader. {genre} fan. {books_per_year} books last year. no reviews.",
        "reads {genre}. keeps opinions private. stars speak for themselves.",
        "silent reader. {genre} consumer. the algorithm knows my taste.",
        "reads constantly, posts never. {genre}. {trope_love} is a weakness."
    ]
}

SUBREDDITS = {
    "Contemporary Romance": "romancebooks", "Dark Romance": "romancebooks",
    "Romantic Fantasy": "Fantasy", "Cozy Mystery": "CozyMysteries",
    "Psychological Thriller": "books", "Epic Fantasy": "Fantasy",
    "Sci-Fi": "printSF", "Literary Fiction": "literature",
    "Horror": "horrorlit", "Historical Fiction": "HistoricalFiction",
    "YA Fantasy": "YAlit", "YA Contemporary": "YAlit",
    "Urban Fantasy": "urbanfantasy", "Dystopian": "books",
    "Crime Fiction": "books", "LitRPG": "litrpg",
    "Grimdark": "Fantasy", "Hard Sci-Fi": "printSF", "Space Opera": "printSF",
}

# ==========================================================================
# PRISM DEMOGRAPHIC SEGMENTS
# ==========================================================================

PRISM_SEGMENTS = {
    "Affluent Bookworms": {
        "description": "High income, educated professionals who prefer literary fiction and are willing to pay premium prices for hardcovers and first editions",
        "reading_preferences": ["Literary Fiction", "Historical Fiction", "Memoir", "Nonfiction Narrative", "Magical Realism"],
        "price_sensitivity": "low",
        "discovery_method": "reviews, awards lists, NYT bestseller list, bookstore browsing",
        "avg_books_per_year": 35,
        "preferred_formats": ["hardcover", "ebook"],
        "brand_loyalty": "high",
        "weight": 100,
    },
    "Young Urban Readers": {
        "description": "18-30, trend-driven, heavily influenced by BookTok and social media. Genre fiction fans who read in bursts",
        "reading_preferences": ["Contemporary Romance", "Romantasy", "YA Fantasy", "Dark Romance", "Spicy Romance"],
        "price_sensitivity": "medium",
        "discovery_method": "BookTok, Instagram reels, influencer recommendations",
        "avg_books_per_year": 45,
        "preferred_formats": ["ebook", "audiobook"],
        "brand_loyalty": "low",
        "weight": 200,
    },
    "Suburban Families": {
        "description": "Parents who read for escapism during limited free time. Prefer feel-good or page-turning genres",
        "reading_preferences": ["Cozy Mystery", "Women's Fiction", "Domestic Thriller", "Clean Romance", "Cozy Fantasy"],
        "price_sensitivity": "medium",
        "discovery_method": "book clubs, library, Amazon recommendations, friend referrals",
        "avg_books_per_year": 20,
        "preferred_formats": ["paperback", "audiobook"],
        "brand_loyalty": "high",
        "weight": 150,
    },
    "Academic Readers": {
        "description": "University-affiliated readers with high critical standards. Prefer award-winning and intellectually challenging works",
        "reading_preferences": ["Literary Fiction", "Magical Realism", "Poetry", "Nonfiction Narrative", "Southern Gothic"],
        "price_sensitivity": "low",
        "discovery_method": "literary journals, university presses, awards shortlists, NPR reviews",
        "avg_books_per_year": 40,
        "preferred_formats": ["hardcover", "paperback"],
        "brand_loyalty": "medium",
        "weight": 80,
    },
    "Budget Readers": {
        "description": "Price-sensitive high-volume readers. Kindle Unlimited subscribers who devour books quickly and rate based on entertainment value",
        "reading_preferences": ["Contemporary Romance", "Spicy Romance", "Paranormal Romance", "Cozy Fantasy", "Reverse Harem"],
        "price_sensitivity": "high",
        "discovery_method": "Kindle Unlimited, Amazon also-boughts, newsletter swaps, free promos",
        "avg_books_per_year": 100,
        "preferred_formats": ["ebook"],
        "brand_loyalty": "low",
        "weight": 150,
    },
    "Senior Traditionalists": {
        "description": "55+ readers who prefer established authors and physical books. Value craftsmanship and traditional storytelling",
        "reading_preferences": ["Historical Fiction", "Mystery", "Crime Fiction", "Memoir", "Literary Fiction"],
        "price_sensitivity": "low",
        "discovery_method": "bookstores, library, newspaper reviews, word of mouth",
        "avg_books_per_year": 25,
        "preferred_formats": ["hardcover", "large print", "paperback"],
        "brand_loyalty": "very high",
        "weight": 80,
    },
    "Diverse Explorers": {
        "description": "Multicultural readers who actively seek diverse representation and cross-genre experiences",
        "reading_preferences": ["Literary Fiction", "YA Contemporary", "Sapphic Romance", "Magical Realism", "MM Romance"],
        "price_sensitivity": "medium",
        "discovery_method": "diverse book clubs, indie bookstores, social media communities, podcast recs",
        "avg_books_per_year": 35,
        "preferred_formats": ["paperback", "ebook", "audiobook"],
        "brand_loyalty": "medium",
        "weight": 120,
    },
    "Genre Devotees": {
        "description": "Deep genre fans who attend conventions, participate in online communities, and have encyclopedic knowledge of their genre",
        "reading_preferences": ["Epic Fantasy", "Sci-Fi", "Hard Sci-Fi", "Grimdark", "LitRPG", "Space Opera"],
        "price_sensitivity": "medium",
        "discovery_method": "subreddit recommendations, author newsletters, conventions, Goodreads lists",
        "avg_books_per_year": 55,
        "preferred_formats": ["ebook", "hardcover", "audiobook"],
        "brand_loyalty": "very high",
        "weight": 120,
    }
}

# ==========================================================================
# GENRE-SPECIFIC CONFIGURATIONS
# ==========================================================================

GENRE_CONFIGS = {
    "romance": {
        "primary_genres": ["Contemporary Romance", "Dark Romance", "Romantic Fantasy",
                           "Spicy Romance", "Clean Romance", "Sapphic Romance",
                           "MM Romance", "Reverse Harem", "Paranormal Romance", "Romantasy"],
        "platform_weights": {"BookTok": 400, "Goodreads": 200, "Reddit": 80,
                             "Bookstagram": 200, "X_Twitter": 70, "Lurker": 50},
        "segment_weights": {"Young Urban Readers": 300, "Budget Readers": 250,
                            "Suburban Families": 200, "Diverse Explorers": 100,
                            "Affluent Bookworms": 50, "Genre Devotees": 50,
                            "Academic Readers": 30, "Senior Traditionalists": 20},
        "trope_loves_override": [
            "enemies to lovers", "forced proximity", "second chance romance",
            "slow burn", "friends to lovers", "grumpy x sunshine", "one bed",
            "fake dating", "forbidden love", "bodyguard romance", "age gap",
            "workplace romance", "royal romance", "marriage of convenience",
            "secret baby", "billionaire", "mafia romance", "found family",
            "small town setting", "summer romance", "island setting"
        ],
        "critical_level_bias": -1,
    },
    "thriller": {
        "primary_genres": ["Psychological Thriller", "Domestic Thriller", "Crime Fiction",
                           "Mystery", "True Crime", "Horror", "Southern Gothic"],
        "platform_weights": {"BookTok": 200, "Goodreads": 300, "Reddit": 200,
                             "Bookstagram": 100, "X_Twitter": 150, "Lurker": 50},
        "segment_weights": {"Suburban Families": 250, "Affluent Bookworms": 200,
                            "Young Urban Readers": 150, "Senior Traditionalists": 150,
                            "Academic Readers": 80, "Budget Readers": 80,
                            "Genre Devotees": 50, "Diverse Explorers": 40},
        "trope_loves_override": [
            "unreliable narrator", "locked room mystery", "dual timeline",
            "revenge plot", "who done it", "haunted house", "survival story",
            "time loop", "secret identity", "villain origin story",
            "morally grey hero", "strong female lead"
        ],
        "critical_level_bias": 1,
    },
    "fantasy": {
        "primary_genres": ["Epic Fantasy", "Urban Fantasy", "Cozy Fantasy",
                           "Romantic Fantasy", "Grimdark", "YA Fantasy",
                           "Portal Fantasy", "Steampunk", "Romantasy"],
        "platform_weights": {"BookTok": 250, "Goodreads": 250, "Reddit": 250,
                             "Bookstagram": 100, "X_Twitter": 100, "Lurker": 50},
        "segment_weights": {"Genre Devotees": 300, "Young Urban Readers": 250,
                            "Diverse Explorers": 120, "Academic Readers": 100,
                            "Budget Readers": 100, "Affluent Bookworms": 60,
                            "Suburban Families": 40, "Senior Traditionalists": 30},
        "trope_loves_override": [
            "found family", "chosen one", "morally grey hero", "portal fantasy",
            "heist", "redemption arc", "strong female lead", "villain origin story",
            "secret identity", "mentor figure", "reluctant hero", "slow burn",
            "enemies to lovers", "forbidden love", "time loop"
        ],
        "critical_level_bias": 0,
    },
    "scifi": {
        "primary_genres": ["Sci-Fi", "Hard Sci-Fi", "Space Opera", "Cyberpunk",
                           "Dystopian", "LitRPG", "Steampunk"],
        "platform_weights": {"BookTok": 100, "Goodreads": 250, "Reddit": 350,
                             "Bookstagram": 50, "X_Twitter": 150, "Lurker": 100},
        "segment_weights": {"Genre Devotees": 350, "Academic Readers": 150,
                            "Young Urban Readers": 150, "Affluent Bookworms": 100,
                            "Budget Readers": 100, "Diverse Explorers": 80,
                            "Senior Traditionalists": 40, "Suburban Families": 30},
        "trope_loves_override": [
            "time loop", "survival story", "underdog story", "heist",
            "revenge plot", "dual timeline", "secret identity",
            "morally grey hero", "villain origin story", "found family",
            "reluctant hero", "strong female lead"
        ],
        "critical_level_bias": 1,
    },
    "literary": {
        "primary_genres": ["Literary Fiction", "Magical Realism", "Southern Gothic",
                           "Poetry", "Historical Fiction", "Memoir"],
        "platform_weights": {"BookTok": 100, "Goodreads": 300, "Reddit": 200,
                             "Bookstagram": 150, "X_Twitter": 150, "Lurker": 100},
        "segment_weights": {"Academic Readers": 300, "Affluent Bookworms": 250,
                            "Diverse Explorers": 150, "Senior Traditionalists": 100,
                            "Young Urban Readers": 80, "Genre Devotees": 60,
                            "Suburban Families": 40, "Budget Readers": 20},
        "trope_loves_override": [
            "unreliable narrator", "dual timeline", "epistolary format",
            "redemption arc", "morally grey hero", "small town setting",
            "road trip", "found family", "strong female lead",
            "academic/dark academia"
        ],
        "critical_level_bias": 2,
    },
    "nonfiction": {
        "primary_genres": ["Self-Help", "Memoir", "True Crime", "Nonfiction Narrative"],
        "platform_weights": {"BookTok": 150, "Goodreads": 300, "Reddit": 200,
                             "Bookstagram": 100, "X_Twitter": 150, "Lurker": 100},
        "segment_weights": {"Affluent Bookworms": 250, "Academic Readers": 200,
                            "Suburban Families": 150, "Senior Traditionalists": 150,
                            "Young Urban Readers": 100, "Diverse Explorers": 80,
                            "Budget Readers": 40, "Genre Devotees": 30},
        "trope_loves_override": [
            "underdog story", "redemption arc", "mentor figure",
            "dual timeline", "strong female lead", "survival story",
            "road trip", "epistolary format"
        ],
        "critical_level_bias": 1,
    },
    "ya": {
        "primary_genres": ["YA Fantasy", "YA Contemporary", "Dystopian",
                           "Romantasy", "Urban Fantasy"],
        "platform_weights": {"BookTok": 400, "Goodreads": 200, "Reddit": 50,
                             "Bookstagram": 250, "X_Twitter": 50, "Lurker": 50},
        "segment_weights": {"Young Urban Readers": 400, "Budget Readers": 150,
                            "Diverse Explorers": 150, "Suburban Families": 100,
                            "Genre Devotees": 100, "Affluent Bookworms": 40,
                            "Academic Readers": 40, "Senior Traditionalists": 20},
        "trope_loves_override": [
            "chosen one", "found family", "enemies to lovers", "slow burn",
            "friends to lovers", "forbidden love", "portal fantasy",
            "redemption arc", "strong female lead", "underdog story",
            "reluctant hero", "secret identity", "grumpy x sunshine"
        ],
        "critical_level_bias": -1,
    },
}


# ==========================================================================
# GENERATION FUNCTIONS
# ==========================================================================

def weighted_pick(distribution: dict) -> str:
    items = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(items, weights=weights, k=1)[0]


def generate_persona(persona_id: int, platform: str, age_range: str,
                     segment: str = None, genre_config: dict = None) -> dict:
    """Generate a single reader persona with PRISM demographic segment."""
    gender = random.choice(["female", "male", "nonbinary"])
    if gender == "female":
        first = random.choice(FIRST_NAMES_F)
    elif gender == "male":
        first = random.choice(FIRST_NAMES_M)
    else:
        first = random.choice(FIRST_NAMES_F + FIRST_NAMES_M)

    last = random.choice(LAST_NAMES)

    # Genre preferences — biased by segment and genre config
    available_genres = GENRES
    if genre_config and "primary_genres" in genre_config:
        # 70% chance primary genre comes from the genre config pool
        if random.random() < 0.7:
            available_genres = genre_config["primary_genres"]

    seg_data = PRISM_SEGMENTS.get(segment, {})
    seg_prefs = seg_data.get("reading_preferences", [])

    num_genres = random.randint(2, 4)
    if seg_prefs and random.random() < 0.5:
        # 50% chance primary genre influenced by segment preferences
        primary_genre = random.choice(seg_prefs)
        other_pool = [g for g in available_genres if g != primary_genre]
        if not other_pool:
            other_pool = [g for g in GENRES if g != primary_genre]
        preferred_genres = [primary_genre] + random.sample(other_pool, min(num_genres - 1, len(other_pool)))
    else:
        preferred_genres = random.sample(available_genres, min(num_genres, len(available_genres)))
        if len(preferred_genres) < num_genres:
            extras = random.sample([g for g in GENRES if g not in preferred_genres],
                                   num_genres - len(preferred_genres))
            preferred_genres.extend(extras)
    primary_genre = preferred_genres[0]

    # Tropes — use genre-specific overrides if available
    trope_pool = genre_config.get("trope_loves_override", TROPE_LOVES) if genre_config else TROPE_LOVES
    num_loves = random.randint(2, 5)
    num_hates = random.randint(1, 4)
    trope_loves = random.sample(trope_pool, min(num_loves, len(trope_pool)))
    trope_hates = random.sample(TROPE_HATES, num_hates)

    # Reading behavior — influenced by segment
    reading_speed = random.choice(["fast", "moderate", "slow"])
    seg_books = seg_data.get("avg_books_per_year", None)
    if seg_books:
        books_per_year = max(5, seg_books + random.randint(-15, 15))
    else:
        books_per_year = {"fast": random.randint(50, 200), "moderate": random.randint(20, 50),
                          "slow": random.randint(5, 20)}[reading_speed]

    # Critical level — with genre bias
    base_weights = [5, 8, 12, 15, 18, 18, 12, 7, 3, 2]
    critical_level = random.choices(range(1, 11), weights=base_weights, k=1)[0]
    bias = genre_config.get("critical_level_bias", 0) if genre_config else 0
    critical_level = max(1, min(10, critical_level + bias))

    dnf_threshold = random.choice(["low", "medium", "high"])

    # Review style (correlated with platform)
    style_weights = {
        "BookTok": ([40, 30, 15, 10, 5], ["emotional", "cheerleader", "snarky", "analytical", "lurker"]),
        "Goodreads": ([40, 20, 15, 15, 10], ["analytical", "emotional", "cheerleader", "snarky", "lurker"]),
        "Reddit": ([30, 35, 15, 5, 15], ["analytical", "snarky", "emotional", "cheerleader", "lurker"]),
        "Bookstagram": ([35, 25, 15, 20, 5], ["cheerleader", "emotional", "analytical", "lurker", "snarky"]),
        "X_Twitter": ([35, 25, 20, 10, 10], ["snarky", "emotional", "analytical", "cheerleader", "lurker"]),
    }
    if platform in style_weights:
        weights, styles = style_weights[platform]
        review_style = random.choices(styles, weights=weights, k=1)[0]
    else:
        review_style = "lurker"

    influence_level = random.choices(["micro", "mid", "macro"], weights=[70, 25, 5], k=1)[0]

    # Generate bio
    subreddit = SUBREDDITS.get(primary_genre, "books")
    bio_templates = BIO_TEMPLATES.get(platform, BIO_TEMPLATES["Lurker"])
    bio = random.choice(bio_templates).format(
        speed=reading_speed, genre=primary_genre.lower(),
        trope_love=trope_loves[0], trope_hate=trope_hates[0],
        books_per_year=books_per_year, subreddit=subreddit
    )

    persona = {
        "persona_id": persona_id,
        "name": f"{first} {last}",
        "gender": gender,
        "age_range": age_range,
        "platform": platform,
        "preferred_genres": preferred_genres,
        "primary_genre": primary_genre,
        "trope_loves": trope_loves,
        "trope_hates": trope_hates,
        "reading_speed": reading_speed,
        "books_per_year": books_per_year,
        "critical_level": critical_level,
        "dnf_threshold": dnf_threshold,
        "review_style": review_style,
        "influence_level": influence_level,
        "platform_voice": PLATFORM_VOICE_NOTES[platform],
        "bio": bio,
        # V3: PRISM demographic segment
        "demographic_segment": segment or "General",
        "segment_data": {
            "description": seg_data.get("description", ""),
            "price_sensitivity": seg_data.get("price_sensitivity", "medium"),
            "discovery_method": seg_data.get("discovery_method", ""),
            "preferred_formats": seg_data.get("preferred_formats", []),
            "brand_loyalty": seg_data.get("brand_loyalty", "medium"),
        }
    }
    return persona


def generate_all_personas(count=1000, genre=None) -> list:
    """Generate all personas with PRISM segments and optional genre tuning."""
    personas = []
    persona_id = 1
    scale = count / 1000.0

    # Get genre config if specified
    genre_config = GENRE_CONFIGS.get(genre) if genre else None

    # Platform weights — use genre overrides or defaults
    plat_weights = genre_config.get("platform_weights", PLATFORMS) if genre_config else PLATFORMS
    platform_assignments = []
    for platform, base_num in plat_weights.items():
        num = max(1, round(base_num * scale))
        platform_assignments.extend([platform] * num)

    # Age assignments
    age_assignments = []
    for age, base_num in AGE_RANGES.items():
        num = max(1, round(base_num * scale))
        age_assignments.extend([age] * num)

    # PRISM segment assignments — use genre overrides or defaults
    seg_weights = genre_config.get("segment_weights", {s: d["weight"] for s, d in PRISM_SEGMENTS.items()}) if genre_config else {s: d["weight"] for s, d in PRISM_SEGMENTS.items()}
    segment_assignments = []
    for seg, base_num in seg_weights.items():
        num = max(1, round(base_num * scale))
        segment_assignments.extend([seg] * num)

    # Pad or trim all to exact count
    for lst, pool in [(platform_assignments, list(plat_weights.keys())),
                      (age_assignments, list(AGE_RANGES.keys())),
                      (segment_assignments, list(seg_weights.keys()))]:
        while len(lst) < count:
            lst.append(random.choice(pool))

    platform_assignments = platform_assignments[:count]
    age_assignments = age_assignments[:count]
    segment_assignments = segment_assignments[:count]

    random.shuffle(platform_assignments)
    random.shuffle(age_assignments)
    random.shuffle(segment_assignments)

    for i in range(count):
        persona = generate_persona(
            persona_id, platform_assignments[i], age_assignments[i],
            segment=segment_assignments[i], genre_config=genre_config
        )
        personas.append(persona)
        persona_id += 1

    return personas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Readers Persona Generator v3")
    parser.add_argument("count", nargs="?", type=int, default=1000, help="Number of personas to generate")
    parser.add_argument("--genre", "-g", default=None,
                        choices=["romance", "thriller", "fantasy", "scifi", "literary", "nonfiction", "ya"],
                        help="Genre-specific persona tuning")
    args = parser.parse_args()

    count = args.count
    genre = args.genre

    print(f"Readers Persona Generator v3")
    print("=" * 50)
    print(f"Generating {count:,} {'genre-tuned (' + genre + ')' if genre else 'general'} reader personas...")
    if genre:
        print(f"Genre config: {genre} | PRISM segments enabled")

    personas = generate_all_personas(count, genre=genre)

    # Save to JSON
    if genre:
        output_name = f"personas_{genre}.json" if count == 1000 else f"personas_{genre}_{count}.json"
    else:
        output_name = f"personas_{count}.json" if count != 1000 else "personas.json"

    output_path = os.path.join(os.path.dirname(__file__) or ".", output_name)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(personas, f, indent=2)

    total = len(personas)
    print(f"\n Generated {total:,} personas -> {output_path}")
    print(f"\n Distribution:")

    # Platform
    platform_counts = {}
    for p in personas:
        platform_counts[p["platform"]] = platform_counts.get(p["platform"], 0) + 1
    print("\nBy Platform:")
    for plat, ct in sorted(platform_counts.items(), key=lambda x: -x[1]):
        print(f"  {plat:15s} {ct:5d} ({ct/total*100:.1f}%)")

    # Age
    age_counts = {}
    for p in personas:
        age_counts[p["age_range"]] = age_counts.get(p["age_range"], 0) + 1
    print("\nBy Age:")
    for age, ct in sorted(age_counts.items()):
        print(f"  {age:15s} {ct:5d} ({ct/total*100:.1f}%)")

    # PRISM Segments
    seg_counts = {}
    for p in personas:
        seg_counts[p["demographic_segment"]] = seg_counts.get(p["demographic_segment"], 0) + 1
    print("\nBy PRISM Segment:")
    for seg, ct in sorted(seg_counts.items(), key=lambda x: -x[1]):
        print(f"  {seg:25s} {ct:5d} ({ct/total*100:.1f}%)")

    print(f"\nAvg Critical Level: {sum(p['critical_level'] for p in personas)/total:.1f}/10")

    sample = random.choice(personas)
    print(f"\nSample: {sample['name']} | {sample['age_range']} | {sample['platform']} | "
          f"{sample['primary_genre']} | {sample['demographic_segment']}")
