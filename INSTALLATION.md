# Installation

## Requirements
- Python 3.10 or newer
- An OpenWeatherMap API key
- A graphical desktop session (Tkinter must be available)

## Windows (PowerShell)

```powershell
git clone https://github.com/okyanus-11/weather-app-gui.git
cd weather-app-gui
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `WEATHER_API_KEY` to your OpenWeatherMap API key. Do not share or commit the key. Launch:

```powershell
python weather_gui.py
```

## Linux

Install your distribution's Tkinter package first (often named `python3-tk`), then:

```bash
git clone https://github.com/okyanus-11/weather-app-gui.git
cd weather-app-gui
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set `WEATHER_API_KEY` in `.env` and run `python weather_gui.py`.
