import hashlib
import re
import secrets
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, or_
from app import models as m
from app.config import settings
from app.auth import user, student, verify_csrf
from app.db import database, utcnow
from app.common import one, add, change, audit, fail, clean

router = APIRouter(prefix="/api/v1/files", tags=["Private evidence"])
MIMES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


@router.post("/staging", status_code=201, dependencies=[Depends(verify_csrf)])
def upload(file: UploadFile = File(...), actor=Depends(student), db=Depends(database)):
    name = re.sub(
        r"[^A-Za-z0-9._ -]", "_", Path((file.filename or "").replace("\\", "/")).name
    )[:128]
    extension = Path(name).suffix.lower()
    mime = MIMES.get(extension)
    if not mime or file.content_type != mime:
        fail(
            "UNSUPPORTED_FILE_TYPE",
            "Use PDF, JPEG or PNG with a matching file type.",
            415,
        )
    settings.private_dir.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    target = settings.private_dir / key
    size = 0
    checksum = hashlib.sha256()
    first = b""
    try:
        with target.open("xb") as out:
            while chunk := file.file.read(65536):
                if not first:
                    first = chunk[:16]
                size += len(chunk)
                if size > 5242880:
                    fail("FILE_TOO_LARGE", "Maximum file size is 5 MiB.", 413)
                checksum.update(chunk)
                out.write(chunk)
        if not size:
            fail("VALIDATION_FAILED", "Empty evidence is not accepted.")
        valid_signature = (
            (mime == "application/pdf" and first.startswith(b"%PDF-"))
            or (mime == "image/png" and first.startswith(b"\x89PNG\r\n\x1a\n"))
            or (mime == "image/jpeg" and first.startswith(b"\xff\xd8\xff"))
        )
        if not valid_signature:
            fail(
                "UNSUPPORTED_FILE_TYPE",
                "The file signature does not match its declared format.",
                415,
            )
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.file_validation", str(target), mime],
                timeout=8,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode:
                fail(
                    "VALIDATION_FAILED",
                    "Evidence is corrupt, encrypted, or exceeds the parser limits.",
                )
        except subprocess.TimeoutExpired:
            fail("VALIDATION_FAILED", "Evidence inspection exceeded its time limit.")
        fid = add(
            db,
            m.stored_files,
            uploaded_by_user_id=actor["id"],
            original_filename=name,
            storage_key=key,
            mime_type=mime,
            size_bytes=size,
            sha256_hex=checksum.hexdigest(),
            storage_status="staging",
            staging_expires_at=utcnow() + timedelta(hours=24),
            verified_at=utcnow(),
        )
        audit(
            db,
            actor["id"],
            "file_staged",
            "file",
            fid,
            details={"mime_type": mime, "size_bytes": size},
        )
        db.commit()
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()
    record = one(db, m.stored_files, m.stored_files.c.id == fid)
    return clean(
        {
            k: record[k]
            for k in (
                "id",
                "original_filename",
                "mime_type",
                "size_bytes",
                "storage_status",
                "staging_expires_at",
            )
        }
    )


def referenced(db, file_id):
    return bool(
        db.scalar(
            select(m.request_attachments.c.id)
            .where(m.request_attachments.c.stored_file_id == file_id)
            .limit(1)
        )
        or db.scalar(
            select(m.request_revisions.c.id)
            .where(m.request_revisions.c.payment_receipt_file_id == file_id)
            .limit(1)
        )
    )


@router.get("/{file_id}")
def download(
    file_id: int,
    disposition: str = Query("attachment", pattern="^(inline|attachment)$"),
    actor=Depends(user),
    db=Depends(database),
):
    record = one(db, m.stored_files, m.stored_files.c.id == file_id)
    if (
        not record
        or record["storage_status"] == "removed"
        or (actor["role"] == "student" and record["uploaded_by_user_id"] != actor["id"])
        or (actor["role"] == "staff" and not referenced(db, file_id))
    ):
        fail("RESOURCE_NOT_FOUND", "Evidence not found.", 404)
    target = settings.private_dir / record["storage_key"]
    if not target.is_file():
        fail("RESOURCE_NOT_FOUND", "Evidence unavailable; contact staff.", 404)
    return FileResponse(
        target,
        media_type=record["mime_type"],
        filename=record["original_filename"],
        content_disposition_type=disposition,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )


@router.delete(
    "/staging/{file_id}", status_code=204, dependencies=[Depends(verify_csrf)]
)
def remove(file_id: int, actor=Depends(student), db=Depends(database)):
    record = one(db, m.stored_files, m.stored_files.c.id == file_id, lock=True)
    if not record or record["uploaded_by_user_id"] != actor["id"]:
        fail("RESOURCE_NOT_FOUND", "Evidence not found.", 404)
    if referenced(db, file_id) or record["storage_status"] == "ready":
        fail("FILE_ALREADY_ATTACHED", "Historical evidence must be preserved.", 409)
    change(db, m.stored_files, file_id, storage_status="removed")
    db.commit()  # A crash after this point is reconciled by scheduled cleanup.
    (settings.private_dir / record["storage_key"]).unlink(missing_ok=True)
    return Response(status_code=204)
