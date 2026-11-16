import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

import generate  # noqa: E402
from metrics import build  # noqa: E402


@pytest.fixture(scope="session")
def dbs(tmp_path_factory):
    """(source, gold) built once per session from a smaller dataset."""
    folder = tmp_path_factory.mktemp("data")
    source, gold = folder / "zaffre.db", folder / "gold.db"
    generate.build(source, n_customers=800, seed=7)
    build.build(source, gold)
    return source, gold


@pytest.fixture
def con(dbs):
    connection = build.connect(*dbs)
    yield connection
    connection.close()
