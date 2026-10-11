# Task 5 - Chat Application (Python)

A real-time chat app built with Python sockets and threading, in two tiers:

| Tier | Folder | What it is |
|------|--------|------------|
| Beginner | `beginner/` | Command-line chat over TCP sockets, timestamps, disconnect notices |
| Advanced | `advanced/` | tkinter GUI, registration/login (SQLite), multiple rooms, message history, notifications, emoji shortcodes |

Only the Python standard library is required. `plyer` is optional (desktop notifications).

## Requirements
- Python 3.8+
- tkinter (bundled with Python on Windows/macOS; on Linux: `sudo apt install python3-tk`)

## Beginner tier
Open **two or three terminals** in `beginner/`:

```bash
python server.py      # terminal 1 - start first
python client.py      # terminal 2 - enter a username
python client.py      # terminal 3 - enter another username
```
Type a message and press Enter. Type `/quit` to leave.
Example: `[14:35] Alice: Hello`

## Advanced tier
```bash
cd advanced
python server.py     # terminal 1
python client.py     # terminal 2 (GUI)
python client.py     # terminal 3 (GUI, second user)
```
1. Enter a username (3-20 letters/numbers/_) and password (4+ chars), click **Register**, then **Login**.
2. You land in `#general`. Double-click a room in the list to join it.
3. Type a name in the box below the room list and click **+** to create a room.
4. Messages from earlier are loaded automatically when you join a room.
5. Try `:smile:`, `:heart:`, `:thumbsup:`, `:fire:`, `:tada:`, `:rocket:` ...
6. Switch to another window: you will get a bell, a `(1) New messages` title, and a desktop notification if `plyer` is installed (`pip install plyer`).

### Using it over your network (optional)
Run `python server.py 0.0.0.0` and enter the server computer's IP address in the client's *Server* field.

## Feature checklist

**Beginner**
- [x] Server listens for incoming connections
- [x] Client connects to server
- [x] Real-time two-way messaging
- [x] Timestamp prefix `[HH:MM] Name: text`
- [x] Notification when the other client disconnects
- [x] Runs on the same machine via `localhost`

**Advanced**
- [x] tkinter GUI
- [x] Registration and login stored in SQLite
- [x] Multiple rooms (create/join)
- [x] Message history loaded on join (last 50)
- [x] Notification when window is not focused
- [x] Emoji shortcodes rendered as Unicode
- [x] Security transparency (below)

## How messages are stored (security transparency)

- Messages, room names and users are stored in a local SQLite file, `advanced/chat.db`, on the machine running the server.
- Messages are saved as **plain text**. Anyone with access to the server or the database file can read all messages, including messages in every room.
- **Traffic is NOT encrypted.** Data travels over plain TCP (no TLS), so anyone on the same network could read it. Do not use it on untrusted networks or send sensitive information.
- Passwords are **not** stored in plain text: each is salted and hashed with PBKDF2-HMAC-SHA256 (100,000 iterations). However, the password itself is sent to the server unencrypted at login, because there is no TLS.
- There is no end-to-end encryption, no message deletion, and no rate limiting.
- Rooms are public: any logged-in user can join any room.

To make it production-ready you would add TLS (`ssl` module), end-to-end encryption, private rooms and rate limiting.

## How it works

- The server starts one thread per connected client.
- The advanced protocol is one JSON object per line, for example
  `{"type": "msg", "text": "Hello"}`.
- The GUI client uses a background thread to read from the socket and a `queue.Queue`, which the tkinter main loop polls every 100 ms (tkinter widgets must only be touched from the main thread).

## Project structure
```
chat_app/
├── README.md
├── beginner/
│   ├── server.py
│   └── client.py
└── advanced/
    ├── server.py      # creates chat.db on first run
    └── client.py
```

## Troubleshooting
- **Cannot connect / connection refused:** start the server first and check host/port.
- **Address already in use:** an old server is still running; close it or wait a minute.
- **No tkinter:** install `python3-tk` (Linux).
- **Emoji look black and white:** that is your OS font; it is only cosmetic.
