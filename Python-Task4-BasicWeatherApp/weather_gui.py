"""
weather_gui.py  -  ADVANCED TIER
Tkinter weather app with icons, hourly + 5-day forecast, unit toggle,
IP-based location detection and in-GUI error messages.

Run:  python weather_gui.py
"""

import io
import queue
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

import weather_api as api

BG = "#eef3f9"
CARD = "#ffffff"
ACCENT = "#2b6cb0"
TEXT = "#1a202c"
MUTED = "#5a6778"
ERROR = "#c53030"


class WeatherApp:
    def __init__(self, root):
        self.root = root
        root.title("Weather App")
        root.geometry("780x700")
        root.minsize(720, 640)
        root.configure(bg=BG)

        self.unit = "C"              # "C" or "F"
        self.data = None             # last successful result
        self.icon_bytes = {}         # icon code -> PNG bytes
        self.icon_cache = {}         # (code, size) -> PhotoImage (keeps refs alive)
        self.busy = False
        self.results = queue.Queue()  # worker thread -> UI thread

        self._build_ui()
        self.root.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # --- top bar ---
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(16, 6))

        self.city_var = tk.StringVar()
        self.entry = ttk.Entry(top, textvariable=self.city_var, font=("Segoe UI", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", lambda e: self.get_weather())
        self.entry.focus()

        self.btn_get = ttk.Button(top, text="Get Weather", command=self.get_weather)
        self.btn_get.pack(side="left", padx=(8, 0))

        self.btn_loc = ttk.Button(top, text="📍 My Location", command=self.use_my_location)
        self.btn_loc.pack(side="left", padx=(6, 0))

        self.btn_unit = ttk.Button(top, text="Switch to °F", command=self.toggle_unit)
        self.btn_unit.pack(side="left", padx=(6, 0))

        # --- status / error line ---
        self.status = tk.Label(
            self.root, text="Enter a city or ZIP code (e.g. Ahmedabad, 380001, 10001,US).",
            bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w", wraplength=740, justify="left",
        )
        self.status.pack(fill="x", padx=18, pady=(0, 6))

        # --- current weather panel (results panel) ---
        self.current_frame = tk.Frame(self.root, bg=CARD, highlightbackground="#d5dde8",
                                      highlightthickness=1)
        self.current_frame.pack(fill="x", padx=16, pady=6)

        # --- hourly panel ---
        self._section_label("Hourly forecast (3-hour steps)")
        self.hourly_frame = tk.Frame(self.root, bg=CARD, highlightbackground="#d5dde8",
                                     highlightthickness=1)
        self.hourly_frame.pack(fill="x", padx=16, pady=(0, 6))

        # --- daily panel ---
        self._section_label("Next 5 days")
        self.daily_frame = tk.Frame(self.root, bg=CARD, highlightbackground="#d5dde8",
                                    highlightthickness=1)
        self.daily_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.render()

    def _section_label(self, text):
        tk.Label(self.root, text=text, bg=BG, fg=TEXT,
                 font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", padx=18, pady=(6, 2))

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def show_error(self, message):
        self.status.config(text=f"⚠  {message}", fg=ERROR)

    def show_info(self, message):
        self.status.config(text=message, fg=MUTED)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def get_weather(self):
        query = self.city_var.get().strip()
        if not query:
            self.show_error("Please enter a city name or ZIP code.")
            return
        self._start(query, use_ip=False)

    def use_my_location(self):
        self._start(None, use_ip=True)

    def toggle_unit(self):
        self.unit = "F" if self.unit == "C" else "C"
        self.btn_unit.config(text="Switch to °C" if self.unit == "F" else "Switch to °F")
        self.render()

    def _start(self, query, use_ip):
        if self.busy:
            return
        self.busy = True
        for b in (self.btn_get, self.btn_loc):
            b.state(["disabled"])
        self.show_info("Loading weather data…")
        threading.Thread(target=self._worker, args=(query, use_ip), daemon=True).start()

    # ------------------------------------------------------------------
    # Background worker (network calls happen here so the window never freezes)
    # ------------------------------------------------------------------
    def _worker(self, query, use_ip):
        try:
            if use_ip:
                query = api.get_location_from_ip()
            current = api.get_current(query)
            forecast = api.get_forecast(current["lat"], current["lon"])
            hourly = api.build_hourly(forecast)
            daily = api.build_daily(forecast)

            codes = {current["icon"]} | {h["icon"] for h in hourly} | {d["icon"] for d in daily}
            icons = {c: api.download_icon(c) for c in codes if c}

            payload = {"current": current, "hourly": hourly, "daily": daily,
                       "icons": icons, "query": query}
            self.results.put(("ok", payload))
        except api.WeatherError as exc:
            self.results.put(("error", str(exc)))
        except ValueError as exc:
            self.results.put(("error", str(exc)))
        except Exception as exc:  # last-resort safety net
            self.results.put(("error", f"Unexpected error: {exc}"))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.results.get_nowait()
                self._finish(kind, payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _finish(self, kind, payload):
        self.busy = False
        for b in (self.btn_get, self.btn_loc):
            b.state(["!disabled"])

        if kind == "error":
            self.data = None
            self.show_error(payload)
        else:
            self.data = payload
            self.icon_bytes.update({k: v for k, v in payload["icons"].items() if v})
            self.city_var.set(payload["current"]["city"])
            self.show_info("Weather updated.")
        self.render()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _icon(self, code, size):
        key = (code, size)
        if key in self.icon_cache:
            return self.icon_cache[key]
        raw = self.icon_bytes.get(code)
        if not raw:
            return None
        img = Image.open(io.BytesIO(raw)).convert("RGBA").resize((size, size), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.icon_cache[key] = photo
        return photo

    def _temp(self, celsius):
        if celsius is None:
            return "--"
        value = celsius if self.unit == "C" else api.c_to_f(celsius)
        return f"{round(value)}°{self.unit}"

    def _wind(self, ms):
        if self.unit == "C":
            return f"{api.ms_to_kmh(ms):.1f} km/h"
        return f"{api.ms_to_mph(ms):.1f} mph"

    @staticmethod
    def _clear(frame):
        for child in frame.winfo_children():
            child.destroy()

    def render(self):
        for frame in (self.current_frame, self.hourly_frame, self.daily_frame):
            self._clear(frame)

        if not self.data:
            tk.Label(self.current_frame, text="No weather data yet.", bg=CARD, fg=MUTED,
                     font=("Segoe UI", 11), pady=30).pack()
            return

        self._render_current(self.data["current"])
        self._render_hourly(self.data["hourly"])
        self._render_daily(self.data["daily"])

    def _render_current(self, cur):
        f = self.current_frame
        left = tk.Frame(f, bg=CARD)
        left.pack(side="left", padx=16, pady=10)

        photo = self._icon(cur["icon"], 100)
        if photo:
            tk.Label(left, image=photo, bg=CARD).pack()

        right = tk.Frame(f, bg=CARD)
        right.pack(side="left", fill="x", expand=True, padx=8, pady=10)

        tk.Label(right, text=f"{cur['city']}, {cur['country']}", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x")
        tk.Label(right, text=self._temp(cur["temp_c"]), bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 34, "bold"), anchor="w").pack(fill="x")
        tk.Label(right, text=cur["description"], bg=CARD, fg=TEXT,
                 font=("Segoe UI", 13), anchor="w").pack(fill="x")

        details = (f"Feels like {self._temp(cur['feels_c'])}    •    "
                   f"Humidity {cur['humidity']}%    •    Wind {self._wind(cur['wind_ms'])}")
        tk.Label(right, text=details, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=(4, 0))

    def _render_hourly(self, hourly):
        f = self.hourly_frame
        for i, h in enumerate(hourly):
            f.columnconfigure(i, weight=1, uniform="h")
            cell = tk.Frame(f, bg=CARD)
            cell.grid(row=0, column=i, padx=6, pady=8, sticky="n")
            tk.Label(cell, text=h["label"], bg=CARD, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack()
            photo = self._icon(h["icon"], 50)
            if photo:
                tk.Label(cell, image=photo, bg=CARD).pack()
            tk.Label(cell, text=self._temp(h["temp_c"]), bg=CARD, fg=ACCENT,
                     font=("Segoe UI", 13, "bold")).pack()
            tk.Label(cell, text=h["description"], bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9)).pack()
            tk.Label(cell, text=f"Rain {h['rain_chance']}%", bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9)).pack()

    def _render_daily(self, daily):
        f = self.daily_frame
        if not daily:
            tk.Label(f, text="Daily forecast not available.", bg=CARD, fg=MUTED,
                     pady=20).pack()
            return
        for i, d in enumerate(daily):
            f.columnconfigure(i, weight=1, uniform="d")
            cell = tk.Frame(f, bg=CARD)
            cell.grid(row=0, column=i, padx=6, pady=10, sticky="n")
            tk.Label(cell, text=d["label"], bg=CARD, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack()
            photo = self._icon(d["icon"], 56)
            if photo:
                tk.Label(cell, image=photo, bg=CARD).pack()
            tk.Label(cell, text=f"{self._temp(d['max_c'])} / {self._temp(d['min_c'])}",
                     bg=CARD, fg=ACCENT, font=("Segoe UI", 11, "bold")).pack()
            tk.Label(cell, text=d["description"], bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9), wraplength=110).pack()


def main():
    root = tk.Tk()
    WeatherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
