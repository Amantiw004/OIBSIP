"""
knowledge.py - "Answer general knowledge questions using a QA API or
local knowledge base."

Uses Wikipedia's free public REST API (no API key or signup required) to
fetch a short summary for the requested topic. Falls back gracefully if
the topic isn't found or the network is unavailable.
"""

import requests

WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
MAX_SPOKEN_SENTENCES = 2


def answer_question(query: str) -> str:
    """Return a short spoken-friendly answer for a general knowledge query."""
    if not query:
        return "What would you like to know about?"

    topic = query.strip().replace(" ", "_")

    try:
        response = requests.get(WIKI_SUMMARY_URL.format(topic), timeout=8)
    except requests.exceptions.RequestException:
        return "I couldn't reach the knowledge service. Please check your internet connection."

    if response.status_code == 404:
        return f"I couldn't find information about {query}. Could you try rephrasing it?"
    if response.status_code != 200:
        return "The knowledge service returned an unexpected error."

    data = response.json()
    extract = data.get("extract", "")
    if not extract:
        return f"I found {query}, but there wasn't a summary available."

    # Trim to the first couple of sentences so text-to-speech doesn't ramble on.
    sentences = extract.split(". ")
    short_answer = ". ".join(sentences[:MAX_SPOKEN_SENTENCES])
    if not short_answer.endswith("."):
        short_answer += "."

    return short_answer
