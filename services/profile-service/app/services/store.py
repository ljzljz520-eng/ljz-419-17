"""
资料存储

轻量示例服务不引入数据库：资料保存在进程内存中，并写穿透到本地 JSON 快照文件，
容器重启后从快照恢复（快照路径由 PROFILE_STORE_PATH 配置，置空则退回纯内存模式）。
key 为 user-service 的用户 ID（字符串形式的 UUID）。
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# 区分"未传参（不修改）"与"显式传 None（清空字段）"的哨兵
_UNSET: Any = object()


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
    """线程安全的资料存储：内存读写 + JSON 快照持久化"""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._profiles: dict[str, ProfileRecord] = {}
        self._lock = threading.Lock()
        self._persist_path = Path(persist_path) if persist_path else None
        self._load()

    # ---------- 持久化 ----------

    def _load(self) -> None:
        """启动时从快照恢复；快照缺失/损坏时告警并回退为空存储，不影响服务启动"""
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
            for user_id, data in raw.items():
                self._profiles[user_id] = ProfileRecord(**data)
            logger.info("资料快照已恢复", path=str(self._persist_path), count=len(self._profiles))
        except Exception as exc:  # noqa: BLE001 - 持久化失败不应拖垮服务
            logger.warning("资料快照加载失败，使用空存储", path=str(self._persist_path), error=str(exc))

    def _save_locked(self) -> None:
        """在锁内调用：全量快照原子写入（先写临时文件再替换，避免半截文件）"""
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._persist_path.with_name(self._persist_path.name + ".tmp")
            payload = {user_id: record.to_dict() for user_id, record in self._profiles.items()}
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, self._persist_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("资料快照写入失败", path=str(self._persist_path), error=str(exc))

    # ---------- 读写 ----------

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
        avatar: Any = _UNSET,
        department: Any = _UNSET,
        position: Any = _UNSET,
    ) -> ProfileRecord:
        """更新资料；仅更新显式传入的字段（未传参表示不改，None 表示清空该字段）"""
        with self._lock:
            record = self._profiles.get(user_id)
            if record is None:
                record = ProfileRecord(user_id=user_id)
                self._profiles[user_id] = record
            if avatar is not _UNSET:
                record.avatar = avatar
            if department is not _UNSET:
                record.department = department
            if position is not _UNSET:
                record.position = position
            self._save_locked()
            return record

    def reset(self) -> None:
        """清空全部资料（演示故障恢复/测试用），同时清空磁盘快照"""
        with self._lock:
            self._profiles.clear()
            self._save_locked()


# 全局单例（PROFILE_STORE_PATH 为空字符串时仅内存，不持久化）
profile_store = ProfileStore(settings.PROFILE_STORE_PATH or None)
