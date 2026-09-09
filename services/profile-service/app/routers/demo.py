"""
演示故障注入路由（仅用于教学演示降级，生产环境应移除）

- PUT /demo/faults/upstream?failed=true|false  模拟 user-service 不可用
- PUT /demo/faults/self?failed=true|false      模拟资料服务自身错误
- DELETE /demo/faults                          恢复正常
"""

from datetime import datetime

from fastapi import APIRouter, Query

from app.services.demo_faults import demo_faults

router = APIRouter(prefix="/demo")


@router.put("/faults/upstream", response_model=dict, summary="演示：开关 user-service 故障")
async def toggle_upstream_fault(
    failed: bool = Query(..., description="true=模拟用户服务调用失败"),
):
    demo_faults.set_upstream_fail(failed)
    return {
        "success": True,
        "message": f"user-service 故障模拟已{'开启' if failed else '关闭'}",
        "data": {"upstream_fail": demo_faults.upstream_fail},
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/faults/self", response_model=dict, summary="演示：开关资料服务自身故障")
async def toggle_self_fault(
    failed: bool = Query(..., description="true=模拟资料服务自身返回错误"),
):
    demo_faults.set_self_fail(failed)
    return {
        "success": True,
        "message": f"资料服务自身故障模拟已{'开启' if failed else '关闭'}",
        "data": {"self_fail": demo_faults.self_fail},
        "timestamp": datetime.now().isoformat(),
    }


@router.delete("/faults", response_model=dict, summary="演示：清除全部故障开关")
async def reset_faults():
    demo_faults.reset()
    return {
        "success": True,
        "message": "全部演示故障已清除",
        "timestamp": datetime.now().isoformat(),
    }
