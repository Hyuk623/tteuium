"""SQLite connection factory with transactional writes and FK enforcement."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        if "action_date" not in {row["name"] for row in connection.execute("PRAGMA table_info(actions)")}:
            connection.execute("ALTER TABLE actions ADD COLUMN action_date TEXT")
