"""Shared test setup: isolated test DB + seeded demo data + TestClient."""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Must be set BEFORE any app import: db.py creates the engine at import time.
TEST_DB = BACKEND_DIR / "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    """Build the full demo dataset into the isolated test DB once per run."""
    from seed import generate

    argv_backup = sys.argv
    sys.argv = ["seed.generate", "--reset"]
    try:
        assert generate.main() == 0, "seed failed"
    finally:
        sys.argv = argv_backup
    yield


@pytest.fixture(scope="session")
def client(seeded_db):
    from app.main import app

    with TestClient(app) as c:
        yield c
