import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.festival import Festival
from deauville.storage import JsonStorage, MemoryStorage

DATA = Path(__file__).parent.parent / "data" / "festival.json"


@pytest.fixture
def raw() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@pytest.fixture
def festival(raw) -> Festival:
    return Festival.open(MemoryStorage(raw))


@pytest.fixture
def json_storage(tmp_path) -> JsonStorage:
    copy = tmp_path / "festival.json"
    copy.write_text(DATA.read_text(encoding="utf-8"), encoding="utf-8")
    return JsonStorage(copy)


@pytest.fixture
def client(json_storage) -> TestClient:
    return TestClient(create_app(json_storage))
