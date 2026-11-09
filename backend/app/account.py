"""Self-service profile and password operations."""

from fastapi import APIRouter, Depends, Request, Response
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy.exc import IntegrityError

from app import models as m
from app.auth import hasher, public_user, session_user, user, verify_csrf
from app.common import audit, change, fail, one
from app.db import database, utcnow
from app.schemas import PasswordChange, ProfileUpdate

router = APIRouter(prefix="/api/v1/account", tags=["Account"])


@router.patch("/me", dependencies=[Depends(verify_csrf)])
def update_profile(body: ProfileUpdate, actor=Depends(user), db=Depends(database)):
    updates = body.model_dump(exclude_unset=True)
    if "email" in updates:
        if updates["email"] is None:
            fail("VALIDATION_FAILED", "Email cannot be empty.")
        updates["email"] = updates["email"].lower()
        existing = one(db, m.users, m.users.c.email == updates["email"])
        if existing and existing["id"] != actor["id"]:
            fail("DUPLICATE_RESOURCE", "That email is already registered.", 409)
    if "phone_number" in updates:
        updates["phone_number"] = updates["phone_number"] or None
    try:
        change(db, m.users, actor["id"], **updates)
        audit(db, actor["id"], "profile_updated", "user", actor["id"])
        return public_user(one(db, m.users, m.users.c.id == actor["id"]))
    except IntegrityError:
        db.rollback()
        fail("DUPLICATE_RESOURCE", "That email is already registered.", 409)


@router.post("/password", status_code=204, dependencies=[Depends(verify_csrf)])
def change_password(body: PasswordChange, request: Request, response: Response,
                    actor=Depends(session_user), db=Depends(database)):
    try:
        valid = hasher.verify(actor["password_hash"], body.current_password)
    except (VerifyMismatchError, InvalidHashError):
        valid = False
    if not valid:
        fail("INVALID_CREDENTIALS", "The current password is incorrect.", 401)
    change(db, m.users, actor["id"], password_hash=hasher.hash(body.new_password),
           must_change_password=False)
    db.execute(m.auth_sessions.update().where(
        m.auth_sessions.c.user_id == actor["id"],
        m.auth_sessions.c.revoked_at.is_(None),
    ).values(revoked_at=utcnow()))
    response.delete_cookie("sdrt_session", path="/")
    audit(db, actor["id"], "password_changed", "user", actor["id"])
