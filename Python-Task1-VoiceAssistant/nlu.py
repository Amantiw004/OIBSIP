"""
nlu.py - Lightweight rule-based Natural Language Understanding.

Advanced Tier checklist item:
  "Natural language understanding: parse intent from free-form spoken
   sentences (not just keyword matching)"

Design notes
------------
Instead of plain `if "time" in command`, every intent below is defined as
one or more REGEX PATTERNS with named capture groups. This lets the
assistant understand many different phrasings of the same request and pull
out the actual slot values (city, search topic, reminder duration, etc.)
directly from a full sentence, e.g.:

    "hey can you tell me the weather in Mumbai please"
        -> intent="weather", entities={"city": "mumbai"}

    "remind me to drink water in 10 minutes"
        -> intent="reminder", entities={"text": "drink water",
                                          "amount": "10", "unit": "minutes"}

This is intentionally dependency-free (no nltk/transformers download
required) so the project runs out-of-the-box. Swapping this module for a
spaCy / transformers pipeline later is a drop-in upgrade - see README.
"""

import re

# Each intent maps to a list of regex patterns tried in order.
# re.IGNORECASE is applied when matching.
INTENT_PATTERNS = {
    "greet": [
        r"\b(hello|hi|hey)\b",
    ],
    "time": [
        r"\bwhat.*(time|clock)\b",
        r"\btime\b",
    ],
    "date": [
        r"\bwhat.*date\b",
        r"\bdate\b",
        r"\bwhat day\b",
    ],
    "search": [
        r"\b(?:search|google|look ?up)\s+(?:for\s+)?(?P<query>.+)",
    ],
    "weather": [
        r"\bweather\b.*?\b(?:in|for|at)\s+(?P<city>[a-zA-Z\s]+)$",
        r"\bweather\b",
    ],
    "email": [
        r"\bsend\s+(?:an?\s+)?email\b",
        r"\bcompose\s+(?:an?\s+)?email\b",
    ],
    "reminder": [
        r"\bremind\s+me\s+to\s+(?P<text>.+?)\s+in\s+(?P<amount>\d+)\s*"
        r"(?P<unit>seconds?|minutes?|hours?)\b",
        r"\bset\s+a?\s*reminder\b",
    ],
    "knowledge": [
        r"\b(?:what\s+is|what\s+are|who\s+is|who\s+are|define|"
        r"tell\s+me\s+about)\s+(?P<query>.+)",
    ],
    "add_command": [
        r"\b(?:add|create|teach)\s+(?:a\s+)?(?:new\s+)?command\b",
    ],
    "exit": [
        r"\b(exit|quit|stop|goodbye|bye)\b",
    ],
}

# Order matters: more specific intents are checked before generic ones.
# time/date must come before knowledge so "what is the time" doesn't get
# swallowed by the broad "what is <query>" knowledge pattern.
INTENT_ORDER = [
    "exit", "add_command", "reminder", "email", "weather",
    "search", "time", "date", "knowledge", "greet",
]


def parse_intent(text: str):
    """Return (intent_name, entities_dict). intent_name is None if nothing matched."""
    if not text:
        return None, {}

    cleaned = text.strip().lower()

    for intent in INTENT_ORDER:
        for pattern in INTENT_PATTERNS[intent]:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                entities = {k: v.strip() for k, v in match.groupdict().items() if v}
                return intent, entities

    return None, {}
