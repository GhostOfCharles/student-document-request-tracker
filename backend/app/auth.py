import base64
import hashlib
import hmac
import secrets
import time
from datetime import timedelta
from collections import defaultdict, deque
from fastapi import APIRouter, Depends, Request, Response
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.db import database, utcnow
from app import models as m
from app.schemas import Login, Register
from app.common import one, add, change, fail, clean, audit

router = APIRouter(prefix="/api/v1/auth", tags=["Sessions"])
hasher = PasswordHasher(type=Type.ID)
dummy_hash = hasher.hash(secrets.token_urlsafe(24))
login_limits = defaultdict(deque)
registration_limits = defaultdict(deque)


def digest(value):
    return hashlib.sha256(value.encode()).digest()


def issue_csrf(response):
    binding = secrets.token_urlsafe(32)
    expires = int(time.time()) + 3600
    msg = f"{binding}.{expires}"
    signature = hmac.new(
        settings.csrf_secret.encode(), msg.encode(), hashlib.sha256
    ).hexdigest()
    response.set_cookie(
        "sdrt_csrf",
        binding,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=3600,
        path="/",
    )
    return {
        "csrf_token": f"{expires}.{signature}",
        "expires_at": clean(utcnow() + timedelta(hours=1)),
    }


def verify_csrf(request: Request):
    if request.headers.get("origin") not in settings.allowed_origins:
        fail("CSRF_FAILED", "The browser origin is not allowed.", 403)
    binding = request.cookies.get("sdrt_csrf", "")
    token = request.headers.get("x-csrf-token", "")
    try:
        expires, signature = token.split(".")
        expected = hmac.new(
            settings.csrf_secret.encode(),
            f"{binding}.{expires}".encode(),
            hashlib.sha256,
        ).hexdigest()
        valid = (
            bool(binding)
            and int(expires) > time.time()
            and hmac.compare_digest(expected, signature)
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        fail("CSRF_FAILED", "Refresh the form security token and retry.", 403)


def session_user(request: Request, db=Depends(database)):
    token = request.cookies.get("sdrt_session")
    session = one(
        db, m.auth_sessions, m.auth_sessions.c.session_token_hash == digest(token or "")
    )
    if not session or session["revoked_at"] or session["expires_at"] <= utcnow():
        fail("AUTHENTICATION_REQUIRED", "Sign in to continue.", 401)
    actor = one(db, m.users, m.users.c.id == session["user_id"])
    if not actor or not actor["is_active"]:
        fail("AUTHENTICATION_REQUIRED", "Sign in to continue.", 401)
    return actor


def user(actor=Depends(session_user)):
    if actor["must_change_password"]:
        fail(
            "PERMISSION_DENIED",
            "Change your temporary password before continuing.",
            403,
        )
    return actor


def staff(actor=Depends(user)):
    if actor["role"] != "staff":
        fail("PERMISSION_DENIED", "Registrar staff access is required.", 403)
    return actor


def student(actor=Depends(user)):
    if actor["role"] != "student":
        fail("PERMISSION_DENIED", "Student access is required.", 403)
    return actor


def public_user(actor):
    return {
        k: actor[k]
        for k in (
            "id",
            "role",
            "full_name",
            "email",
            "phone_number",
            "student_number",
            "staff_number",
            "can_manage_services",
            "must_change_password",
        )
    }


@router.get("/csrf")
def csrf(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return issue_csrf(response)


@router.post("/register", status_code=201, dependencies=[Depends(verify_csrf)])
def register(body: Register, request: Request, db=Depends(database)):
    # Student-number ownership is not yet verified; registration is a local
    # development feature until an institution-approved process exists.
    if settings.environment not in ("development", "test"):
        fail("PERMISSION_DENIED", "Student registration is unavailable.", 403)
    ip = request.client.host if request.client else "local"
    bucket = registration_limits[ip]
    now = time.monotonic()
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= 5:
        from fastapi import HTTPException
        raise HTTPException(429, {"code": "RATE_LIMITED", "detail": "Wait before trying again.",
                                  "field_errors": []}, headers={"Retry-After": "60"})
    bucket.append(now)
    email = body.email.lower()
    if one(db, m.users, or_(m.users.c.email == email, m.users.c.student_number == body.student_number)):
        fail("DUPLICATE_RESOURCE", "That email or student number is already registered.", 409)
    try:
        uid = add(db, m.users, role="student", full_name=body.full_name,
                  student_number=body.student_number, staff_number=None, email=email,
                  phone_number=body.phone_number or None, password_hash=hasher.hash(body.password),
                  can_manage_services=False, is_active=True, must_change_password=False)
        audit(db, uid, "student_registered", "user", uid)
        return public_user(one(db, m.users, m.users.c.id == uid))
    except IntegrityError:
        db.rollback()
        fail("DUPLICATE_RESOURCE", "That email or student number is already registered.", 409)


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(body: Login, request: Request, response: Response, db=Depends(database)):
    ip = request.client.host if request.client else "local"
    bucket = login_limits[ip]
    now = time.monotonic()
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= 10:
        from fastapi import HTTPException

        raise HTTPException(
            429,
            {
                "code": "RATE_LIMITED",
                "detail": "Wait before trying again.",
                "field_errors": [],
            },
            headers={"Retry-After": "60"},
        )
    bucket.append(now)
    actor = one(
        db,
        m.users,
        or_(
            m.users.c.email == body.login.lower(),
            m.users.c.student_number == body.login,
        ),
    )
    try:
        ok = hasher.verify(
            actor["password_hash"] if actor else dummy_hash, body.password
        )
    except (VerifyMismatchError, InvalidHashError):
        ok = False
    if not ok or not actor or not actor["is_active"]:
        audit(db, None, "login_denied", "session", result="denied")
        db.commit()
        fail("INVALID_CREDENTIALS", "The sign-in details are invalid.", 401)
    token = secrets.token_urlsafe(32)
    expiry = utcnow() + (timedelta(days=30) if body.remember_me else timedelta(hours=8))
    add(
        db,
        m.auth_sessions,
        user_id=actor["id"],
        session_token_hash=digest(token),
        remember_me=body.remember_me,
        expires_at=expiry,
    )
    change(db, m.users, actor["id"], last_login_at=utcnow())
    response.set_cookie(
        "sdrt_session",
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=2592000 if body.remember_me else 28800,
    )
    issue_csrf(response)
    audit(db, actor["id"], "login", "session")
    return public_user(actor)


@router.get("/me")
def me(actor=Depends(session_user)):
    return public_user(actor)


@router.post("/logout", status_code=204, dependencies=[Depends(verify_csrf)])
def logout(
    request: Request, response: Response, actor=Depends(session_user), db=Depends(database)
):
    session = one(
        db,
        m.auth_sessions,
        m.auth_sessions.c.session_token_hash == digest(request.cookies["sdrt_session"]),
    )
    change(db, m.auth_sessions, session["id"], revoked_at=utcnow())
    response.delete_cookie("sdrt_session", path="/")
    audit(db, actor["id"], "logout", "session")
