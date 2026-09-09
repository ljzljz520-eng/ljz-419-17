"""健康检查路由"""

from datetime import datetime

from fastapi import APIRouter

from app.config import settings
from app.services.demo_faults import demo_faults

router = APIRouter()


@router.get("/health", summary="健康检查")
async def health_check():
    """资料服务存活检查（内存存储，无外部依赖）"""
    if demo_faults.self_fail:
        return {
            "status": "unhealthy",
            "service": settings.SERVICE_NAME,
            "timestamp": datetime.now().isoformat(),
        }
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/live", summary="存活检查")
async def liveness_check():
    return {"status": "alive"}
