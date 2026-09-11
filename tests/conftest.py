import sys
import pytest
from PyQt6.QtWidgets import QApplication
from wiz.core.config import config


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance is initialized for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Isolate config.json to temporary directory so tests don't overwrite user config."""
    temp_config = tmp_path / "test_config.json"
    orig_file = config.config_file
    orig_data = dict(config._data)

    config.config_file = temp_config
    config._data = dict(orig_data)

    yield

    config.config_file = orig_file
    config._data = orig_data

