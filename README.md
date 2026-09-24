# Weather App GUI

A clean desktop weather app built with Python's included Tkinter interface and OpenWeatherMap.

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

Search by city, optionally including a country code such as `London,GB`, and switch between Celsius and Fahrenheit.

