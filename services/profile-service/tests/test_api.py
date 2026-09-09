"""profile-service API 测试"""

from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.config import settings
from app.services import profile_service
from app.services.demo_faults import demo_faults
from app.services.user_client import UserBasicInfo, UserServiceError

API = "/api/v1/profiles"


def make_access_token(user_id="11111111-1111-1111-1111-111111111111", username="zhangsan", role="user"):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "type": "access",
        "role": role,
        "username": username,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_access_token()}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_me_requires_token(client):
    resp = client.get(f"{API}/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "UNAUTHORIZED"


def test_me_rejects_invalid_token(client):
    resp = client.get(f"{API}/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_get_merged_profile_success(client, auth_headers, monkeypatch):
    """user-service 正常时返回两边合并数据"""

    async def fake_fetch(authorization):
        assert authorization.startswith("Bearer ")
        return UserBasicInfo(
            id="11111111-1111-1111-1111-111111111111",
            username="zhangsan",
            email="zhangsan@example.com",
            nickname="张三",
            phone="13800000000",
            role="user",
        )

    monkeypatch.setattr(profile_service, "fetch_current_user", fake_fetch)

    resp = client.get(f"{API}/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["degraded"] is False
    assert data["warnings"] == []
    assert data["user"]["username"] == "zhangsan"
    assert data["user"]["email"] == "zhangsan@example.com"
    # 资料侧种子数据
    assert data["profile"]["department"] == "研发部"
    assert data["profile"]["position"] == "后端工程师"
    assert data["profile"]["user_id"] == "11111111-1111-1111-1111-111111111111"


def test_get_profile_degrades_when_user_service_down(client, auth_headers, monkeypatch):
    """user-service 调用失败时降级：200 + degraded + 资料仍可用，页面不会全空"""

    async def failing_fetch(authorization):
        raise UserServiceError("用户服务不可用")

    monkeypatch.setattr(profile_service, "fetch_current_user", failing_fetch)

    resp = client.get(f"{API}/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["degraded"] is True
    assert len(data["warnings"]) == 1
    # 基本信息只剩令牌里的内容，邮箱等为空
    assert data["user"]["username"] == "zhangsan"
    assert data["user"]["email"] is None
    # 资料数据仍可展示
    assert data["profile"]["department"] == "研发部"


def test_get_profile_degrades_via_demo_switch(client, auth_headers):
    """演示开关模拟上游故障时同样降级，且不应触发真实 HTTP 调用"""
    demo_faults.set_upstream_fail(True)

    resp = client.get(f"{API}/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["degraded"] is True
    assert data["profile"] is not None


def test_update_profile_without_user_service(client, auth_headers):
    """更新资料只依赖本服务内存存储，不调用 user-service"""
    resp = client.put(
        f"{API}/me",
        headers=auth_headers,
        json={"department": "平台工程部", "position": "架构师", "avatar": "https://example.com/a.png"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["department"] == "平台工程部"
    assert data["position"] == "架构师"
    assert data["avatar"] == "https://example.com/a.png"


def test_update_profile_partial(client, auth_headers):
    client.put(f"{API}/me", headers=auth_headers, json={"position": "技术负责人"})
    # 上游故障时走降级路径，但本服务数据仍在
    demo_faults.set_upstream_fail(True)
    resp = client.get(f"{API}/me", headers=auth_headers)
    data = resp.json()["data"]
    assert data["degraded"] is True
    assert data["profile"]["position"] == "技术负责人"
    # 未传的部门保留种子值
    assert data["profile"]["department"] == "研发部"


def test_update_profile_validation(client, auth_headers):
    resp = client.put(
        f"{API}/me",
        headers=auth_headers,
        json={"department": "x" * 101},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_demo_self_fault_returns_503(client, auth_headers):
    client.put(f"{API}/demo/faults/self?failed=true")
    resp = client.get(f"{API}/me", headers=auth_headers)
    assert resp.status_code == 503
    assert resp.json()["error_code"] == "SERVICE_UNAVAILABLE"

    # 管理接口自身仍可用，能够关闭故障
    client.delete(f"{API}/demo/faults")
    resp = client.get("/health")
    assert resp.json()["status"] == "healthy"
