"""
资料内存存储

示例服务不引入数据库：资料保存在进程内存中，重启后回到演示种子数据。
key 为 user-service 的用户 ID（字符串形式的 UUID）。
"""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class ProfileRecord:
    """用户资料"""

    user_id: str
    avatar: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# 按用户名预置的演示资料（user-service 种子用户）
_SEED_PROFILES_BY_USERNAME: dict[str, dict] = {
    "admin": {"department": "信息技术部", "position": "系统管理员"},
    "user": {"department": "研发部", "position": "测试工程师"},
    "manager": {"department": "研发部", "position": "部门经理"},
    "zhangsan": {"department": "研发部", "position": "后端工程师"},
    "lisi": {"department": "产品部", "position": "UI 设计师"},
    "wangwu": {"department": "销售部", "position": "销售经理"},
    "zhaoliu": {"department": "市场部", "position": "市场专员"},
    "guest": {"department": None, "position": None},
}


class ProfileStore:
    """线程安全的内存资料存储"""

    def __init__(self) -> None:
        self._profiles: dict[str, ProfileRecord] = {}
        self._lock = threading.Lock()

    def get_or_create(self, user_id: str, username: Optional[str] = None) -> ProfileRecord:
        """获取资料；不存在时按用户名种子创建，再没有则返回空资料"""
        with self._lock:
            record = self._profiles.get(user_id)
            if record is None:
                seed = _SEED_PROFILES_BY_USERNAME.get(username or "", {})
                record = ProfileRecord(user_id=user_id, **seed)
                self._profiles[user_id] = record
            return record

    def update(
        self,
        user_id: str,
        avatar: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
    ) -> ProfileRecord:
        """更新资料；仅更新调用方显式提供的字段（None 表示不改）"""
        with self._lock:
            record = self._profiles.get(user_id)
            if record is None:
                record = ProfileRecord(user_id=user_id)
                self._profiles[user_id] = record
            if avatar is not None:
                record.avatar = avatar
            if department is not None:
                record.department = department
            if position is not None:
                record.position = position
            return record

    def reset(self) -> None:
        """清空全部资料（演示故障恢复/测试用）"""
        with self._lock:
            self._profiles.clear()


# 全局单例
profile_store = ProfileStore()
