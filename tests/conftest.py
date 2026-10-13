import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path():
    base_dir = Path(__file__).resolve().parents[1] / ".tmp" / "pytest-runs"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="test-", dir=base_dir))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
