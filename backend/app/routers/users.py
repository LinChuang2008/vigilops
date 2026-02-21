"""
用户管理路由模块

提供用户的增删改查接口，仅管理员可操作。
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserListResponse, PasswordReset
from app.services.audit import log_audit

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """获取用户列表（分页），仅管理员可访问。"""
    total = (await db.execute(select(func.count(User.id)))).scalar()
    result = await db.execute(
        select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    return UserListResponse(
        items=[UserOut.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """创建新用户，仅管理员可操作。"""
    # 验证角色值
    if data.role not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="角色必须为 admin / operator / viewer")

    # 检查邮箱唯一性
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()

    await log_audit(db, admin.id, "create_user", "user", user.id,
                    json.dumps({"email": data.email, "role": data.role}),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """获取指定用户详情，仅管理员可访问。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """编辑用户信息（name/role/is_active），仅管理员可操作。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 保护 demo 账号不可编辑
    if user.email == "demo@vigilops.io":
        raise HTTPException(status_code=403, detail="Demo 账号不可编辑")

    updates = data.model_dump(exclude_unset=True)

    # 验证角色值
    if "role" in updates and updates["role"] not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="角色必须为 admin / operator / viewer")

    for field, value in updates.items():
        setattr(user, field, value)

    await log_audit(db, admin.id, "update_user", "user", user_id,
                    json.dumps(updates),
                    request.client.host if request.client else None)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """删除用户，管理员不能删除自己。"""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 保护 demo 账号不可删除
    if user.email == "demo@vigilops.io":
        raise HTTPException(status_code=403, detail="Demo 账号不可删除")

    await log_audit(db, admin.id, "delete_user", "user", user_id,
                    json.dumps({"email": user.email}),
                    request.client.host if request.client else None)
    await db.delete(user)
    await db.commit()


@router.put("/{user_id}/password", status_code=status.HTTP_200_OK)
async def reset_password(
    user_id: int,
    data: PasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """重置用户密码，仅管理员可操作。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 保护 demo 账号密码不可修改
    if user.email == "demo@vigilops.io":
        raise HTTPException(status_code=403, detail="Demo 账号密码不可修改")

    user.hashed_password = hash_password(data.new_password)

    await log_audit(db, admin.id, "reset_password", "user", user_id,
                    None,
                    request.client.host if request.client else None)
    await db.commit()
    return {"status": "ok"}
