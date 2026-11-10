from unittest.mock import Mock, patch

import pytest

from weather_gui import WeatherError, fetch_weather


def valid_weather_data() -> dict[str, object]:
    return {
        "name": "Istanbul",
        "sys": {"country": "TR"},
        "weather": [{"description": "clear sky"}],
        "main": {"temp": 20.0, "feels_like": 19.0, "humidity": 50},
        "wind": {"speed": 3.5},
        "dt": 1_700_000_000,
    }


@patch("weather_gui.requests.get")
def test_fetch_weather_uses_selected_units(mock_get: Mock) -> None:
    response = Mock()
    response.json.return_value = valid_weather_data()
    mock_get.return_value = response
    assert fetch_weather("Istanbul", "key", "metric") == valid_weather_data()
    assert mock_get.call_args.kwargs["params"]["units"] == "metric"


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {"name": "Istanbul"},
        {**valid_weather_data(), "weather": []},
        {**valid_weather_data(), "weather": [None]},
        {**valid_weather_data(), "main": {"temp": "20", "feels_like": 19, "humidity": 50}},
        {**valid_weather_data(), "main": {"temp": 20, "humidity": 50}},
        {**valid_weather_data(), "main": {"temp": 20, "feels_like": 19, "humidity": True}},
        {**valid_weather_data(), "wind": {"speed": float("nan")}},
        {**valid_weather_data(), "dt": "1700000000"},
        {**valid_weather_data(), "dt": 10**1000},
    ],
)
@patch("weather_gui.requests.get")
def test_fetch_weather_rejects_malformed_success_response(mock_get: Mock, data: object) -> None:
    response = Mock()
    response.json.return_value = data
    mock_get.return_value = response
    with pytest.raises(WeatherError, match="invalid weather response"):
        fetch_weather("Istanbul", "key", "metric")


@patch("weather_gui.requests.get")
def test_fetch_weather_rejects_invalid_json(mock_get: Mock) -> None:
    response = Mock()
    response.json.side_effect = ValueError("invalid JSON")
    mock_get.return_value = response
    with pytest.raises(WeatherError, match="invalid weather response"):
        fetch_weather("Istanbul", "key", "metric")
