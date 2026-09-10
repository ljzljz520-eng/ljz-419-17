"""pytest 公共夹具"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_faults import demo_faults
from app.services.store import profile_store


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 持久化快照重定向到临时目录，避免测试读写真实数据文件
    monkeypatch.setattr(profile_store, "_persist_path", tmp_path / "profiles.json")
    demo_faults.reset()
    profile_store.reset()
    with TestClient(app) as c:
        yield c
    demo_faults.reset()
    profile_store.reset()
