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



def test_accent_button_text_uses_readable_contrast() -> None:
    from weather_gui import _accent_foreground

    assert _accent_foreground("#326fd1") == "#ffffff"
    assert _accent_foreground("#68a9ff") == "#10151d"
    assert _accent_foreground("#b59cff") == "#10151d"


def test_invalid_accent_uses_safe_foreground_fallback() -> None:
    from weather_gui import _accent_foreground

    assert _accent_foreground("not-a-colour") == "#ffffff"
