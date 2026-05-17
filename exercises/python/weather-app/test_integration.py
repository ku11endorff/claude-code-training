"""
Integration tests for the weather app.

Unlike test_main.py (which patches requests.get at the Python level), these
tests use the `responses` library to intercept at the HTTP transport layer.
The full requests call runs — URL construction, param encoding, JSON parsing —
so bugs in how main.py builds API calls are caught here but not in unit tests.
"""

import pytest
import responses as responses_lib
from urllib.parse import urlparse, parse_qs
from main import app, OWM_ENDPOINT, OWM_FORECAST_ENDPOINT, GEOCODING_API_ENDPOINT


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Shared fixture data ---

GEOCODING_PAYLOAD = [{"lat": 48.8566, "lon": 2.3522, "name": "Paris"}]

CURRENT_WEATHER_PAYLOAD = {
    "main": {"temp": 22.4, "temp_min": 18.1, "temp_max": 26.8},
    "weather": [{"main": "Clear"}],
    "wind": {"speed": 3.1},
}

FORECAST_PAYLOAD = {
    "list": [
        {"main": {"temp": 22.0}, "weather": [{"main": "Clear"}],  "dt_txt": "2026-05-17 12:00:00"},
        {"main": {"temp": 19.0}, "weather": [{"main": "Clouds"}], "dt_txt": "2026-05-18 12:00:00"},
        {"main": {"temp": 17.0}, "weather": [{"main": "Rain"}],   "dt_txt": "2026-05-19 12:00:00"},
        {"main": {"temp": 21.0}, "weather": [{"main": "Clear"}],  "dt_txt": "2026-05-20 12:00:00"},
        {"main": {"temp": 20.0}, "weather": [{"main": "Clouds"}], "dt_txt": "2026-05-21 12:00:00"},
        # Off-hours entries — must be excluded from forecast lists
        {"main": {"temp": 5.0},  "weather": [{"main": "Tornado"}], "dt_txt": "2026-05-17 06:00:00"},
        {"main": {"temp": 5.0},  "weather": [{"main": "Tornado"}], "dt_txt": "2026-05-17 18:00:00"},
    ]
}


def register_all_weather_endpoints():
    """Register all three OWM API endpoints with the responses interceptor."""
    responses_lib.add(responses_lib.GET, GEOCODING_API_ENDPOINT, json=GEOCODING_PAYLOAD, status=200)
    responses_lib.add(responses_lib.GET, OWM_ENDPOINT, json=CURRENT_WEATHER_PAYLOAD, status=200)
    responses_lib.add(responses_lib.GET, OWM_FORECAST_ENDPOINT, json=FORECAST_PAYLOAD, status=200)


# --- Home route integration ---

class TestHomeIntegration:
    def test_get_home_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_home_contains_search_form(self, client):
        response = client.get("/")
        assert b'method="post"' in response.data
        assert b'name="search"' in response.data

    def test_post_redirects_to_city_url(self, client):
        response = client.post("/", data={"search": "paris"})
        assert response.status_code == 302
        assert "paris" in response.headers["Location"]

    def test_post_follows_redirect_to_weather_page(self, client):
        with responses_lib.RequestsMock() as rsps:
            rsps.add(responses_lib.GET, GEOCODING_API_ENDPOINT, json=GEOCODING_PAYLOAD)
            rsps.add(responses_lib.GET, OWM_ENDPOINT, json=CURRENT_WEATHER_PAYLOAD)
            rsps.add(responses_lib.GET, OWM_FORECAST_ENDPOINT, json=FORECAST_PAYLOAD)
            response = client.post("/", data={"search": "paris"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Paris" in response.data


# --- Weather route integration: verifying HTTP requests sent to OWM ---

class TestWeatherApiCallIntegration:
    @responses_lib.activate
    def test_geocoding_endpoint_is_called(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        called_urls = [call.request.url for call in responses_lib.calls]
        assert any("geo/1.0/direct" in url for url in called_urls)

    @responses_lib.activate
    def test_geocoding_receives_capitalized_city_name(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        geocoding_call = next(c for c in responses_lib.calls if "geo" in c.request.url)
        params = parse_qs(urlparse(geocoding_call.request.url).query)
        assert params["q"] == ["Paris"]

    @responses_lib.activate
    def test_weather_endpoint_receives_metric_units(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        weather_call = next(
            c for c in responses_lib.calls
            if "data/2.5/weather" in c.request.url
        )
        params = parse_qs(urlparse(weather_call.request.url).query)
        assert params["units"] == ["metric"]

    @responses_lib.activate
    def test_weather_endpoint_receives_coordinates_from_geocoding(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        weather_call = next(
            c for c in responses_lib.calls
            if "data/2.5/weather" in c.request.url
        )
        params = parse_qs(urlparse(weather_call.request.url).query)
        assert params["lat"] == [str(GEOCODING_PAYLOAD[0]["lat"])]
        assert params["lon"] == [str(GEOCODING_PAYLOAD[0]["lon"])]

    @responses_lib.activate
    def test_forecast_endpoint_called_with_same_coordinates(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        forecast_call = next(
            c for c in responses_lib.calls
            if "data/2.5/forecast" in c.request.url
        )
        params = parse_qs(urlparse(forecast_call.request.url).query)
        assert params["lat"] == [str(GEOCODING_PAYLOAD[0]["lat"])]
        assert params["lon"] == [str(GEOCODING_PAYLOAD[0]["lon"])]

    @responses_lib.activate
    def test_exactly_three_http_calls_made(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        assert len(responses_lib.calls) == 3

    @responses_lib.activate
    def test_api_calls_made_in_correct_order(self, client):
        register_all_weather_endpoints()
        client.get("/paris")
        urls = [call.request.url for call in responses_lib.calls]
        assert "geo" in urls[0]
        assert "data/2.5/weather" in urls[1]
        assert "data/2.5/forecast" in urls[2]


# --- Weather route integration: verifying rendered HTML output ---

class TestWeatherResponseIntegration:
    @responses_lib.activate
    def test_city_name_rendered_in_response(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        assert b"Paris" in response.data

    @responses_lib.activate
    def test_temperature_rounded_and_rendered(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        # 22.4 rounds to 22
        assert b"22" in response.data

    @responses_lib.activate
    def test_weather_condition_rendered(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        assert b"Clear" in response.data

    @responses_lib.activate
    def test_wind_speed_rendered(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        assert b"3.1" in response.data

    @responses_lib.activate
    def test_forecast_icons_use_lowercased_condition_names(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        assert b"clouds.png" in response.data
        assert b"rain.png" in response.data

    @responses_lib.activate
    def test_off_hours_condition_excluded_from_render(self, client):
        register_all_weather_endpoints()
        response = client.get("/paris")
        # "Tornado" only appears in non-noon fixture entries
        assert b"tornado.png" not in response.data


# --- Error flow integration ---

class TestErrorFlowIntegration:
    @responses_lib.activate
    def test_unknown_city_redirects_to_error_page(self, client):
        responses_lib.add(responses_lib.GET, GEOCODING_API_ENDPOINT, json=[], status=200)
        response = client.get("/xyznotacity")
        assert response.status_code == 302
        assert "/error" in response.headers["Location"]

    @responses_lib.activate
    def test_unknown_city_makes_only_one_api_call(self, client):
        responses_lib.add(responses_lib.GET, GEOCODING_API_ENDPOINT, json=[], status=200)
        client.get("/xyznotacity")
        # Must short-circuit after geocoding — weather/forecast must not be called
        assert len(responses_lib.calls) == 1

    def test_error_page_renders_correctly(self, client):
        response = client.get("/error")
        assert response.status_code == 200
        assert b"does not exist" in response.data

    def test_error_page_links_back_to_home(self, client):
        response = client.get("/error")
        assert b'href="/"' in response.data
