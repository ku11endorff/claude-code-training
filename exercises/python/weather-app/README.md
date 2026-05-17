# Weather App

A responsive Flask web application that displays current conditions and a 5-day forecast for any city, powered by the [OpenWeatherMap API](https://openweathermap.org/api).

## Screenshots

**Desktop**

<img src="/screenshots/weather_app_desktop_home_page_screenshot.png" alt="Home page">
<img src="/screenshots/weather_app_desktop_forecast_page_screenshot.png" alt="Forecast page">
<img src="/screenshots/weather_app_desktop_error_page_screenshot.png" alt="Error page">

**Mobile**

<img src="/screenshots/weather_app_iphone_home_page_screenshot.png" style="width:400px;" alt="Mobile home"> <img src="/screenshots/weather_app_iphone_forecast_page_screenshot.png" style="width:400px;" alt="Mobile forecast">

---

## Features

- Current temperature, weather condition, and wind speed for any city
- 5-day forecast filtered to midday readings
- Responsive layout (CSS Grid + Flexbox) for desktop and mobile
- Graceful error page for unrecognised city names

---

## Prerequisites

- Python 3.8+
- A free [OpenWeatherMap API key](https://home.openweathermap.org/users/sign_up)

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd weather-app

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

Create a `.env` file in the project root:

```bash
OWM_API_KEY=your_api_key_here
```

The app reads this value via `python-dotenv` at startup (`main.py:7-12`). The `.gitignore` already excludes `.env` — never commit your key.

---

## Running the app

### Development

```bash
python main.py
```

Flask's built-in server starts on `http://127.0.0.1:5000` with hot-reload enabled (`debug=True`).

### Production

The included `Procfile` configures [Gunicorn](https://gunicorn.org/) for deployment:

```bash
gunicorn main:app
```

Default port is 8000. To specify a port:

```bash
gunicorn main:app --bind 0.0.0.0:5000
```

---

## Usage

1. Open `http://localhost:5000` in a browser.
2. Type a city name into the search box and press Enter.
3. The forecast page shows:
   - Today's temperature (°C), weather condition, min/max range, and wind speed
   - A 5-day strip showing the noon forecast for each day

**Example cities to try:** `London`, `Tokyo`, `New York`, `São Paulo`, `Cape Town`

If the city name is not recognised by the OpenWeatherMap geocoding API, the app redirects to an error page with a link back to the search form.

---

## Project structure

```
weather-app/
├── main.py                  # Flask app — all routes and API calls
├── requirements.txt         # Python dependencies
├── Procfile                 # Gunicorn entry point for PaaS deployment
├── .env                     # API key (not committed — create this yourself)
├── templates/
│   ├── index.html           # Home page with search form
│   ├── city.html            # Forecast display page
│   └── error.html           # Invalid city error page
├── static/
│   ├── css/main.css         # Single stylesheet (responsive)
│   └── assets/              # Weather condition icons + background images
├── test_main.py             # Unit tests (mock at requests.get level)
└── test_integration.py      # Integration tests (mock at HTTP transport level)
```

### API endpoints used

| Endpoint | Purpose |
|---|---|
| `geo/1.0/direct` | Resolve city name → latitude/longitude |
| `data/2.5/weather` | Current weather conditions |
| `data/2.5/forecast` | 5-day / 3-hour forecast |

All three calls happen sequentially in `get_weather()` (`main.py:29-87`) on each page request.

---

## Running tests

Install pytest if not already present:

```bash
pip install pytest
```

Run all tests:

```bash
pytest test_main.py test_integration.py -v
```

| File | Type | Count | What's tested |
|---|---|---|---|
| `test_main.py` | Unit | 27 | Route handlers, data transformation, API call structure, network/HTTP error paths |
| `test_integration.py` | Integration | 21 | Full HTTP pipeline, query param encoding, API call ordering, error short-circuit |

No live network calls are made during tests — all OpenWeatherMap responses are intercepted by mocks.

---

## Known limitations

- **Units are hardcoded to metric (°C).** There is no toggle for Fahrenheit.
- **All 3 API calls are synchronous and sequential.** Each page load waits for ~3 round trips. A future improvement would use `httpx` with `async`/`await` to run them concurrently.
- **No caching.** Searching the same city twice makes 6 API calls. Adding a short TTL cache (e.g. `flask-caching`) would reduce latency and API quota usage.
- **The 5-day forecast uses noon readings only.** This is a reasonable approximation but not the true daily high/low.
- **No country disambiguation.** Searching "London" always returns the first geocoding result (London, UK). A future improvement would let users specify a country code.

---

## Credits

Original application by [Rachana Hegde](https://rachanahegde.squarespace.com/).

**Icons** from [Icons8](https://icons8.com): Wind, Thermometer, Clouds, Rain, Fog, Snow, Drizzle, Thunderstorm, Search, Chevron Left, Clear (Summer), Tornado

**Background images** from [Unsplash](https://unsplash.com):
[Home page](https://unsplash.com/photos/2KXEb_8G5vo) · [Error page](https://unsplash.com/photos/U-Kty6HxcQc)
