"""
Task 5 - Chat Application (Beginner Tier)
CLIENT: connects to the server, sends and receives messages in real time.

Run in two separate terminals (after starting server.py):
    python client.py
"""

import socket
import threading
import os
from datetime import datetime

HOST = "127.0.0.1"
PORT = 5555


def receive_messages(sock):
    """Background thread: print everything the server sends."""
    reader = sock.makefile("r", encoding="utf-8")
    try:
        for line in reader:
            # \r + spaces erases the "You:" prompt, then we reprint it
            print(f"\r{line.strip()}\n", end="")
    except OSError:
        pass
    print("\n*** Disconnected from server ***")
    sock.close()
    os._exit(0)  # main thread is blocked on input(), so force exit


def main():
    name = input("Enter your username: ").strip() or "Anonymous"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Could not connect. Is server.py running?")
        return

    sock.sendall((name + "\n").encode("utf-8"))

    thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    thread.start()

    try:
        while True:
            message = input()
            if not message.strip():
                continue
            if message.strip() == "/quit":
                sock.sendall(b"/quit\n")
                break
            sock.sendall((message + "\n").encode("utf-8"))
            # show our own message locally with the same timestamp format
            print(f"[{datetime.now().strftime('%H:%M')}] {name}: {message}")
    except (KeyboardInterrupt, EOFError):
        try:
            sock.sendall(b"/quit\n")
        except OSError:
            pass
    except OSError:
        print("Connection lost.")
    finally:
        sock.close()
        print("Goodbye!")


if __name__ == "__main__":
    main()
