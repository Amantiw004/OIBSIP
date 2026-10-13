"""
Task 5 - Chat Application (Advanced Tier)
SERVER: TCP sockets + threading + SQLite.

Features: registration/login, multiple rooms, message history,
          emoji shortcodes, timestamps, graceful disconnects.

Run:  python server.py            (default 127.0.0.1:5556)
      python server.py 0.0.0.0    (allow other machines on your network)

Protocol: one JSON object per line ("\n" terminated), over plain TCP.
"""

import hashlib
import hmac
import json
import os
import re
import socket
import sqlite3
import sys
import threading
from datetime import datetime

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 5556
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat.db")
HISTORY_LIMIT = 50
DEFAULT_ROOM = "general"

EMOJI = {
    ":smile:": "\U0001F604", ":grin:": "\U0001F601", ":joy:": "\U0001F602",
    ":wink:": "\U0001F609", ":heart:": "\u2764\uFE0F", ":cry:": "\U0001F622",
    ":sunglasses:": "\U0001F60E", ":thinking:": "\U0001F914",
    ":thumbsup:": "\U0001F44D", ":+1:": "\U0001F44D", ":thumbsdown:": "\U0001F44E",
    ":clap:": "\U0001F44F", ":wave:": "\U0001F44B", ":pray:": "\U0001F64F",
    ":ok_hand:": "\U0001F44C", ":fire:": "\U0001F525", ":tada:": "\U0001F389",
    ":rocket:": "\U0001F680", ":star:": "\u2B50", ":100:": "\U0001F4AF",
    ":eyes:": "\U0001F440", ":sob:": "\U0001F62D", ":laughing:": "\U0001F606",
    ":party:": "\U0001F973", ":coffee:": "\u2615", ":sun:": "\u2600\uFE0F",
}

# ---------------------------------------------------------------- database
db = sqlite3.connect(DB_FILE, check_same_thread=False)
db_lock = threading.Lock()


def init_db():
    with db_lock:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                salt     BLOB NOT NULL,
                pw_hash  BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rooms (
                name TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS messages (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                room     TEXT NOT NULL,
                username TEXT NOT NULL,
                text     TEXT NOT NULL,
                ts       TEXT NOT NULL
            );
            """
        )
        db.execute("INSERT OR IGNORE INTO rooms(name) VALUES (?)", (DEFAULT_ROOM,))
        db.commit()


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)


def db_register(username, password):
    salt = os.urandom(16)
    try:
        with db_lock:
            db.execute(
                "INSERT INTO users(username, salt, pw_hash) VALUES (?,?,?)",
                (username, salt, hash_password(password, salt)),
            )
            db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def db_check_login(username, password):
    with db_lock:
        row = db.execute(
            "SELECT salt, pw_hash FROM users WHERE username=?", (username,)
        ).fetchone()
    if not row:
        return False
    return hmac.compare_digest(row[1], hash_password(password, row[0]))


def db_rooms():
    with db_lock:
        return [r[0] for r in db.execute("SELECT name FROM rooms ORDER BY name")]


def db_room_exists(name):
    with db_lock:
        return db.execute("SELECT 1 FROM rooms WHERE name=?", (name,)).fetchone() is not None


def db_create_room(name):
    try:
        with db_lock:
            db.execute("INSERT INTO rooms(name) VALUES (?)", (name,))
            db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def db_save_message(room, username, text, ts):
    with db_lock:
        db.execute(
            "INSERT INTO messages(room, username, text, ts) VALUES (?,?,?,?)",
            (room, username, text, ts),
        )
        db.commit()


def db_history(room):
    with db_lock:
        rows = db.execute(
            "SELECT username, text, ts FROM messages WHERE room=? "
            "ORDER BY id DESC LIMIT ?",
            (room, HISTORY_LIMIT),
        ).fetchall()
    return [{"user": u, "text": t, "ts": ts} for u, t, ts in reversed(rows)]


# ------------------------------------------------------------ live state
clients = []                       # list of client dicts
clients_lock = threading.Lock()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send(client, obj):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    try:
        with client["send_lock"]:
            client["conn"].sendall(data)
    except OSError:
        pass


def logged_in_clients():
    with clients_lock:
        return [c for c in clients if c["user"]]


def room_members(room):
    return [c for c in logged_in_clients() if c["room"] == room]


def broadcast_room(room, obj):
    for c in room_members(room):
        send(c, obj)


def send_user_list(room):
    users = sorted(c["user"] for c in room_members(room))
    broadcast_room(room, {"type": "users", "room": room, "users": users})


def broadcast_rooms():
    rooms = db_rooms()
    for c in logged_in_clients():
        send(c, {"type": "rooms", "rooms": rooms})


def system_msg(room, text):
    broadcast_room(room, {"type": "system", "room": room, "text": text, "ts": now()})


def apply_emoji(text):
    for code, char in EMOJI.items():
        text = text.replace(code, char)
    return text


# --------------------------------------------------------------- actions
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
ROOM_RE = re.compile(r"^[A-Za-z0-9_-]{2,20}$")


def do_register(client, msg):
    username = str(msg.get("username", "")).strip()
    password = str(msg.get("password", ""))
    if not USERNAME_RE.match(username):
        return send(client, {"type": "auth", "ok": False,
                             "message": "Username: 3-20 letters, numbers or _"})
    if len(password) < 4:
        return send(client, {"type": "auth", "ok": False,
                             "message": "Password must be at least 4 characters"})
    if db_register(username, password):
        send(client, {"type": "info", "message": "Registered! You can log in now."})
    else:
        send(client, {"type": "auth", "ok": False, "message": "Username already taken"})


def do_login(client, msg):
    username = str(msg.get("username", "")).strip()
    password = str(msg.get("password", ""))
    if not db_check_login(username, password):
        return send(client, {"type": "auth", "ok": False,
                             "message": "Invalid username or password"})
    if any(c["user"] == username for c in logged_in_clients()):
        return send(client, {"type": "auth", "ok": False,
                             "message": "This user is already logged in"})
    client["user"] = username
    send(client, {"type": "auth", "ok": True, "username": username})
    send(client, {"type": "rooms", "rooms": db_rooms()})
    join_room(client, DEFAULT_ROOM)
    print(f"[+] {username} logged in")


def join_room(client, room):
    old = client["room"]
    if old == room:
        return
    client["room"] = room
    if old:
        system_msg(old, f"{client['user']} left the room")
        send_user_list(old)
    users = sorted(c["user"] for c in room_members(room))
    send(client, {"type": "joined", "room": room, "users": users,
                  "history": db_history(room)})
    system_msg(room, f"{client['user']} joined the room")
    send_user_list(room)


def do_join(client, msg):
    room = str(msg.get("room", "")).strip()
    if not db_room_exists(room):
        return send(client, {"type": "error", "message": f"Room '{room}' does not exist"})
    join_room(client, room)


def do_create_room(client, msg):
    room = str(msg.get("room", "")).strip()
    if not ROOM_RE.match(room):
        return send(client, {"type": "error",
                             "message": "Room name: 2-20 letters, numbers, - or _"})
    if db_create_room(room):
        broadcast_rooms()
    join_room(client, room)


def do_message(client, msg):
    text = apply_emoji(str(msg.get("text", "")).strip())
    if not text or not client["room"]:
        return
    text = text[:1000]
    ts = now()
    db_save_message(client["room"], client["user"], text, ts)
    broadcast_room(client["room"], {"type": "msg", "room": client["room"],
                                    "user": client["user"], "text": text, "ts": ts})


ACTIONS = {"create_room": do_create_room, "join": do_join, "msg": do_message}


def process(client, msg):
    kind = msg.get("type")
    if kind == "register":
        return do_register(client, msg)
    if kind == "login":
        return do_login(client, msg)
    if not client["user"]:
        return send(client, {"type": "error", "message": "Please log in first"})
    handler = ACTIONS.get(kind)
    if handler:
        handler(client, msg)


def disconnect(client):
    with clients_lock:
        if client in clients:
            clients.remove(client)
    if client["user"] and client["room"]:
        system_msg(client["room"], f"{client['user']} disconnected")
        send_user_list(client["room"])
        print(f"[-] {client['user']} disconnected")
    try:
        client["conn"].close()
    except OSError:
        pass


def handle_client(conn):
    client = {"conn": conn, "user": None, "room": None, "send_lock": threading.Lock()}
    with clients_lock:
        clients.append(client)
    buffer = b""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    process(client, msg)
    except OSError:
        pass
    finally:
        disconnect(client)


def main():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Advanced chat server on {HOST}:{PORT}  (database: {DB_FILE})")
    try:
        while True:
            conn, _ = server.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
