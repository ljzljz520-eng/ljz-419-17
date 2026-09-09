"""
资料路由

演示服务间调用：资料服务在处理请求时调用 user-service 获取用户基本信息，
与本地维护的头像/部门/岗位合并后返回。user-service 故障时降级，不返回 5xx。
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header

from app.routers.deps import get_current_principal
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import get_merged_profile, update_my_profile
from app.services.security import TokenPrincipal

router = APIRouter()


@router.get("/me", response_model=dict, summary="获取当前用户的合并资料")
async def get_my_profile(
    principal: TokenPrincipal = Depends(get_current_principal),
    authorization: str = Header(..., description="调用方 JWT，原样转发给 user-service"),
):
    """
    获取当前用户资料（基本信息来自 user-service，扩展资料来自本服务）。

    user-service 不可用时返回 200 + degraded=true，仅缺失基本信息字段，
    头像/部门/岗位仍可正常展示。
    """
    merged = await get_merged_profile(principal, authorization)

    return {
        "success": True,
        "message": "获取成功" if not merged["degraded"] else "降级返回：部分数据不可用",
        "data": merged,
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/me", response_model=dict, summary="更新当前用户的扩展资料")
async def update_my_profile_api(
    payload: ProfileUpdate,
    principal: TokenPrincipal = Depends(get_current_principal),
):
    """更新头像、部门、岗位（资料服务自管字段，不依赖 user-service）"""
    profile = update_my_profile(principal, payload)

    return {
        "success": True,
        "message": "资料更新成功",
        "data": profile,
        "timestamp": datetime.now().isoformat(),
    }
