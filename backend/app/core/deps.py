"""
FastAPI 依赖项模块 (FastAPI Dependencies Module)

提供 VigilOps 平台的通用依赖注入函数，包括用户认证、权限检查等。
基于 JWT 令牌实现用户身份验证和基于角色的访问控制（RBAC）。

Provides common dependency injection functions for the VigilOps platform,
including user authentication and permission checks. Implements user authentication
and Role-Based Access Control (RBAC) based on JWT tokens.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

# Bearer Token 认证方案 (Bearer Token Authentication Scheme)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从请求头中提取并验证 JWT，返回当前登录用户 (Extract and validate JWT from request header, return current user)
    
    解析 Authorization 头中的 Bearer Token，验证 JWT 签名和有效期，
    从数据库查询用户信息并返回。用于保护需要认证的 API 端点。
    
    Parses Bearer Token from Authorization header, validates JWT signature and expiration,
    queries user information from database and returns it. Used to protect API endpoints that require authentication.
    """
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_role(*roles: str):
    """
    角色检查依赖工厂 (Role check dependency factory)
    
    返回一个检查用户角色的依赖函数，用于实现基于角色的访问控制。
    只有拥有指定角色的用户才能访问受保护的端点。
    
    Returns a dependency function that checks user roles for Role-Based Access Control.
    Only users with specified roles can access protected endpoints.
    """
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user
    return checker


# 预定义常用角色依赖 (Predefined common role dependencies)
get_admin_user = require_role("admin")  # 仅管理员 (Admin only)
get_operator_user = require_role("admin", "operator")  # 管理员和操作员 (Admin and operator)
get_viewer_user = require_role("admin", "operator", "viewer")  # 所有角色 (All roles)
