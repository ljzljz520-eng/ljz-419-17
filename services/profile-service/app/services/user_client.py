"""
user-service 客户端：资料服务通过 HTTP 调用用户服务获取用户基本信息

调用 user-service 的 /api/v1/auth/me，并原样转发调用方的 Authorization 头，
由用户服务负责令牌有效性与用户激活状态的最终判定。
"""

from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class UserServiceError(Exception):
    """调用 user-service 失败（网络错误、超时或非预期响应）"""


@dataclass
class UserBasicInfo:
    """用户基本信息（user-service 为权威来源）"""

    id: str
    username: str
    email: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    role: Optional[str] = None


async def fetch_current_user(authorization: str) -> UserBasicInfo:
    """
    携带调用方令牌请求 user-service 的当前用户信息。

    :param authorization: 原始 Authorization 头值，如 "Bearer xxx"
    :raises UserServiceError: user-service 不可达、超时或返回异常状态码
    """
    url = f"{settings.USER_SERVICE_URL.rstrip('/')}/api/v1/auth/me"
    try:
        async with httpx.AsyncClient(timeout=settings.USER_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers={"Authorization": authorization})
    except httpx.TimeoutException as exc:
        logger.warning("调用 user-service 超时", url=url, error=str(exc))
        raise UserServiceError("用户服务响应超时") from exc
    except httpx.HTTPError as exc:
        logger.warning("调用 user-service 失败", url=url, error=str(exc))
        raise UserServiceError("用户服务不可用") from exc

    if response.status_code != 200:
        # 401/403 透传语义由上层路由处理；其余状态码视为下游异常
        raise UserServiceError(f"用户服务返回异常状态码: {response.status_code}")

    payload = response.json()
    data = payload.get("data") or {}
    try:
        return UserBasicInfo(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            nickname=data.get("nickname"),
            avatar=data.get("avatar"),
            phone=data.get("phone"),
            bio=data.get("bio"),
            role=data.get("role"),
        )
    except (KeyError, TypeError) as exc:
        raise UserServiceError("用户服务返回数据格式异常") from exc
