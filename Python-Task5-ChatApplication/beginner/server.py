"""
Task 5 - Chat Application (Beginner Tier)
SERVER: listens for client connections and relays messages between them.

Run first:   python server.py
"""

import socket
import threading
from datetime import datetime

HOST = "127.0.0.1"   # localhost - both scripts run on the same machine
PORT = 5555

clients = {}                     # {connection: username}
clients_lock = threading.Lock()  # protects the dict across threads


def timestamp():
    """Return current time as HH:MM."""
    return datetime.now().strftime("%H:%M")


def send_line(conn, text):
    """Send one line of text to one client."""
    try:
        conn.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast(text, sender=None):
    """Send text to every connected client except `sender`."""
    with clients_lock:
        targets = [c for c in clients if c is not sender]
    for conn in targets:
        send_line(conn, text)


def handle_client(conn, addr):
    """Runs in its own thread for every connected client."""
    reader = conn.makefile("r", encoding="utf-8")
    name = "Anonymous"
    try:
        # The first line a client sends is its username
        name = reader.readline().strip() or f"User{addr[1]}"
        with clients_lock:
            clients[conn] = name
        print(f"[+] {name} connected from {addr}")
        send_line(conn, f"*** Welcome, {name}! Type /quit to leave. ***")
        broadcast(f"*** {name} joined the chat ***", sender=conn)

        # Every following line is a chat message
        for line in reader:
            message = line.strip()
            if not message:
                continue
            if message == "/quit":
                break
            broadcast(f"[{timestamp()}] {name}: {message}", sender=conn)
    except (ConnectionResetError, OSError):
        pass
    finally:
        # Graceful disconnection: remove client and notify the others
        with clients_lock:
            clients.pop(conn, None)
        broadcast(f"*** {name} has disconnected ***")
        print(f"[-] {name} disconnected")
        try:
            conn.close()
        except OSError:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server listening on {HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
