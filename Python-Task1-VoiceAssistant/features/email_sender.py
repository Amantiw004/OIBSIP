"""
email_sender.py - "Send an email via voice command using smtplib"
(use a test/dummy email account, not your primary one).

Requires in your .env file:
  EMAIL_ADDRESS       - the sending account (e.g. a test Gmail address)
  EMAIL_APP_PASSWORD  - a 16-character Gmail "App Password" (NOT your
                          normal login password - see README for how to
                          generate one)

Uses Gmail's SMTP server by default; change SMTP_SERVER/SMTP_PORT for
another provider (Outlook, Yahoo, etc.).
"""

import os
import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_email(to_address: str, subject: str, body: str) -> str:
    """Attempt to send an email. Returns a spoken-friendly result message."""
    sender = os.getenv("EMAIL_ADDRESS")
    app_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not app_password or "your_" in sender:
        return (
            "The email feature needs EMAIL_ADDRESS and EMAIL_APP_PASSWORD "
            "set in your dot env file."
        )

    if not to_address or "@" not in to_address:
        return "That doesn't look like a valid email address, so I didn't send it."

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_address

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.login(sender, app_password)
            server.sendmail(sender, [to_address], message.as_string())
        return f"Email sent to {to_address} successfully."
    except smtplib.SMTPAuthenticationError:
        return (
            "Email login failed. Please check your email address and app "
            "password in the dot env file."
        )
    except smtplib.SMTPException as e:
        return f"I couldn't send the email due to a mail server error."
    except OSError:
        return "I couldn't reach the mail server. Please check your internet connection."
