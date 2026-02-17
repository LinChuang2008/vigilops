"""
用户管理相关的请求/响应数据模型。

定义用户创建、更新、密码重置等操作的 Schema。
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """创建用户请求体。"""
    email: EmailStr
    name: str
    password: str
    role: str = "viewer"  # admin / operator / viewer


class UserUpdate(BaseModel):
    """更新用户请求体，所有字段可选。"""
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    """重置密码请求体。"""
    new_password: str


class UserOut(BaseModel):
    """用户信息响应模型。"""
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """用户列表分页响应。"""
    items: List[UserOut]
    total: int
    page: int
    page_size: int
