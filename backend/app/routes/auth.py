from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_token, hash_password, verify_password
from app.database import get_db
from app.deps import get_current_user
from app.models import PlatformUser
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.provision import provision_tactile_resources
from app.tactile_client import TactileAPIError

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(PlatformUser).where(PlatformUser.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    user = PlatformUser(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name or data.email.split("@")[0],
    )
    db.add(user)
    await db.flush()

    try:
        await provision_tactile_resources(
            db, user, data.email, data.password, user.display_name
        )
    except TactileAPIError as e:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Tactile 初始化失败: {e.detail}")

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        email=user.email,
        display_name=user.display_name,
        workspace_id=user.tactile_workspace_id,
        agent_id=user.tactile_agent_id,
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlatformUser).where(PlatformUser.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.tactile_token:
        try:
            await provision_tactile_resources(
                db, user, data.email, data.password, user.display_name
            )
        except TactileAPIError as e:
            raise HTTPException(status_code=502, detail=f"Tactile 连接失败: {e.detail}")

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        email=user.email,
        display_name=user.display_name,
        workspace_id=user.tactile_workspace_id,
        agent_id=user.tactile_agent_id,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: PlatformUser = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        workspace_id=current_user.tactile_workspace_id,
        agent_id=current_user.tactile_agent_id,
        create_time=current_user.create_time,
    )
