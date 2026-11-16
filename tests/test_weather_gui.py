from unittest.mock import Mock, patch

from weather_gui import fetch_weather


@patch("weather_gui.requests.get")
def test_fetch_weather_uses_selected_units(mock_get: Mock) -> None:
    response = Mock()
    response.json.return_value = {"name": "Istanbul"}
    mock_get.return_value = response
    assert fetch_weather("Istanbul", "key", "metric") == {"name": "Istanbul"}
    assert mock_get.call_args.kwargs["params"]["units"] == "metric"




def test_modern_palettes_have_complete_semantic_roles() -> None:
    from weather_gui import THEMES

    required = {"background", "surface", "surface_alt", "border", "text", "muted", "accent"}
    assert {"graphite", "midnight", "light"} <= THEMES.keys()
    for palette in THEMES.values():
        assert required <= palette.keys()
        assert all(len(palette[key]) == 7 for key in required)
