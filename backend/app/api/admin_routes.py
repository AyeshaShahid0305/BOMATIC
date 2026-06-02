"""
Admin routes - require role='admin'.

GET  /api/admin/opportunities                 all opportunities across all engineers
GET  /api/admin/users                         all registered users
POST /api/admin/users/{user_id}/deactivate    deactivate a user account
POST /api/admin/users/{user_id}/activate      reactivate a user account
GET  /api/admin/stats                         platform-wide counts
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db import get_db
from app.models.opportunity import Opportunity
from app.models.pipeline_state import PipelineState
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Opportunities - all, regardless of owner
# ---------------------------------------------------------------------------

@router.get("/opportunities")
def admin_list_opportunities(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return all opportunities across all engineers with pipeline progress."""
    rows = (
        db.query(Opportunity, PipelineState)
        .join(PipelineState, PipelineState.opportunity_id == Opportunity.id)
        .order_by(Opportunity.created_at.desc())
        .all()
    )

    return [
        {
            "opportunity_id": opp.opportunity_id,
            "project_name": opp.project_name,
            "client_name": opp.client_name,
            "mode": opp.mode,
            "status": opp.status,
            "current_step": pipeline.current_step,
            "created_at": opp.created_at.isoformat(),
            "updated_at": opp.updated_at.isoformat(),
            "owner_user_id": str(opp.user_id) if opp.user_id else None,
            "engines_completed": list((pipeline.step_outputs or {}).keys()),
        }
        for opp, pipeline in rows
    ]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
def admin_list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return all registered users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users/{user_id}/deactivate")
def admin_deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Deactivate a user account; they can no longer log in."""
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()
    return {"id": user_id, "is_active": False, "message": f"{user.email} deactivated."}


@router.post("/users/{user_id}/activate")
def admin_activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Reactivate a deactivated user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    return {"id": user_id, "is_active": True, "message": f"{user.email} activated."}


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Platform-wide statistics."""
    total_opps = db.query(Opportunity).count()
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712

    status_counts_raw = (
        db.query(Opportunity.status, func.count(Opportunity.id))
        .group_by(Opportunity.status)
        .all()
    )
    status_counts = {status: count for status, count in status_counts_raw}

    completed = sum(
        v for k, v in status_counts.items()
        if k == "complete" or k.endswith("_complete") or k.endswith("_approved")
    )

    return {
        "total_opportunities": total_opps,
        "completed_opportunities": completed,
        "in_progress_opportunities": total_opps - completed,
        "total_users": total_users,
        "active_users": active_users,
        "status_breakdown": status_counts,
    }
