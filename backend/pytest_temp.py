"""Give pytest a fresh project-local temporary directory on Windows."""
import os
from pathlib import Path
from uuid import uuid4


def pytest_configure(config):
    # pytest's default AppData temp root may be inaccessible on some Windows
    # profiles. Reusing a fixed --basetemp is also unsafe because pytest first
    # deletes that directory. Use a new, nonexistent directory for each run.
    if config.option.basetemp is None:
        root = Path(__file__).resolve().parents[1]
        config.option.basetemp = str(root / f'.pytest-tmp-{os.getpid()}-{uuid4().hex}')
