"""
认证相关请求/响应模型

定义用户注册、登录、令牌刷新等 API 的数据结构。
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    """用户注册请求体。"""
    email: EmailStr
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度至少为 8 个字符")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        if not any(c.isalpha() for c in v):
            raise ValueError("密码必须包含至少一个字母")
        return v


class UserLogin(BaseModel):
    """用户登录请求体。"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """令牌响应体，包含访问令牌和刷新令牌。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """令牌刷新请求体。"""
    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应体。"""
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
