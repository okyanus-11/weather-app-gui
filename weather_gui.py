"""A desktop weather app powered by OpenWeatherMap and Tkinter."""

from __future__ import annotations

import math
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

import requests
from dotenv import load_dotenv


API_URL = "https://api.openweathermap.org/data/2.5/weather"


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

    if (
        not _is_finite_number(measurements.get("temp"))
        or not _is_finite_number(measurements.get("feels_like"))
        or not _is_finite_number(measurements.get("humidity"))
        or not 0 <= measurements["humidity"] <= 100
        or not _is_finite_number(wind.get("speed"))
        or wind["speed"] < 0
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
        response = requests.get(API_URL, params={"q": city, "appid": api_key, "units": units}, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as error:
            raise WeatherError("OpenWeatherMap returned an invalid weather response. Please try again.") from error
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
        self.geometry("520x540")
        self.minsize(460, 500)
        self.configure(bg="#101827")
        self.units = tk.StringVar(value="metric")
        self.city = tk.StringVar(value="Istanbul")
        self.api_key = os.getenv("WEATHER_API_KEY", "")
        self._build_ui()
        self.bind("<Return>", lambda _event: self.show_weather())

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Search.TButton", font=("Segoe UI", 11, "bold"), foreground="#101827", background="#79d5ff", padding=(15, 10))
        style.map("Search.TButton", background=[("active", "#b8e9ff")])

        header = tk.Frame(self, bg="#101827", padx=32, pady=28)
        header.pack(fill="x")
        tk.Label(header, text="Weather Now", font=("Segoe UI", 27, "bold"), fg="#f7fbff", bg="#101827").pack(anchor="w")
        tk.Label(header, text="Current conditions, wherever you are headed.", font=("Segoe UI", 11), fg="#a8bad2", bg="#101827").pack(anchor="w", pady=(3, 0))

        controls = tk.Frame(self, bg="#101827", padx=32)
        controls.pack(fill="x")
        entry = tk.Entry(controls, textvariable=self.city, font=("Segoe UI", 12), bg="#f7fbff", fg="#101827", relief="flat", insertbackground="#101827")
        entry.pack(side="left", fill="x", expand=True, ipady=10)
        ttk.Button(controls, text="Search", style="Search.TButton", command=self.show_weather).pack(side="left", padx=(10, 0))

        switch = tk.Frame(self, bg="#101827", padx=32)
        switch.pack(fill="x", pady=(12, 18))
        for label, value in (("°C", "metric"), ("°F", "imperial")):
            tk.Radiobutton(switch, text=label, variable=self.units, value=value, command=self.show_weather, font=("Segoe UI", 10), fg="#d9e7f7", bg="#101827", selectcolor="#24415c", activebackground="#101827", activeforeground="#ffffff").pack(side="left", padx=(0, 12))

        self.card = tk.Frame(self, bg="#1b2a3d", padx=30, pady=26)
        self.card.pack(fill="both", expand=True, padx=32, pady=(0, 32))
        self.location_label = tk.Label(self.card, text="Search for a city", font=("Segoe UI", 21, "bold"), fg="#f7fbff", bg="#1b2a3d")
        self.location_label.pack(anchor="w")
        self.condition_label = tk.Label(self.card, text="", font=("Segoe UI", 12), fg="#a8bad2", bg="#1b2a3d")
        self.condition_label.pack(anchor="w", pady=(4, 20))
        self.temperature_label = tk.Label(self.card, text="—", font=("Segoe UI", 54, "bold"), fg="#79d5ff", bg="#1b2a3d")
        self.temperature_label.pack(anchor="w")
        self.details_label = tk.Label(self.card, text="", justify="left", font=("Segoe UI", 12), fg="#e7f1fb", bg="#1b2a3d", anchor="w")
        self.details_label.pack(anchor="w", pady=(18, 0))
        self.updated_label = tk.Label(self.card, text="", font=("Segoe UI", 9), fg="#a8bad2", bg="#1b2a3d")
        self.updated_label.pack(anchor="w", pady=(22, 0))

    def show_weather(self) -> None:
        city = self.city.get().strip()
        if not city:
            messagebox.showwarning("City required", "Enter a city name first.", parent=self)
            return
        if not self.api_key:
            messagebox.showerror("API key missing", "Add WEATHER_API_KEY to a .env file, then restart the app.", parent=self)
            return
        try:
            data = fetch_weather(city, self.api_key, self.units.get())
        except WeatherError as error:
            messagebox.showerror("Weather unavailable", str(error), parent=self)
            return

        temp_unit = "°F" if self.units.get() == "imperial" else "°C"
        wind_unit = "mph" if self.units.get() == "imperial" else "m/s"
        self.location_label.config(text=f"{data['name']}, {data['sys']['country']}")
        self.condition_label.config(text=data["weather"][0]["description"].capitalize())
        self.temperature_label.config(text=f"{data['main']['temp']:.1f}{temp_unit}")
        self.details_label.config(text=(f"Feels like  {data['main']['feels_like']:.1f}{temp_unit}\n"
                                        f"Humidity    {data['main']['humidity']}%\n"
                                        f"Wind        {data['wind']['speed']:.1f} {wind_unit}"))
        observed = datetime.fromtimestamp(data["dt"]).strftime("%Y-%m-%d %H:%M")
        self.updated_label.config(text=f"Updated {observed}")


def main() -> None:
    load_dotenv()
    WeatherApp().mainloop()


if __name__ == "__main__":
    main()
