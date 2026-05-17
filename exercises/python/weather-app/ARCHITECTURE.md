# Architecture Overview

## System summary

A server-rendered Flask web application with no database, no JavaScript, and no
caching layer. The browser makes a standard HTML form request; the server makes
three sequential HTTP calls to OpenWeatherMap, assembles the data, and returns a
complete HTML page. There is no client-side state.

---

## High-level request flow

```
Browser
  │
  │  POST / (form: search=london)
  ▼
┌─────────────────────────────┐
│  Flask  /  main.py          │
│  home() → redirect(/<city>) │
└─────────────┬───────────────┘
              │  302 → /london
              ▼
┌─────────────────────────────────────────────────────────┐
│  get_weather("london")                                  │
│                                                         │
│  1. GET geo/1.0/direct?q=London          ─────────────► │ ──► OpenWeatherMap
│     ◄── [{"lat": 51.5, "lon": -0.1}]                   │     Geocoding API
│                                                         │
│  2. GET data/2.5/weather?lat=51.5&lon=-0.1 ──────────► │ ──► OpenWeatherMap
│     ◄── {temp, weather, wind}                           │     Current Weather API
│                                                         │
│  3. GET data/2.5/forecast?lat=51.5&lon=-0.1 ─────────► │ ──► OpenWeatherMap
│     ◄── {list: [...40 items...]}                        │     Forecast API
│                                                         │
│  render_template("city.html", ...)                      │
└─────────────────────────────────────────────────────────┘
              │
              │  200 OK — complete HTML page
              ▼
           Browser
```

All three API calls happen **synchronously and sequentially** within a single
request. The browser blocks until all three complete.

---

## Component map

```
weather-app/
│
├── main.py                ← Entire backend. Routes + API calls + data mapping.
│                            No separate service, controller, or model layers.
│
├── templates/             ← Jinja2 server-side templates.
│   ├── index.html           Search form. No dynamic variables.
│   ├── city.html            Forecast display. Receives 9 template variables.
│   └── error.html           Static error message. No dynamic variables.
│
└── static/
    ├── css/main.css         Single stylesheet. Responsive via Grid + Flexbox.
    └── assets/              Weather icons (PNG) + background images.
                             Icon filenames are a contract with the API —
                             see "Icon-condition mapping" below.
```

---

## Route table

| Method | Path      | Handler       | Returns         | Notes |
|--------|-----------|---------------|-----------------|-------|
| GET    | `/`       | `home()`      | 200 HTML        | Search form |
| POST   | `/`       | `home()`      | 302 → `/<city>` | Redirects immediately; no API calls |
| GET    | `/<city>` | `get_weather()` | 200 HTML or 302 → `/error` | Makes all 3 OWM calls |
| GET    | `/error`  | `error()`     | 200 HTML        | Static page; no API calls |

---

## Data pipeline: `get_weather()`

The core function (`main.py:29–113`) is a single flat pipeline with no
extracted helpers. Each stage feeds directly into the next:

```
URL path parameter "london"
         │
         ▼
  string.capwords()  →  "London"           [input normalisation]
         │
         ▼
  Geocoding API call                        [I/O — resolves city to coords]
  location_data[0]["lat"], ["lon"]
         │
         ├─ empty result → redirect("/error")   [early exit]
         │
         ▼
  Current weather API call                  [I/O — conditions + wind]
  .raise_for_status()   ← called here only
  current_temp, current_weather, min/max, wind_speed
         │
         ▼
  Forecast API call                         [I/O — 40 data points]
  list comprehensions filter to noon (12:00:00) entries → 5 items
         │
         ▼
  Date arithmetic: today + timedelta(0..4) → five_day_dates_list
         │
         ▼
  render_template("city.html", 9 variables) [view rendering]
```

---

## External dependencies

### OpenWeatherMap API

Three endpoints are consumed. All require the `OWM_API_KEY` environment variable
passed as `appid=`.

| Call | Endpoint | Key params | Used fields |
|------|----------|------------|-------------|
| Geocoding | `geo/1.0/direct` | `q`, `limit=3` | `[0].lat`, `[0].lon` |
| Current weather | `data/2.5/weather` | `lat`, `lon`, `units=metric` | `main.temp`, `main.temp_min`, `main.temp_max`, `weather[0].main`, `wind.speed` |
| Forecast | `data/2.5/forecast` | `lat`, `lon`, `units=metric` | `list[*].main.temp`, `list[*].weather[0].main`, `list[*].dt_txt` |

**Geocoding is mandatory.** The older `?q=<city>` shorthand on the weather
endpoint is deprecated by OWM; coordinates must be resolved first.

**Error handling asymmetry:** `raise_for_status()` is called only on the current
weather response (`main.py:75`). A non-2xx from geocoding or forecast propagates
as a Python exception rather than an HTTP error, reaching Flask's default 500
handler.

---

## Icon-condition mapping contract

The template renders forecast icons via a direct string substitution:

```html
<img src="/static/assets/{{ current_weather.lower() }}.png">
```

This creates an **implicit contract** between the OWM `weather[0].main` field
values and the filenames in `static/assets/`. Any OWM condition string that does
not have a matching PNG produces a broken image with no fallback.

Current icon coverage:

| OWM `weather[0].main` | Asset file |
|---|---|
| `Clear` | `clear.png` |
| `Clouds` | `clouds.png` |
| `Drizzle` | `drizzle.png` |
| `Fog` | `fog.png` |
| `Haze` | `haze.png` |
| `Mist` | `mist.png` |
| `Rain` | `rain.png` |
| `Smoke` | `smoke.png` |
| `Snow` | `snow.png` |
| `Thunderstorm` | `thunderstorm.png` |
| `Tornado` | `tornado.png` |

OWM also returns `Ash`, `Dust`, `Sand`, `Squall` — none of these have
corresponding assets and would silently render a broken image.

---

## Configuration

| Source | Variable | Used in | Notes |
|--------|----------|---------|-------|
| `.env` via python-dotenv | `OWM_API_KEY` | All three API calls as `appid=` | Loaded at module import time (`main.py:7–12`). Returns `None` silently if `.env` is absent; OWM returns 401. |

There is no database, no session store, and no other configurable state.

---

## Deployment architecture

```
Internet → Gunicorn (WSGI server)
               │
               └── Flask app (main.py)
                        │
                        └── OpenWeatherMap API (external, over HTTPS)
```

The `Procfile` (`web: gunicorn main:app`) targets Heroku-style PaaS platforms.
Gunicorn manages worker processes; Flask handles routing and templating within
each worker.

There is no reverse proxy (nginx/caddy) layer defined in this repo.

---

## Architectural limitations and improvement vectors

| Limitation | Impact | Improvement |
|---|---|---|
| 3 sequential synchronous API calls per page load | ~3× latency of optimal | Replace `requests` with `httpx` + `asyncio.gather()` to run all 3 calls concurrently |
| No response caching | Same city searched twice = 6 API calls; burns OWM quota | Add `flask-caching` with a short TTL (e.g. 10 min) keyed on city name |
| Fat controller — all logic in one function | Untestable in isolation; hard to reuse | Extract `weather_service.py` with `get_coordinates()`, `get_current_weather()`, `get_forecast()` |
| Hardcoded metric units | No °F option | Accept a `?units=imperial` query param and thread it through to OWM |
| No country disambiguation | "London" always returns London UK | Add optional country code input; pass `q=London,CA` to geocoding API |
| Unhandled network/HTTP errors | Unformatted 500 on API failure | Wrap API calls in `try/except RequestException` and redirect to `/error` |
| Icon set incomplete | `Ash`, `Dust`, `Sand`, `Squall` → broken images | Add missing assets or add a fallback icon in CSS |
