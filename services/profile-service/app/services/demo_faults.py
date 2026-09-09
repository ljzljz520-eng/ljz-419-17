"""
演示用故障开关

仅用于教学演示降级行为，生产环境不应保留：
- upstream_fail: 资料服务调用 user-service 时强制失败（模拟用户服务不可用）
- self_fail: 资料服务自身直接返回 503（模拟资料服务宕机前的错误态）
"""

import threading


class _DemoFaultState:
    def __init__(self) -> None:
        self._upstream_fail = False
        self._self_fail = False
        self._lock = threading.Lock()

    @property
    def upstream_fail(self) -> bool:
        with self._lock:
            return self._upstream_fail

    @property
    def self_fail(self) -> bool:
        with self._lock:
            return self._self_fail

    def set_upstream_fail(self, value: bool) -> None:
        with self._lock:
            self._upstream_fail = value

    def set_self_fail(self, value: bool) -> None:
        with self._lock:
            self._self_fail = value

    def reset(self) -> None:
        with self._lock:
            self._upstream_fail = False
            self._self_fail = False


demo_faults = _DemoFaultState()
