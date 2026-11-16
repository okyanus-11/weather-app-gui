# Weather App GUI

A clean, responsive desktop weather app built with Tkinter and OpenWeatherMap.

## Features

- Search by city, optionally including a country code such as `London,GB`.
- Switch between Celsius and Fahrenheit.
- Graphite, Midnight and Light themes with a custom accent-colour picker.
- Theme and accent preferences persist between launches.
- Weather requests run in a background worker; the interface remains responsive
  while the network is slow.
- Stale results are ignored when a newer search has already started.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Put your OpenWeatherMap key in `.env`, then launch the app:

```powershell
python weather_gui.py
```

## Installation

Requires Python 3.10+, Tkinter and an OpenWeatherMap API key. Clone the repository, create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and set `WEATHER_API_KEY`. Launch with `python weather_gui.py`. Linux users may need to install their distribution's Tkinter package. See the [full installation guide](INSTALLATION.md).
