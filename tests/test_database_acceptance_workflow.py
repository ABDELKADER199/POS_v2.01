import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_full_database_acceptance_workflow_is_available():
    runner = Path(".tmp/run_acceptance_db_test.py")
    assert runner.exists()


@pytest.mark.skipif(
    os.getenv("POS_RUN_DB_ACCEPTANCE") != "1",
    reason="Database acceptance workflow creates a temporary MySQL database; set POS_RUN_DB_ACCEPTANCE=1 to run it.",
)
def test_full_database_acceptance_workflow_passes_when_enabled():
    completed = subprocess.run(
        [sys.executable, ".tmp/run_acceptance_db_test.py"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["status"] == "passed"
    assert payload["database"].startswith("stocks_acceptance_")
    assert Path(payload["report"]).exists()
