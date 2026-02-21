"""
用户认证路由模块 (User Authentication Router)

功能说明：提供用户注册、登录、JWT令牌管理等认证相关接口
核心职责：
  - 用户注册（首个用户自动设为管理员）
  - 用户登录验证与令牌生成
  - JWT访问令牌和刷新令牌管理
  - 获取当前用户信息
依赖关系：依赖 SQLAlchemy、JWT安全模块、审计服务
API端点：POST /register, POST /login, POST /refresh, GET /me

Author: VigilOps Team
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, TokenRefresh, UserResponse
from app.services.audit import log_audit

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    用户注册接口 (User Registration)
    
    新用户注册功能，系统中第一个注册的用户将自动成为管理员。
    
    Args:
        data: 用户注册数据（邮箱、姓名、密码）
        db: 数据库会话依赖注入
    Returns:
        TokenResponse: 包含访问令牌和刷新令牌的响应
    Raises:
        HTTPException 409: 邮箱已被注册
    流程：
        1. 检查邮箱唯一性
        2. 统计现有用户数量，决定权限角色
        3. 创建用户并保存到数据库
        4. 生成并返回JWT令牌
    """
    # 检查邮箱唯一性约束 (Check email uniqueness constraint)
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # 第一个用户自动设为管理员，后续用户默认为观察者 (First user becomes admin automatically)
    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar()
    role = "admin" if user_count == 0 else "viewer"

    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """
    用户登录接口 (User Login)
    
    验证用户凭证并生成访问令牌，同时记录审计日志。
    
    Args:
        data: 用户登录数据（邮箱、密码）
        request: HTTP请求对象（用于获取客户端IP）
        db: 数据库会话依赖注入
    Returns:
        TokenResponse: 包含访问令牌和刷新令牌的响应
    Raises:
        HTTPException 401: 凭证无效（邮箱不存在或密码错误）
        HTTPException 403: 账户已禁用
    流程：
        1. 根据邮箱查找用户
        2. 验证密码哈希值
        3. 检查账户状态
        4. 记录登录审计日志
        5. 生成并返回JWT令牌
    """
    # 根据邮箱查找用户 (Find user by email)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    # 验证用户存在性和密码正确性 (Verify user existence and password)
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # 检查账户是否被禁用 (Check if account is disabled)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # 记录登录审计日志，包含客户端IP (Log login audit with client IP)
    await log_audit(db, user.id, "login", "user", user.id,
                    None, request.client.host if request.client else None)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """
    令牌刷新接口 (Token Refresh)
    
    使用有效的刷新令牌获取新的访问令牌和刷新令牌。
    
    Args:
        data: 令牌刷新数据（包含刷新令牌）
        db: 数据库会话依赖注入
    Returns:
        TokenResponse: 包含新的访问令牌和刷新令牌
    Raises:
        HTTPException 401: 刷新令牌无效或已过期，或用户不存在
    流程：
        1. 解析并验证刷新令牌
        2. 检查令牌类型是否为 refresh
        3. 根据用户ID查找并验证用户状态
        4. 生成新的访问令牌和刷新令牌
    """
    # 解析刷新令牌载荷 (Decode refresh token payload)
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # 从令牌中提取用户ID并验证用户状态 (Extract user ID and verify user status)
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息 (Get Current User)
    
    基于JWT令牌获取当前登录用户的详细信息。
    
    Args:
        current_user: 当前用户对象（通过JWT依赖注入获得）
    Returns:
        UserResponse: 用户信息响应（ID、邮箱、姓名、角色等）
    流程：
        1. 通过JWT中间件验证访问令牌
        2. 从数据库获取用户信息
        3. 返回用户详情（不包含敏感信息）
    """
    return current_user
