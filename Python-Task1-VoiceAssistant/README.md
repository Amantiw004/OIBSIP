# Python Voice Assistant — Oasis Infobyte Task 1

A Python voice assistant that listens to spoken commands and responds with
speech. Covers **all Beginner Tier + all Advanced Tier** checklist items.

### Beginner Tier
- [x] Capture voice input using `speech_recognition` (microphone)
- [x] Respond to "Hello" with a predefined greeting
- [x] Tell the current time and date on request
- [x] Perform a web search on a user-specified topic (opens browser)
- [x] Graceful error handling — asks the user to repeat if unclear
- [x] Text-to-speech feedback using `pyttsx3` for all responses

### Advanced Tier
- [x] Natural language understanding — parses intent from full sentences, not just keyword matching (`nlu.py`)
- [x] Send an email via voice command using `smtplib`
- [x] Set a timed reminder that triggers an audible alert after a duration
- [x] Fetch and read live weather updates (OpenWeatherMap API)
- [x] Answer general knowledge questions (Wikipedia summary API — free, no key needed)
- [x] Add custom commands via voice prompt, or by editing `commands.json`
- [x] Privacy consideration — see **Privacy Notice** below

## Project Structure

```
voice_assistant/
├── main.py                  # Entry point - run this
├── nlu.py                   # Rule-based intent + entity parser
├── commands.json            # Custom trigger -> response pairs (editable, and voice-writable)
├── requirements.txt         # Python dependencies
├── .env.example              # Template for API keys / credentials
├── .gitignore
├── README.md
└── features/
    ├── __init__.py
    ├── weather.py            # OpenWeatherMap integration
    ├── email_sender.py       # smtplib email sending
    ├── reminders.py          # threading.Timer-based reminders
    └── knowledge.py          # Wikipedia summary Q&A
```

## Setup Guide

### 1. Create and activate a virtual environment (recommended)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

**Note on PyAudio (common sticking point):**
- **Windows:** if `pip install pyaudio` fails, run:
  ```bash
  pip install pipwin
  pipwin install pyaudio
  ```
- **macOS:** install the portaudio system library first:
  ```bash
  brew install portaudio
  pip install pyaudio
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt-get install python3-pyaudio portaudio19-dev
  pip install pyaudio
  ```

### 3. Set up your `.env` file
```bash
cp .env.example .env      # macOS/Linux
copy .env.example .env    # Windows
```
Then fill in the real values — you can add these later; each feature will
just tell you (by voice) that it needs a key until you do:

- **`OPENWEATHER_API_KEY`** → free at https://openweathermap.org/api
  (Sign up → "API keys" tab → copy the default key). New keys can take
  a few minutes to activate.
- **`EMAIL_ADDRESS`** / **`EMAIL_APP_PASSWORD`** → use a **test/dummy Gmail
  account**, never your primary one:
  1. Turn on 2-Step Verification for that Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Generate an app password (choose "Mail" as the app).
  4. Paste the 16-character password into `EMAIL_APP_PASSWORD`.

`.env` is already excluded via `.gitignore` — it will never be committed.

### 4. Run the assistant
```bash
python main.py
```

## Example things to say

| Category | Example phrases |
|---|---|
| Greeting | "Hello", "Hi" |
| Time / Date | "What's the time?", "What's today's date?" |
| Search | "Search for python tutorials", "Google the Eiffel Tower" |
| Weather | "What's the weather in Mumbai?", "Weather" (it'll ask which city) |
| Email | "Send an email" (it'll ask recipient / subject / body one at a time) |
| Reminder | "Remind me to drink water in 10 minutes" |
| Knowledge | "What is photosynthesis?", "Who is Alan Turing?" |
| Custom commands | "Add a command" (it'll ask for the trigger phrase and response) |
| Exit | "Exit", "Quit", "Bye" |

## How the NLU works

`nlu.py` uses **regex patterns with named capture groups** per intent, so a
full free-form sentence like *"hey can you tell me the weather in Mumbai
please"* is parsed into `intent="weather"`, `entities={"city": "mumbai"}` —
not just a substring check. This is dependency-free by design so the
project runs immediately without downloading any ML models. If you want to
extend it with `nltk` (tokenizing/lemmatizing) or a `transformers` intent
classifier later, `parse_intent(text)` is the single function to swap out —
everything else calls it through that interface.

## Privacy Notice

This assistant processes the following data, all **locally on your machine**
unless noted:

- **Microphone audio**: captured locally, then sent to Google's speech
  recognition API (via the `speech_recognition` library) to convert it to
  text. Audio is not stored to disk.
- **Search / weather / knowledge queries**: the text you speak for these
  features is sent to the relevant third-party API (Google Search,
  OpenWeatherMap, Wikipedia) to fetch results. No personal identifiers are
  attached beyond the query itself.
- **Email feature**: recipient address, subject, and body you dictate are
  sent via your configured Gmail account over an encrypted (SSL) connection
  directly to Gmail's SMTP server — nothing is sent to us or stored
  elsewhere. Use a test/dummy account, not one with sensitive access.
- **API keys / credentials**: stored only in your local `.env` file, which
  is excluded from version control by `.gitignore` and never transmitted
  anywhere except to authenticate with the respective service (OpenWeatherMap,
  Gmail).
- **Custom commands**: trigger phrases and responses you add are saved
  locally in `commands.json`.

No data is sent to any server other than the specific API needed for the
feature you're using, and nothing is logged or shared with third parties
beyond that.

## Troubleshooting

| Problem | Fix |
|---|---|
| `OSError: No Default Input Device Available` | No microphone detected — check OS sound settings / plug in a mic |
| Assistant mishears you often | Speak in a quiet room; ambient noise is auto-calibrated each time it listens |
| `speech_recognition.RequestError` | `recognize_google()` needs internet — check your connection |
| "needs an OpenWeatherMap API key" | Add `OPENWEATHER_API_KEY` to `.env` (see Setup step 3) |
| "Email login failed" | Make sure you're using an **App Password**, not your normal Gmail password, and that 2-Step Verification is on |
| Weather says city not found | Try a more specific name, e.g. "Surat, IN" instead of just "Surat" if there's ambiguity |
| Reminder alert isn't very loud | The `\a` terminal bell depends on your OS/terminal sound settings — the spoken reminder will still play regardless |
