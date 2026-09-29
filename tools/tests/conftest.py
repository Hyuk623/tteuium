"""Keep tool-test artifacts inside build/, including plain pytest tools/tests runs."""
from pathlib import Path
import uuid


def pytest_configure(config):
    if config.option.basetemp is None:
        root = Path(__file__).resolve().parents[2]
        config.option.basetemp = str(root / "build" / f"tool_tests_{uuid.uuid4().hex[:12]}")
