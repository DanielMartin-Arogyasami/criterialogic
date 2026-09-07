"""Local .env loading. Does not read the repo .env — that file may hold a real key."""
import os

from criterialogic.env import load_dotenv


def test_load_dotenv_does_not_override_existing(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("CRITERIALOGIC_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("CRITERIALOGIC_TEST_KEY", "from-process")
    load_dotenv(path)
    assert os.environ["CRITERIALOGIC_TEST_KEY"] == "from-process"


def test_load_dotenv_fills_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("CRITERIALOGIC_TEST_KEY_2", raising=False)
    path = tmp_path / ".env"
    path.write_text('CRITERIALOGIC_TEST_KEY_2="quoted-value"\n', encoding="utf-8")
    load_dotenv(path)
    assert os.environ["CRITERIALOGIC_TEST_KEY_2"] == "quoted-value"
