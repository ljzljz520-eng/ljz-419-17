"""
路由公共依赖
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.security import TokenPrincipal, decode_access_token

security = HTTPBearer(auto_error=False)


async def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPrincipal:
    """本地验签 JWT，返回调用方身份"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = decode_access_token(credentials.credentials)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal
