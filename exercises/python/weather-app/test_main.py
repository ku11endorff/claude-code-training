import pytest
import requests as requests_lib
from unittest.mock import patch, MagicMock
from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Fixture data matching real OpenWeatherMap response shapes ---

GEOCODING_RESPONSE = [{"lat": 51.5074, "lon": -0.1278}]

CURRENT_WEATHER_RESPONSE = {
    "main": {"temp": 15.7, "temp_min": 12.3, "temp_max": 18.9},
    "weather": [{"main": "Clouds"}],
    "wind": {"speed": 5.2},
}

FORECAST_RESPONSE = {
    "list": [
        # 5 noon entries — one per forecast day
        {"main": {"temp": 15.0}, "weather": [{"main": "Clouds"}], "dt_txt": "2026-05-17 12:00:00"},
        {"main": {"temp": 12.0}, "weather": [{"main": "Rain"}],   "dt_txt": "2026-05-18 12:00:00"},
        {"main": {"temp": 14.0}, "weather": [{"main": "Clear"}],  "dt_txt": "2026-05-19 12:00:00"},
        {"main": {"temp": 16.0}, "weather": [{"main": "Clouds"}], "dt_txt": "2026-05-20 12:00:00"},
        {"main": {"temp": 11.0}, "weather": [{"main": "Rain"}],   "dt_txt": "2026-05-21 12:00:00"},
        # Non-noon entries that should be filtered out by the list comprehension
        {"main": {"temp": 10.0}, "weather": [{"main": "Snow"}],   "dt_txt": "2026-05-17 09:00:00"},
        {"main": {"temp": 10.0}, "weather": [{"main": "Snow"}],   "dt_txt": "2026-05-17 15:00:00"},
    ]
}


def _make_mock_response(json_data):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


def _weather_api_side_effect(url, *args, **kwargs):
    """Route mock responses by URL, matching the three OWM endpoints in main.py."""
    if "geo" in url:
        return _make_mock_response(GEOCODING_RESPONSE)
    elif "forecast" in url:
        return _make_mock_response(FORECAST_RESPONSE)
    else:
        return _make_mock_response(CURRENT_WEATHER_RESPONSE)


# --- Home route tests ---

class TestHomeRoute:
    def test_get_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_get_renders_search_form(self, client):
        response = client.get("/")
        assert b'name="search"' in response.data

    def test_post_redirects_to_city_route(self, client):
        response = client.post("/", data={"search": "london"})
        assert response.status_code == 302
        assert "/london" in response.headers["Location"]

    def test_post_preserves_city_name_in_redirect(self, client):
        response = client.post("/", data={"search": "new york"})
        assert "new+york" in response.headers["Location"] or "new%20york" in response.headers["Location"]


# --- Weather route tests ---

class TestGetWeatherRoute:
    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_valid_city_returns_200(self, mock_get, client):
        response = client.get("/london")
        assert response.status_code == 200

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_city_name_is_capitalized(self, mock_get, client):
        response = client.get("/london")
        assert b"London" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_multi_word_city_capitalized(self, mock_get, client):
        response = client.get("/new york")
        assert b"New York" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_current_temperature_is_rounded(self, mock_get, client):
        response = client.get("/london")
        # 15.7 rounds to 16
        assert b"16" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_current_weather_condition_displayed(self, mock_get, client):
        response = client.get("/london")
        assert b"Clouds" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_wind_speed_displayed(self, mock_get, client):
        response = client.get("/london")
        assert b"5.2" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_five_day_forecast_rendered(self, mock_get, client):
        response = client.get("/london")
        # Forecast conditions appear as icon filenames (lowercased), not as text
        assert b"rain.png" in response.data
        assert b"clear.png" in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_non_noon_forecast_entries_excluded(self, mock_get, client):
        response = client.get("/london")
        # "Snow" only appears in non-noon entries and must not be rendered
        assert b"Snow" not in response.data

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_geocoding_api_called_first(self, mock_get, client):
        client.get("/london")
        first_call_url = mock_get.call_args_list[0][0][0]
        assert "geo" in first_call_url

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_three_api_calls_made_per_request(self, mock_get, client):
        client.get("/london")
        assert mock_get.call_count == 3

    def test_invalid_city_redirects_to_error(self, client):
        with patch("main.requests.get", return_value=_make_mock_response([])):
            response = client.get("/xyznotacity")
            assert response.status_code == 302
            assert "/error" in response.headers["Location"]

    @patch("main.requests.get", side_effect=_weather_api_side_effect)
    def test_city_name_passed_to_geocoding_api(self, mock_get, client):
        client.get("/paris")
        geocoding_call = mock_get.call_args_list[0]
        params = geocoding_call[1].get("params") or geocoding_call[0][1]
        assert params["q"] == "Paris"


# --- External dependency error path tests ---

class TestExternalDependencyErrors:
    def test_network_error_on_geocoding_raises(self, client):
        with patch("main.requests.get", side_effect=requests_lib.exceptions.ConnectionError):
            with pytest.raises(requests_lib.exceptions.ConnectionError):
                client.get("/london")

    def test_network_error_on_weather_endpoint_raises(self, client):
        def fail_on_weather(url, *args, **kwargs):
            if "geo" in url:
                return _make_mock_response(GEOCODING_RESPONSE)
            raise requests_lib.exceptions.ConnectionError("network unavailable")

        with patch("main.requests.get", side_effect=fail_on_weather):
            with pytest.raises(requests_lib.exceptions.ConnectionError):
                client.get("/london")

    def test_http_error_from_weather_endpoint_raises(self, client):
        # main.py:60 calls raise_for_status() on the weather response only
        def raise_on_weather(url, *args, **kwargs):
            if "geo" in url:
                return _make_mock_response(GEOCODING_RESPONSE)
            mock = _make_mock_response({})
            mock.raise_for_status.side_effect = requests_lib.exceptions.HTTPError("503")
            return mock

        with patch("main.requests.get", side_effect=raise_on_weather):
            with pytest.raises(requests_lib.exceptions.HTTPError):
                client.get("/london")

    def test_api_key_included_in_geocoding_call(self, client):
        with patch("main.requests.get", side_effect=_weather_api_side_effect) as mock_get:
            client.get("/london")
            geocoding_call = mock_get.call_args_list[0]
            params = geocoding_call[1].get("params") or geocoding_call[0][1]
            assert "appid" in params

    def test_api_key_included_in_weather_call(self, client):
        with patch("main.requests.get", side_effect=_weather_api_side_effect) as mock_get:
            client.get("/london")
            weather_call = mock_get.call_args_list[1]
            params = weather_call[1].get("params") or weather_call[0][1]
            assert "appid" in params

    def test_api_key_included_in_forecast_call(self, client):
        with patch("main.requests.get", side_effect=_weather_api_side_effect) as mock_get:
            client.get("/london")
            forecast_call = mock_get.call_args_list[2]
            params = forecast_call[1].get("params") or forecast_call[0][1]
            assert "appid" in params

    def test_geocoding_uses_first_result_when_multiple_returned(self, client):
        multi_result = [
            {"lat": 51.5074, "lon": -0.1278},  # London, UK — should be used
            {"lat": 42.9837, "lon": -81.2497},  # London, Ontario
        ]

        def multi_geocoding_side_effect(url, *args, **kwargs):
            if "geo" in url:
                return _make_mock_response(multi_result)
            elif "forecast" in url:
                return _make_mock_response(FORECAST_RESPONSE)
            else:
                return _make_mock_response(CURRENT_WEATHER_RESPONSE)

        with patch("main.requests.get", side_effect=multi_geocoding_side_effect) as mock_get:
            client.get("/london")
            weather_call = mock_get.call_args_list[1]
            params = weather_call[1].get("params") or weather_call[0][1]
            assert params["lat"] == 51.5074
            assert params["lon"] == -0.1278

    def test_timeout_error_propagates(self, client):
        with patch("main.requests.get", side_effect=requests_lib.exceptions.Timeout):
            with pytest.raises(requests_lib.exceptions.Timeout):
                client.get("/london")


# --- Error route tests ---

class TestErrorRoute:
    def test_error_page_returns_200(self, client):
        response = client.get("/error")
        assert response.status_code == 200

    def test_error_page_shows_message(self, client):
        response = client.get("/error")
        assert b"does not exist" in response.data

    def test_error_page_has_home_link(self, client):
        response = client.get("/error")
        assert b"CHANGE CITY" in response.data
