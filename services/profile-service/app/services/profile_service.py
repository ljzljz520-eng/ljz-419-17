"""
资料聚合服务

合并两个服务的数据：
- user-service：用户名、邮箱、昵称、手机号等基本信息（权威来源）
- profile-service（本服务）：头像、部门、岗位

身份通过本地验签 JWT 获得（与 user-service 共享密钥）；
user-service 调用失败时执行降级：用令牌中的身份返回本服务持有的资料数据，
并在 warnings 中说明缺失字段，避免调用方拿到整页空白。
"""

from typing import Optional

import structlog

from app.schemas.profile import ProfileUpdate
from app.services.demo_faults import demo_faults
from app.services.security import TokenPrincipal
from app.services.store import profile_store
from app.services.user_client import UserBasicInfo, UserServiceError, fetch_current_user

logger = structlog.get_logger(__name__)


async def get_merged_profile(principal: TokenPrincipal, authorization: str) -> dict:
    """
    获取当前用户的合并资料。

    返回结构包含 user / profile / degraded / warnings：
    - degraded=False：user-service 调用成功，两边数据齐全
    - degraded=True：user-service 不可用，user 仅含令牌中的有限信息
    """
    basic: Optional[UserBasicInfo] = None
    warning: Optional[str] = None

    if demo_faults.upstream_fail:
        warning = "用户服务暂时不可用（演示故障），基本信息显示不完整"
        logger.warning("演示开关：跳过 user-service 调用")
    else:
        try:
            basic = await fetch_current_user(authorization)
        except UserServiceError as exc:
            warning = f"用户服务暂时不可用，基本信息显示不完整（{exc}）"
            logger.warning("user-service 降级", error=str(exc))

    if basic is not None:
        user_view = {
            "id": basic.id,
            "username": basic.username,
            "email": basic.email,
            "nickname": basic.nickname,
            "phone": basic.phone,
            "bio": basic.bio,
            "role": basic.role,
        }
        username = basic.username
    else:
        # 降级：令牌 claims 中只有 id / username / role
        user_view = {
            "id": principal.user_id,
            "username": principal.username,
            "email": None,
            "nickname": None,
            "phone": None,
            "bio": None,
            "role": principal.role,
        }
        username = principal.username

    profile = profile_store.get_or_create(user_id=principal.user_id, username=username)

    return {
        "user": user_view,
        "profile": profile.to_dict(),
        "degraded": basic is None,
        "warnings": [warning] if warning else [],
    }


def update_my_profile(principal: TokenPrincipal, payload: ProfileUpdate) -> dict:
    """更新当前用户的资料字段"""
    # 先确保资料记录存在（保留种子部门/岗位），再做局部更新
    profile_store.get_or_create(user_id=principal.user_id, username=principal.username)
    record = profile_store.update(
        user_id=principal.user_id,
        avatar=payload.avatar,
        department=payload.department,
        position=payload.position,
    )
    return record.to_dict()
