"""
资料相关 Schema
"""

from typing import Optional

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    """资料更新请求（资料服务维护的字段）"""

    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    position: Optional[str] = Field(None, max_length=100, description="岗位")
