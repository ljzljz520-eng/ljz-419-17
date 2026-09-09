"""pytest 公共夹具"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_faults import demo_faults
from app.services.store import profile_store


@pytest.fixture
def client():
    demo_faults.reset()
    profile_store.reset()
    with TestClient(app) as c:
        yield c
    demo_faults.reset()
    profile_store.reset()
