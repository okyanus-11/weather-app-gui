"""Responsive Tkinter weather dashboard with async requests and saved themes."""

from __future__ import annotations

import json
import math
import os
import queue
import re
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, messagebox, ttk
from typing import Any

import requests
from dotenv import load_dotenv

API_URL = "https://api.openweathermap.org/data/2.5/weather"
CONFIG_PATH = Path.home() / ".weather-now.json"
THEMES: dict[str, dict[str, str]] = {
    "graphite": {
        "background": "#10151d", "surface": "#171f2a", "surface_alt": "#202b38",
        "border": "#2c3948", "text": "#edf3f8", "muted": "#9aabba",
        "accent": "#68a9ff",
    },
    "midnight": {
        "background": "#11111b", "surface": "#1a1a2a", "surface_alt": "#25253a",
        "border": "#38384f", "text": "#ececf7", "muted": "#a2a2bf",
        "accent": "#b59cff",
    },
    "light": {
        "background": "#f2f5f9", "surface": "#ffffff", "surface_alt": "#e9eef5",
        "border": "#d7e0e9", "text": "#202b3a", "muted": "#66778a",
        "accent": "#326fd1",
    },
}


def _accent_foreground(hex_color: str) -> str:
    """Choose readable text for an accent-filled button (WCAG luminance)."""
    value = hex_color.lstrip("#")
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        return "#ffffff"
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return "#10151d" if luminance > 0.179 else "#ffffff"


class WeatherError(RuntimeError):
    """Raised when the weather service cannot fulfil a request."""


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _validate_weather_data(data: Any) -> dict[str, Any]:
    invalid_response = "OpenWeatherMap returned an invalid weather response. Please try again."
    if not isinstance(data, dict):
        raise WeatherError(invalid_response)

    system = data.get("sys")
    conditions = data.get("weather")
    measurements = data.get("main")
    wind = data.get("wind")
    if (
        not isinstance(data.get("name"), str)
        or not data["name"].strip()
        or not isinstance(system, dict)
        or not isinstance(system.get("country"), str)
        or not system["country"].strip()
        or not isinstance(conditions, list)
        or not conditions
        or not isinstance(conditions[0], dict)
        or not isinstance(conditions[0].get("description"), str)
        or not conditions[0]["description"].strip()
        or not isinstance(measurements, dict)
        or not isinstance(wind, dict)
    ):
        raise WeatherError(invalid_response)

    humidity = measurements.get("humidity")
    wind_speed = wind.get("speed")
    if (
        not _is_finite_number(measurements.get("temp"))
        or not _is_finite_number(measurements.get("feels_like"))
        or not _is_finite_number(humidity)
        or not 0 <= humidity <= 100
        or not _is_finite_number(wind_speed)
        or wind_speed < 0
        or not _is_finite_number(data.get("dt"))
    ):
        raise WeatherError(invalid_response)

    try:
        datetime.fromtimestamp(data["dt"])
    except (OverflowError, OSError, ValueError) as error:
        raise WeatherError(invalid_response) from error
    return data


def fetch_weather(city: str, api_key: str, units: str) -> dict[str, Any]:
    try:
        response = requests.get(
            API_URL, params={"q": city, "appid": api_key, "units": units}, timeout=10
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as error:
            raise WeatherError(
                "OpenWeatherMap returned an invalid weather response. Please try again."
            ) from error
        return _validate_weather_data(data)
    except requests.Timeout as error:
        raise WeatherError("The weather service took too long to respond. Please try again.") from error
    except requests.RequestException as error:
        if error.response is None:
            raise WeatherError("Could not reach OpenWeatherMap. Check your internet connection.") from error
        if error.response.status_code == 401:
            raise WeatherError("Your OpenWeatherMap API key was rejected. Check WEATHER_API_KEY.") from error
        if error.response.status_code == 404:
            raise WeatherError("City not found. Try a city and country code, such as London,GB.") from error
        raise WeatherError(f"OpenWeatherMap returned an error ({error.response.status_code}).") from error

class WeatherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Weather Now")
        self.geometry("600x620")
        self.minsize(500, 540)
        self.units = tk.StringVar(value="metric")
        self.city = tk.StringVar(value="Istanbul")
        self.api_key = os.getenv("WEATHER_API_KEY", "")
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="weather")
        self._request_id = 0
        self._closing = False
        self._results_queue = queue.SimpleQueue()
        self._preferences = self._load_preferences()
        self.theme_name = self._preferences.get("theme", "graphite")
        if self.theme_name not in THEMES:
            self.theme_name = "graphite"
        self.accent = self._preferences.get("accent", THEMES[self.theme_name]["accent"])
        if not isinstance(self.accent, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", self.accent):
            self.accent = THEMES[self.theme_name]["accent"]
        self._build_ui()
        self.apply_theme()
        self.after(40, self._poll_results)
        self.bind("<Return>", lambda _event: self.show_weather())
        self.protocol("WM_DELETE_WINDOW", self.close)

    @staticmethod
    def _load_preferences() -> dict[str, str]:
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_preferences(self) -> None:
        payload = json.dumps({"theme": self.theme_name, "accent": self.accent}, indent=2)
        temp = CONFIG_PATH.with_suffix(".tmp")
        try:
            temp.write_text(payload, encoding="utf-8")
            temp.replace(CONFIG_PATH)
        except OSError:
            temp.unlink(missing_ok=True)

    def _build_ui(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        header = ttk.Frame(self, padding=(30, 26, 30, 14))
        header.pack(fill="x")
        self.title_label = ttk.Label(header, text="Weather Now", style="Title.TLabel")
        self.title_label.pack(anchor="w")
        self.subtitle_label = ttk.Label(
            header, text="Current conditions, wherever you're headed.", style="Muted.TLabel"
        )
        self.subtitle_label.pack(anchor="w", pady=(4, 0))

        controls = ttk.Frame(self, padding=(30, 8, 30, 0))
        controls.pack(fill="x")
        self.entry = ttk.Entry(controls, textvariable=self.city, font=("Segoe UI", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.search_button = ttk.Button(
            controls, text="Search", style="Accent.TButton", command=self.show_weather
        )
        self.search_button.pack(side="left", padx=(10, 0), ipady=4)

        options = ttk.Frame(self, padding=(30, 12, 30, 18))
        options.pack(fill="x")
        for label, value in (("°C", "metric"), ("°F", "imperial")):
            ttk.Radiobutton(
                options, text=label, variable=self.units, value=value,
                command=self.show_weather,
            ).pack(side="left", padx=(0, 12))
        ttk.Label(options, text="Appearance", style="Muted.TLabel").pack(side="left", padx=(18, 6))
        self.theme_select = ttk.Combobox(
            options, state="readonly", width=11,
            values=("Graphite", "Midnight", "Light"),
        )
        self.theme_select.set(self.theme_name.title())
        self.theme_select.pack(side="left")
        self.theme_select.bind("<<ComboboxSelected>>", self._theme_selected)
        self.accent_button = ttk.Button(options, text="Accent colour", command=self.choose_accent)
        self.accent_button.pack(side="left", padx=(8, 0))

        self.card = ttk.Frame(self, style="Card.TFrame", padding=30)
        self.card.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        self.location_label = ttk.Label(self.card, text="Search for a city", style="Location.TLabel")
        self.location_label.pack(anchor="w")
        self.condition_label = ttk.Label(self.card, text="", style="Muted.TLabel")
        self.condition_label.pack(anchor="w", pady=(5, 20))
        self.temperature_label = ttk.Label(self.card, text="—", style="Temperature.TLabel")
        self.temperature_label.pack(anchor="w")
        self.details_label = ttk.Label(self.card, text="", justify="left", style="Body.TLabel")
        self.details_label.pack(anchor="w", pady=(20, 0))
        self.updated_label = ttk.Label(self.card, text="", style="Muted.TLabel")
        self.updated_label.pack(anchor="w", pady=(24, 0))
        self.status_label = ttk.Label(self, text="Ready", style="Muted.TLabel", padding=(30, 0, 30, 12))
        self.status_label.pack(fill="x")

    def apply_theme(self) -> None:
        palette = dict(THEMES[self.theme_name])
        palette["accent"] = self.accent
        self.configure(background=palette["background"])
        self.style.configure("TFrame", background=palette["background"])
        self.style.configure("Card.TFrame", background=palette["surface"], relief="flat")
        self.style.configure("Title.TLabel", background=palette["background"], foreground=palette["text"], font=("Segoe UI", 26, "bold"))
        self.style.configure("Muted.TLabel", background=palette["background"], foreground=palette["muted"], font=("Segoe UI", 10))
        self.style.configure("Location.TLabel", background=palette["surface"], foreground=palette["text"], font=("Segoe UI", 20, "bold"))
        self.style.configure("Temperature.TLabel", background=palette["surface"], foreground=palette["accent"], font=("Segoe UI", 52, "bold"))
        self.style.configure("Body.TLabel", background=palette["surface"], foreground=palette["text"], font=("Segoe UI", 12))
        self.style.configure("TEntry", fieldbackground=palette["surface_alt"], foreground=palette["text"], insertcolor=palette["text"], bordercolor=palette["border"], padding=10)
        self.style.configure("TCombobox", fieldbackground=palette["surface_alt"], background=palette["surface_alt"], foreground=palette["text"], arrowcolor=palette["muted"], bordercolor=palette["border"], padding=6)
        self.style.map("TCombobox", fieldbackground=[("readonly", palette["surface_alt"])], foreground=[("readonly", palette["text"])])
        self.style.configure("TButton", background=palette["surface_alt"], foreground=palette["text"], bordercolor=palette["border"], padding=(12, 8))
        self.style.map("TButton", background=[("active", palette["border"])])
        accent_foreground = _accent_foreground(palette["accent"])
        self.style.configure("Accent.TButton", background=palette["accent"], foreground=accent_foreground, font=("Segoe UI", 10, "bold"), padding=(15, 9))
        self.style.map("Accent.TButton", background=[("active", palette["accent"])], foreground=[("active", accent_foreground)])
        self.style.configure("TRadiobutton", background=palette["background"], foreground=palette["text"])
        self.style.map("TRadiobutton", background=[("active", palette["background"])], foreground=[("active", palette["text"])])
        self._save_preferences()

    def _theme_selected(self, _event=None) -> None:
        previous_default = THEMES[self.theme_name]["accent"]
        self.theme_name = self.theme_select.get().lower()
        if self.accent.lower() == previous_default.lower():
            self.accent = THEMES[self.theme_name]["accent"]
        self.apply_theme()

    def choose_accent(self) -> None:
        selected = colorchooser.askcolor(color=self.accent, parent=self, title="Choose accent colour")[1]
        if selected:
            self.accent = selected
            self.apply_theme()

    def show_weather(self) -> None:
        city = self.city.get().strip()
        if not city:
            messagebox.showwarning("City required", "Enter a city name first.", parent=self)
            return
        if not self.api_key:
            messagebox.showerror("API key missing", "Add WEATHER_API_KEY to a .env file, then restart the app.", parent=self)
            return

        self._request_id += 1
        request_id = self._request_id
        units = self.units.get()
        self.search_button.configure(state="disabled")
        self.status_label.configure(text=f"Fetching weather for {city}…")
        future = self._executor.submit(fetch_weather, city, self.api_key, units)

        def completed(task) -> None:
            try:
                result = task.result()
                error = None
            except Exception as exc:
                result, error = None, exc
            if not self._closing:
                self._results_queue.put((request_id, result, error, units))

        future.add_done_callback(completed)

    def _poll_results(self) -> None:
        if self._closing:
            return
        while True:
            try:
                request = self._results_queue.get_nowait()
            except queue.Empty:
                break
            self._finish_request(*request)
        self.after(40, self._poll_results)

    def _finish_request(self, request_id: int, data: dict[str, Any] | None, error: Exception | None, units: str) -> None:
        if self._closing or request_id != self._request_id:
            return
        self.search_button.configure(state="normal")
        if error is not None:
            self.status_label.configure(text="Weather unavailable")
            messagebox.showerror("Weather unavailable", str(error), parent=self)
            return
        assert data is not None
        try:
            temp_unit = "°F" if units == "imperial" else "°C"
            wind_unit = "mph" if units == "imperial" else "m/s"
            self.location_label.config(text=f"{data['name']}, {data['sys']['country']}")
            self.condition_label.config(text=data["weather"][0]["description"].capitalize())
            self.temperature_label.config(text=f"{data['main']['temp']:.1f}{temp_unit}")
            self.details_label.config(text=(
                f"Feels like  {data['main']['feels_like']:.1f}{temp_unit}\n"
                f"Humidity    {data['main']['humidity']}%\n"
                f"Wind        {data['wind']['speed']:.1f} {wind_unit}"
            ))
            observed = datetime.fromtimestamp(data["dt"]).strftime("%Y-%m-%d %H:%M")
            self.updated_label.config(text=f"Updated {observed}")
            self.status_label.configure(text="Weather updated")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            self.status_label.configure(text="Unexpected weather response")
            messagebox.showerror("Weather unavailable", f"Unexpected response from the weather service: {exc}", parent=self)

    def close(self) -> None:
        self._closing = True
        self._request_id += 1
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main() -> None:
    load_dotenv()
    WeatherApp().mainloop()


if __name__ == "__main__":
    main()
