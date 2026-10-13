import json
from pathlib import Path
from uuid import uuid4

from ui.styles import load_theme_preference, save_theme_preference, theme_preferences_path


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp" / "theme"


def _preference_file() -> Path:
    root = TEST_TMP_ROOT / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root / "ui_preferences.json"


def test_theme_preference_is_saved_and_loaded(monkeypatch):
    path = _preference_file()
    monkeypatch.setenv("POS_UI_PREFERENCES_FILE", str(path))

    save_theme_preference("light")

    assert theme_preferences_path() == path
    assert load_theme_preference() == "light"
    assert json.loads(path.read_text(encoding="utf-8")) == {"theme_mode": "light"}


def test_theme_preference_falls_back_to_dark_for_invalid_values(monkeypatch):
    path = _preference_file()
    monkeypatch.setenv("POS_UI_PREFERENCES_FILE", str(path))
    path.write_text('{"theme_mode": "unknown"}', encoding="utf-8")

    assert load_theme_preference() == "dark"
