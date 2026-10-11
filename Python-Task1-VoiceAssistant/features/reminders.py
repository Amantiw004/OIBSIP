"""
reminders.py - "Set a timed reminder that triggers an audible alert after
a specified duration."

Uses threading.Timer so the assistant keeps listening for other commands
while a reminder counts down in the background. When it fires, it prints/
speaks the reminder text and plays a simple terminal bell as the audible
alert (cross-platform, no extra audio libraries required).
"""

import threading

UNIT_TO_SECONDS = {
    "second": 1, "seconds": 1,
    "minute": 60, "minutes": 60,
    "hour": 3600, "hours": 3600,
}


def _fire_reminder(text: str, speak_fn):
    # \a is the ASCII bell character - most terminals/OSes play a short
    # beep sound for it, giving a simple cross-platform audible alert.
    print("\a" * 3, end="", flush=True)
    speak_fn(f"Reminder: {text}")


def set_reminder(text: str, amount: str, unit: str, speak_fn) -> str:
    """Schedule a reminder. Returns a spoken-friendly confirmation message."""
    try:
        amount_num = int(amount)
    except ValueError:
        return "I couldn't understand the reminder duration."

    unit_key = unit.lower()
    if unit_key not in UNIT_TO_SECONDS:
        return "Please specify the duration in seconds, minutes, or hours."

    total_seconds = amount_num * UNIT_TO_SECONDS[unit_key]
    if total_seconds <= 0:
        return "The reminder duration needs to be greater than zero."

    timer = threading.Timer(total_seconds, _fire_reminder, args=(text, speak_fn))
    timer.daemon = True  # so it doesn't block program exit
    timer.start()

    return f"Okay, I'll remind you to {text} in {amount_num} {unit_key}."
