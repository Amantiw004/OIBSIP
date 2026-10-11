"""
OASIS INFOBYTE - Task 1: Python Voice Assistant
Beginner Tier + Advanced Tier combined.

BEGINNER TIER (all implemented):
  [x] Capture voice input using speech_recognition (microphone)
  [x] Respond to "Hello" with a predefined greeting
  [x] Tell the current time and date on request
  [x] Perform a web search on a user-specified topic (opens browser)
  [x] Graceful error handling - asks the user to repeat if unclear
  [x] Text-to-speech feedback using pyttsx3 for all responses

ADVANCED TIER (all implemented, on top of the above):
  [x] NLU: parse intent from free-form spoken sentences (see nlu.py)
  [x] Send an email via voice command using smtplib
  [x] Set a timed reminder that triggers an audible alert
  [x] Fetch and read live weather updates (OpenWeatherMap)
  [x] Answer general knowledge questions (Wikipedia summary API)
  [x] Add custom commands via voice prompt or by editing commands.json
  [x] Privacy consideration - see "Privacy Notice" in README.md
"""

import json
import os
import sys
import webbrowser
from datetime import datetime

import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv

from nlu import parse_intent
from features.weather import get_weather_report
from features.email_sender import send_email
from features.reminders import set_reminder
from features.knowledge import answer_question

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

load_dotenv()  # reads .env into environment variables (safe no-op if missing)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

recognizer = sr.Recognizer()
engine = pyttsx3.init()
engine.setProperty("rate", 175)
engine.setProperty("volume", 1.0)


def load_custom_commands() -> dict:
    if not os.path.exists(COMMANDS_FILE):
        return {}
    try:
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("custom_commands", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Could not read commands.json: {e}")
        return {}


def save_custom_command(trigger: str, response: str) -> None:
    data = {"custom_commands": load_custom_commands()}
    data["custom_commands"][trigger.lower()] = response
    try:
        with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"[WARN] Could not save commands.json: {e}")


CUSTOM_COMMANDS = load_custom_commands()


# --------------------------------------------------------------------------
# Core voice I/O helpers
# --------------------------------------------------------------------------

def speak(text: str) -> None:
    """Speak text aloud AND print it, so you always have visible feedback."""
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()


def listen(timeout: int = 5, phrase_time_limit: int = 8):
    """Capture audio and return recognized text (lowercased), or None.

    Handles WaitTimeoutError, UnknownValueError, and RequestError so the
    assistant degrades gracefully instead of crashing.
    """
    with sr.Microphone() as source:
        print("\nListening... (speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        except sr.WaitTimeoutError:
            speak("I didn't hear anything. Could you please repeat that?")
            return None

    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text.lower().strip()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that. Could you please repeat?")
        return None
    except sr.RequestError as e:
        speak("I'm having trouble reaching the speech service right now.")
        print(f"[ERROR] Speech recognition request failed: {e}")
        return None


def listen_until_valid(prompt: str, retries: int = 3):
    """Speak `prompt`, then listen, retrying up to `retries` times if
    nothing usable was heard. Used for multi-turn slot-filling (email,
    reminders, adding commands).
    """
    speak(prompt)
    for _ in range(retries):
        response = listen()
        if response:
            return response
    speak("I still didn't catch that, let's cancel this for now.")
    return None


# --------------------------------------------------------------------------
# Beginner tier features
# --------------------------------------------------------------------------

def tell_time() -> None:
    now = datetime.now().strftime("%I:%M %p")
    speak(f"The current time is {now}")


def tell_date() -> None:
    today = datetime.now().strftime("%A, %B %d, %Y")
    speak(f"Today's date is {today}")


def web_search(topic: str) -> None:
    if not topic:
        topic = listen_until_valid("What would you like me to search for?")
        if not topic:
            return
    speak(f"Searching the web for {topic}")
    url = f"https://www.google.com/search?q={topic.replace(' ', '+')}"
    webbrowser.open(url)


def check_custom_commands(command: str) -> bool:
    for trigger, response in CUSTOM_COMMANDS.items():
        if trigger.lower() in command:
            speak(response)
            return True
    return False


# --------------------------------------------------------------------------
# Advanced tier features (slot-filling flows)
# --------------------------------------------------------------------------

def handle_weather(entities: dict) -> None:
    city = entities.get("city")
    if not city:
        city = listen_until_valid("Which city's weather would you like?")
        if not city:
            return
    speak("Let me check that for you.")
    speak(get_weather_report(city))


def handle_email() -> None:
    to_address = listen_until_valid("Who should I send the email to? Please say the email address.")
    if not to_address:
        return
    # Speech recognition often mishears "@" and "." - normalize common spoken forms.
    to_address = (
        to_address.replace(" at the rate ", "@").replace(" at ", "@")
        .replace(" dot ", ".").replace(" ", "")
    )

    subject = listen_until_valid("What's the subject of the email?")
    if not subject:
        return

    body = listen_until_valid("What should the email say?")
    if not body:
        return

    speak("Sending your email now.")
    speak(send_email(to_address, subject, body))


def handle_reminder(entities: dict) -> None:
    text = entities.get("text")
    amount = entities.get("amount")
    unit = entities.get("unit")

    if not (text and amount and unit):
        # Fell through on the generic "set a reminder" pattern - ask directly.
        text = listen_until_valid("What should I remind you about?")
        if not text:
            return
        duration = listen_until_valid("In how long? For example, say '10 minutes'.")
        if not duration:
            return
        # crude parse of "<number> <unit>"
        parts = duration.split()
        amount = next((p for p in parts if p.isdigit()), None)
        unit = next((p for p in parts if p.isalpha()), None)
        if not amount or not unit:
            speak("I couldn't understand that duration, cancelling the reminder.")
            return

    speak(set_reminder(text, amount, unit, speak))


def handle_knowledge(entities: dict) -> None:
    query = entities.get("query")
    if not query:
        query = listen_until_valid("What would you like to know about?")
        if not query:
            return
    speak(answer_question(query))


def handle_add_command() -> None:
    trigger = listen_until_valid("What phrase should trigger the new command?")
    if not trigger:
        return
    response = listen_until_valid("And what should I say in response?")
    if not response:
        return
    save_custom_command(trigger, response)
    global CUSTOM_COMMANDS
    CUSTOM_COMMANDS = load_custom_commands()
    speak(f"Got it. Next time you say '{trigger}', I'll respond with that.")


# --------------------------------------------------------------------------
# Command router (uses NLU intent parsing)
# --------------------------------------------------------------------------

def process_command(command: str) -> bool:
    """Route the recognized command using intent parsing.
    Returns False if the assistant should shut down, True otherwise.
    """
    if command is None:
        return True  # already handled (repeat prompt) inside listen()

    # Custom commands take priority so users can override anything.
    if check_custom_commands(command):
        return True

    intent, entities = parse_intent(command)

    if intent == "exit":
        speak("Goodbye! Have a great day.")
        return False
    elif intent == "greet":
        speak("Hello! I'm your voice assistant. How can I help you today?")
    elif intent == "time":
        tell_time()
    elif intent == "date":
        tell_date()
    elif intent == "search":
        web_search(entities.get("query"))
    elif intent == "weather":
        handle_weather(entities)
    elif intent == "email":
        handle_email()
    elif intent == "reminder":
        handle_reminder(entities)
    elif intent == "knowledge":
        handle_knowledge(entities)
    elif intent == "add_command":
        handle_add_command()
    else:
        speak(
            "I'm not sure how to help with that yet. You can ask me for the "
            "time, date, weather, to search something, send an email, set a "
            "reminder, or a general knowledge question."
        )

    return True


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    speak("Voice assistant started. Say 'hello' to begin, or say 'exit' anytime to quit.")
    running = True
    while running:
        try:
            command = listen()
            running = process_command(command)
        except KeyboardInterrupt:
            speak("Shutting down. Goodbye!")
            sys.exit(0)
        except Exception as e:  # last-resort safety net so the assistant never hard-crashes
            print(f"[ERROR] Unexpected error: {e}")
            speak("Something went wrong on my end, but I'm still here. Please try again.")


if __name__ == "__main__":
    main()
