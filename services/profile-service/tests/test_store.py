"""ProfileStore 存储层测试：字段清空语义与快照持久化"""

from app.services.store import ProfileStore


def test_update_distinguishes_unset_and_none():
    """未传参保持原值，显式 None 清空字段"""
    store = ProfileStore()  # 纯内存，不持久化
    store.update(user_id="u1", department="研发部", position="工程师", avatar="https://a/1.png")

    # 只清空岗位，其余字段未传参
    store.update(user_id="u1", position=None)
    record = store.get_or_create("u1")
    assert record.department == "研发部"
    assert record.avatar == "https://a/1.png"
    assert record.position is None

    # 全部清空
    store.update(user_id="u1", department=None, avatar=None)
    record = store.get_or_create("u1")
    assert record.department is None
    assert record.avatar is None


def test_snapshot_persists_across_restart(tmp_path):
    """快照持久化：模拟容器重启（新实例加载同一快照）后修改仍在"""
    path = tmp_path / "profiles.json"
    store = ProfileStore(str(path))
    store.update(user_id="u1", department="平台工程部", position=None)

    # 模拟重启：新实例从同一快照恢复
    restored = ProfileStore(str(path))
    record = restored.get_or_create("u1")
    assert record.department == "平台工程部"
    assert record.position is None


def test_reset_clears_snapshot(tmp_path):
    """reset 清空内存的同时清空磁盘快照"""
    path = tmp_path / "profiles.json"
    store = ProfileStore(str(path))
    store.update(user_id="u1", department="研发部")
    store.reset()

    restored = ProfileStore(str(path))
    record = restored.get_or_create("u1")
    assert record.department is None


def test_corrupt_snapshot_falls_back_to_empty(tmp_path):
    """快照损坏时告警并回退为空存储，不影响服务启动"""
    path = tmp_path / "profiles.json"
    path.write_text("{not-json", encoding="utf-8")

    store = ProfileStore(str(path))
    record = store.get_or_create("u1")
    assert record.department is None
    # 服务仍可正常写入
    store.update(user_id="u1", department="研发部")
    assert ProfileStore(str(path)).get_or_create("u1").department == "研发部"
