import datetime
import requests
import string
from flask import Flask, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv
load_dotenv()

OWM_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_ENDPOINT = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_API_ENDPOINT = "http://api.openweathermap.org/geo/1.0/direct"
api_key = os.getenv("OWM_API_KEY")
# api_key = os.environ.get("OWM_API_KEY")

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():
    """Render the home page and handle city search form submission.

    GET /
        Returns the search form (index.html). No parameters.

        Response:
            200 OK — HTML search page.

    POST /
        Accepts a city name from the search form and redirects to the forecast
        page for that city.

        Form fields:
            search (str): City name entered by the user. Passed as-is to the
                          redirect URL; capitalisation is normalised downstream
                          in get_weather().

        Response:
            302 Found — Redirects to /<city>.
    """
    if request.method == "POST":
        city = request.form.get("search")
        return redirect(url_for("get_weather", city=city))
    return render_template("index.html")


@app.route("/<city>", methods=["GET", "POST"])
def get_weather(city):
    """Fetch weather data for a city and render the forecast page.

    GET /<city>
        Makes three sequential calls to the OpenWeatherMap API, then renders
        city.html with the combined results.

        Path parameters:
            city (str): City name. Case-insensitive — normalised to title case
                        via string.capwords() before being forwarded to the
                        geocoding API (e.g. "new york" → "New York").

        Upstream API calls (in order):
            1. GET geo/1.0/direct?q=<city>&limit=3&appid=<key>
               Resolves the city name to latitude/longitude coordinates.
               The first result is always used when multiple are returned.

            2. GET data/2.5/weather?lat=<lat>&lon=<lon>&units=metric&appid=<key>
               Returns current conditions for the resolved coordinates.
               raise_for_status() is called on this response — a 4xx/5xx from
               OpenWeatherMap propagates as an unhandled HTTPError.

            3. GET data/2.5/forecast?lat=<lat>&lon=<lon>&units=metric&appid=<key>
               Returns 3-hour forecast data for 5 days (40 data points).
               Only entries with a timestamp of 12:00:00 are used (5 total),
               giving one representative reading per forecast day.

        Template variables passed to city.html:
            city_name (str):              Title-cased city name.
            current_date (str):           Formatted as "Weekday, Month DD"
                                          (e.g. "Sunday, May 17").
            current_temp (int):           Current temperature in °C, rounded.
            current_weather (str):        Condition label from OWM
                                          (e.g. "Clouds", "Rain", "Clear").
                                          Also used as the icon filename:
                                          /static/assets/<lower>.png.
            min_temp (int):               Today's minimum temperature in °C.
            max_temp (int):               Today's maximum temperature in °C.
            wind_speed (float):           Wind speed in metres per second.
            five_day_temp_list (list[int]):    Noon temperatures for days 1-5.
            five_day_weather_list (list[str]): Condition labels for days 1-5.
            five_day_dates_list (list[str]):   Short weekday names for days 1-5
                                               (e.g. ["Sun", "Mon", ...]).

        Response:
            200 OK  — HTML forecast page (city.html).
            302 Found — Redirects to /error if the geocoding API returns no
                        results for the given city name.

        Error behaviour:
            - Unrecognised city → redirect to /error (no upstream API calls
              beyond geocoding).
            - Network failure or non-2xx from OpenWeatherMap → unhandled
              requests.exceptions.RequestException propagates to Flask's
              default 500 handler.
    """
    # Format city name and get current date to display on page
    city_name = string.capwords(city)
    today = datetime.datetime.now()
    current_date = today.strftime("%A, %B %d")

    # Get latitude and longitude for city
    location_params = {
        "q": city_name,
        "appid": api_key,
        "limit": 3,
    }

    location_response = requests.get(GEOCODING_API_ENDPOINT, params=location_params)
    location_data = location_response.json()

    # Prevent IndexError if user entered a city name with no coordinates by redirecting to error page
    if not location_data:
        return redirect(url_for("error"))
    else:
        lat = location_data[0]['lat']
        lon = location_data[0]['lon']

    # Get OpenWeather API data
    weather_params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    weather_response = requests.get(OWM_ENDPOINT, weather_params)
    weather_response.raise_for_status()
    weather_data = weather_response.json()

    # Get current weather data
    current_temp = round(weather_data['main']['temp'])
    current_weather = weather_data['weather'][0]['main']
    min_temp = round(weather_data['main']['temp_min'])
    max_temp = round(weather_data['main']['temp_max'])
    wind_speed = weather_data['wind']['speed']

    # Get five-day weather forecast data
    forecast_response = requests.get(OWM_FORECAST_ENDPOINT, weather_params)
    forecast_data = forecast_response.json()

    # Make lists of temperature and weather description data to show user
    five_day_temp_list = [round(item['main']['temp']) for item in forecast_data['list'] if '12:00:00' in item['dt_txt']]
    five_day_weather_list = [item['weather'][0]['main'] for item in forecast_data['list']
                             if '12:00:00' in item['dt_txt']]

    # Get next four weekdays to show user alongside weather data
    five_day_unformatted = [today, today + datetime.timedelta(days=1), today + datetime.timedelta(days=2),
                            today + datetime.timedelta(days=3), today + datetime.timedelta(days=4)]
    five_day_dates_list = [date.strftime("%a") for date in five_day_unformatted]

    return render_template("city.html", city_name=city_name, current_date=current_date, current_temp=current_temp,
                           current_weather=current_weather, min_temp=min_temp, max_temp=max_temp, wind_speed=wind_speed,
                           five_day_temp_list=five_day_temp_list, five_day_weather_list=five_day_weather_list,
                           five_day_dates_list=five_day_dates_list)


@app.route("/error")
def error():
    """Render the error page for unrecognised city names.

    GET /error
        Displays a static error message with a link back to the home page.
        Reached via redirect from get_weather() when the OpenWeatherMap
        geocoding API returns an empty result set for the searched city.

        Response:
            200 OK — HTML error page (error.html).
    """
    return render_template("error.html")


if __name__ == "__main__":
    app.run(debug=True)
