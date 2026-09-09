"""
JWT 校验工具

profile-service 不持有用户数据库，仅用与 user-service 共享的密钥
在本地验签并取出用户 ID；用户是否仍然存在/激活由 user-service 负责。
"""

from dataclasses import dataclass
from typing import Optional

from jose import JWTError, jwt

from app.config import settings


@dataclass
class TokenPrincipal:
    """从访问令牌解析出的调用方身份"""

    user_id: str
    role: Optional[str] = None
    username: Optional[str] = None


def decode_access_token(token: str) -> Optional[TokenPrincipal]:
    """验签访问令牌，失败返回 None"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None

    if payload.get("type") != "access" or not payload.get("sub"):
        return None

    return TokenPrincipal(
        user_id=payload["sub"],
        role=payload.get("role"),
        username=payload.get("username"),
    )
