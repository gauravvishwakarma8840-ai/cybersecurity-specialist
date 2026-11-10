"""
Settings Router — Organization and user profile management.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit, require_role
from app.core.security import hash_api_key, verify_password, hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import PasswordChange, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class OrgUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)


class TeamMemberCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=200)
    role: UserRole = UserRole.ANALYST
    password: str = Field(..., min_length=12)


class TeamMemberUpdateRole(BaseModel):
    role: UserRole


class TeamMemberUpdateStatus(BaseModel):
    is_active: bool



@router.get("/organization", dependencies=[Depends(rate_limit)])
async def get_organization(
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return {"id": str(org.id), "name": org.name, "slug": org.slug, "plan": org.plan, "is_active": org.is_active}


@router.patch("/organization", dependencies=[Depends(rate_limit)])
async def update_organization(
    payload: OrgUpdate,
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    if payload.name:
        org.name = payload.name
    return {"id": str(org.id), "name": org.name, "slug": org.slug}


@router.post("/organization/rotate-api-key", dependencies=[Depends(rate_limit)])
async def rotate_api_key(
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Generates a new API key for programmatic log ingestion. Shows key only once."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    new_key = f"cs_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    org.api_key_hash = hash_api_key(new_key)
    logger.info("API key rotated for org=%s", org_id)
    return {"api_key": new_key, "message": "Store this key securely — it will not be shown again."}


@router.get("/profile", response_model=UserResponse, dependencies=[Depends(rate_limit)])
async def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/profile", response_model=UserResponse, dependencies=[Depends(rate_limit)])
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.full_name:
        current_user.full_name = payload.full_name
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(rate_limit)])
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    current_user.password_hash = hash_password(payload.new_password)
    logger.info("Password changed for user=%s", current_user.id)


@router.get("/team", dependencies=[Depends(rate_limit)])
async def list_team_members(
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(User).where(User.org_id == org_id).order_by(User.created_at)
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "last_login": u.last_login,
        }
        for u in users
    ]


@router.post("/team", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit)])
async def create_team_member(
    payload: TeamMemberCreate,
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    """Adds a new team member to the organization. Admin only."""
    # Check org user limit
    org_res = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    count = (await db.execute(select(func.count()).select_from(User).where(User.org_id == org_id))).scalar_one()
    if count >= org.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization member limit reached ({org.max_users} users allowed on {org.plan} plan).",
        )

    # Check email duplicate
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    new_user = User(
        org_id=org_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    logger.info("Team member added: %s (role=%s, org=%s)", new_user.email, new_user.role.value, org.slug)
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.value,
        "is_active": new_user.is_active,
    }


@router.patch("/team/{user_id}/role", dependencies=[Depends(rate_limit)])
async def update_member_role(
    user_id: uuid.UUID,
    payload: TeamMemberUpdateRole,
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Updates a team member's role. Admin only."""
    if current_user.id == user_id and payload.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote yourself from admin role.")

    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found.")

    member.role = payload.role
    logger.info("User role updated: user=%s new_role=%s", user_id, payload.role.value)
    return {"id": str(member.id), "role": member.role.value}


@router.patch("/team/{user_id}/status", dependencies=[Depends(rate_limit)])
async def update_member_status(
    user_id: uuid.UUID,
    payload: TeamMemberUpdateStatus,
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Activates or deactivates a team member. Admin only."""
    if current_user.id == user_id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account.")

    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org_id))
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found.")

    member.is_active = payload.is_active
    logger.info("User status updated: user=%s is_active=%s", user_id, payload.is_active)
    return {"id": str(member.id), "is_active": member.is_active}

