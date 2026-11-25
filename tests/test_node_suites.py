"""Run the Node test suites from pytest, so one command (python -m pytest) runs every test in the repo."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["tests/test-observed-model.mjs", "map-2/test-flight-model.mjs", "map-2/test-scenario-playback.mjs"])
def test_node_suite(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    result = subprocess.run([node, script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
