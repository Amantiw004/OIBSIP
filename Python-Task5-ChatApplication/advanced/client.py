"""
Task 5 - Chat Application (Advanced Tier)
CLIENT: tkinter GUI with login/register, rooms, history, notifications.

Run (after starting advanced/server.py):   python client.py
Open it several times to simulate several users.
"""

import json
import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

try:  # optional desktop notifications:  pip install plyer
    from plyer import notification as desktop_notification
except Exception:  # plyer not installed -> fall back to bell + title flash
    desktop_notification = None

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5556
APP_TITLE = "Chat App"


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("860x540")
        self.root.minsize(700, 420)

        self.sock = None
        self.inbox = queue.Queue()
        self.username = None
        self.room = None
        self.unread = 0

        self.login_frame = None
        self.chat_frame = None

        self.build_login()
        self.root.bind("<FocusIn>", self.on_focus)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll_inbox)

    # ------------------------------------------------------------ login UI
    def build_login(self):
        self.login_frame = tk.Frame(self.root, padx=30, pady=30)
        self.login_frame.pack(expand=True)

        tk.Label(self.login_frame, text="Chat App", font=("Segoe UI", 22, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 15))

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()

        fields = [("Server", self.host_var), ("Port", self.port_var),
                  ("Username", self.user_var), ("Password", self.pass_var)]
        for i, (label, var) in enumerate(fields, start=1):
            tk.Label(self.login_frame, text=label, anchor="e").grid(
                row=i, column=0, sticky="e", padx=5, pady=4)
            entry = tk.Entry(self.login_frame, textvariable=var, width=28,
                             show="*" if label == "Password" else "")
            entry.grid(row=i, column=1, pady=4)
            if label == "Password":
                entry.bind("<Return>", lambda e: self.do_login())

        buttons = tk.Frame(self.login_frame)
        buttons.grid(row=5, column=0, columnspan=2, pady=12)
        tk.Button(buttons, text="Login", width=12, command=self.do_login).pack(side="left", padx=5)
        tk.Button(buttons, text="Register", width=12, command=self.do_register).pack(side="left", padx=5)

        self.status_var = tk.StringVar()
        tk.Label(self.login_frame, textvariable=self.status_var, fg="#b00020",
                 wraplength=300).grid(row=6, column=0, columnspan=2)

    # ------------------------------------------------------------- chat UI
    def build_chat(self):
        self.login_frame.destroy()
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(fill="both", expand=True)

        # left sidebar
        side = tk.Frame(self.chat_frame, width=190, padx=8, pady=8)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text=f"Hi, {self.username}", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(side, text="Rooms (double-click)", anchor="w").pack(fill="x", pady=(10, 2))
        self.room_list = tk.Listbox(side, height=8, exportselection=False)
        self.room_list.pack(fill="x")
        self.room_list.bind("<Double-Button-1>", self.on_room_double_click)

        new_row = tk.Frame(side)
        new_row.pack(fill="x", pady=6)
        self.new_room_var = tk.StringVar()
        new_entry = tk.Entry(new_row, textvariable=self.new_room_var)
        new_entry.pack(side="left", fill="x", expand=True)
        new_entry.bind("<Return>", lambda e: self.create_room())
        tk.Button(new_row, text="+", width=3, command=self.create_room).pack(side="left", padx=(4, 0))
        tk.Label(side, text="New room name", fg="gray", anchor="w").pack(fill="x")

        tk.Label(side, text="Online in room", anchor="w").pack(fill="x", pady=(12, 2))
        self.user_list = tk.Listbox(side, exportselection=False)
        self.user_list.pack(fill="both", expand=True)

        # right main area
        main = tk.Frame(self.chat_frame, padx=8, pady=8)
        main.pack(side="left", fill="both", expand=True)

        self.room_label = tk.Label(main, text="", font=("Segoe UI", 13, "bold"), anchor="w")
        self.room_label.pack(fill="x")

        self.text = scrolledtext.ScrolledText(main, state="disabled", wrap="word",
                                              font=("Segoe UI Emoji", 11))
        self.text.pack(fill="both", expand=True, pady=6)
        self.text.tag_config("me", foreground="#0b6b0b")
        self.text.tag_config("system", foreground="#777777", font=("Segoe UI", 9, "italic"))
        self.text.tag_config("time", foreground="#999999")

        bottom = tk.Frame(main)
        bottom.pack(fill="x")
        self.msg_var = tk.StringVar()
        self.msg_entry = tk.Entry(bottom, textvariable=self.msg_var, font=("Segoe UI Emoji", 11))
        self.msg_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())
        self.msg_entry.focus_set()
        tk.Button(bottom, text="Send", width=10, command=self.send_message).pack(side="left", padx=(6, 0))

        tk.Label(main, text="Emoji shortcodes: :smile: :heart: :thumbsup: :fire: :tada: :rocket: ...",
                 fg="gray", anchor="w").pack(fill="x", pady=(4, 0))

    # ------------------------------------------------------------ network
    def connect(self):
        if self.sock:
            return True
        try:
            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())
            sock = socket.create_connection((host, port), timeout=5)
            sock.settimeout(None)
        except (OSError, ValueError) as err:
            self.status_var.set(f"Cannot connect: {err}")
            return False
        self.sock = sock
        threading.Thread(target=self.receive_loop, args=(sock,), daemon=True).start()
        return True

    def receive_loop(self, sock):
        buffer = b""
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            self.inbox.put(json.loads(line.decode("utf-8")))
                        except ValueError:
                            pass
        except OSError:
            pass
        self.inbox.put({"type": "disconnected"})

    def send(self, obj):
        if not self.sock:
            return
        try:
            self.sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
        except OSError:
            self.inbox.put({"type": "disconnected"})

    # ------------------------------------------------------------- actions
    def credentials(self):
        return self.user_var.get().strip(), self.pass_var.get()

    def do_login(self):
        user, pw = self.credentials()
        if not user or not pw:
            self.status_var.set("Enter username and password")
            return
        self.status_var.set("")
        if self.connect():
            self.send({"type": "login", "username": user, "password": pw})

    def do_register(self):
        user, pw = self.credentials()
        if not user or not pw:
            self.status_var.set("Enter username and password")
            return
        self.status_var.set("")
        if self.connect():
            self.send({"type": "register", "username": user, "password": pw})

    def send_message(self):
        text = self.msg_var.get().strip()
        if text:
            self.send({"type": "msg", "text": text})
            self.msg_var.set("")

    def create_room(self):
        name = self.new_room_var.get().strip()
        if name:
            self.send({"type": "create_room", "room": name})
            self.new_room_var.set("")

    def on_room_double_click(self, _event):
        selection = self.room_list.curselection()
        if selection:
            self.send({"type": "join", "room": self.room_list.get(selection[0])})

    # ------------------------------------------------------ incoming events
    def poll_inbox(self):
        try:
            while True:
                self.handle(self.inbox.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self.poll_inbox)

    def handle(self, msg):
        kind = msg.get("type")

        if kind == "auth":
            if msg.get("ok"):
                self.username = msg["username"]
                self.build_chat()
            else:
                self.status_var.set(msg.get("message", "Login failed"))
        elif kind == "info":
            if self.login_frame and self.login_frame.winfo_exists():
                self.status_var.set("")
            messagebox.showinfo("Info", msg.get("message", ""))
        elif kind == "error":
            messagebox.showwarning("Error", msg.get("message", "Unknown error"))
        elif kind == "rooms":
            self.update_rooms(msg["rooms"])
        elif kind == "users":
            if msg["room"] == self.room:
                self.update_users(msg["users"])
        elif kind == "joined":
            self.room = msg["room"]
            self.room_label.config(text=f"# {self.room}")
            self.clear_chat()
            for old in msg.get("history", []):
                self.add_message(old["user"], old["text"], old["ts"])
            if msg.get("history"):
                self.add_line("--- end of history ---", "system")
            self.update_users(msg["users"])
            self.highlight_room()
        elif kind == "msg":
            if msg["room"] == self.room:
                self.add_message(msg["user"], msg["text"], msg["ts"])
                if msg["user"] != self.username:
                    self.notify(f"{msg['user']} in #{msg['room']}", msg["text"])
        elif kind == "system":
            if msg["room"] == self.room:
                self.add_line(f"[{msg['ts'][11:16]}] * {msg['text']}", "system")
        elif kind == "disconnected":
            self.sock = None
            if self.chat_frame:
                self.add_line("*** Connection to server lost ***", "system")
                messagebox.showerror("Disconnected", "Lost connection to the server.")
                self.root.destroy()
            else:
                self.status_var.set("Disconnected from server")

    # ----------------------------------------------------------- UI helpers
    def update_rooms(self, rooms):
        self.room_list.delete(0, "end")
        for r in rooms:
            self.room_list.insert("end", r)
        self.highlight_room()

    def highlight_room(self):
        if not self.room:
            return
        for i in range(self.room_list.size()):
            if self.room_list.get(i) == self.room:
                self.room_list.selection_clear(0, "end")
                self.room_list.selection_set(i)

    def update_users(self, users):
        self.user_list.delete(0, "end")
        for u in users:
            self.user_list.insert("end", u)

    def clear_chat(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def add_line(self, text, tag=None):
        self.text.config(state="normal")
        self.text.insert("end", text + "\n", tag)
        self.text.config(state="disabled")
        self.text.see("end")

    def add_message(self, user, text, ts):
        """Format: [14:35] Alice: Hello"""
        self.text.config(state="normal")
        self.text.insert("end", f"[{ts[11:16]}] ", "time")
        self.text.insert("end", f"{user}: {text}\n", "me" if user == self.username else None)
        self.text.config(state="disabled")
        self.text.see("end")

    # --------------------------------------------------------- notifications
    def window_focused(self):
        return self.root.focus_displayof() is not None

    def notify(self, title, body):
        if self.window_focused():
            return
        self.unread += 1
        self.root.title(f"({self.unread}) New messages - {APP_TITLE}")
        self.root.bell()
        if desktop_notification:
            try:
                desktop_notification.notify(title=title, message=body[:100],
                                            app_name=APP_TITLE, timeout=4)
            except Exception:
                pass

    def on_focus(self, _event):
        self.unread = 0
        self.root.title(APP_TITLE)

    def on_close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    ChatApp(window)
    window.mainloop()
