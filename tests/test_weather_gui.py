from unittest.mock import Mock, patch

from weather_gui import fetch_weather


@patch("weather_gui.requests.get")
def test_fetch_weather_uses_selected_units(mock_get: Mock) -> None:
    response = Mock()
    response.json.return_value = {"name": "Istanbul"}
    mock_get.return_value = response
    assert fetch_weather("Istanbul", "key", "metric") == {"name": "Istanbul"}
    assert mock_get.call_args.kwargs["params"]["units"] == "metric"

