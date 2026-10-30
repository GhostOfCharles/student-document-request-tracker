import uuid
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from app.config import settings, ROOT
from app import auth, services, requests, files, operations

app = FastAPI(title="Student Document Request Tracker — Week 13", version="0.13.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


def error(code, detail, status, fields=None, headers=None):
    return JSONResponse(
        {
            "code": code,
            "detail": detail,
            "field_errors": fields or [],
            "trace_id": uuid.uuid4().hex[:12],
        },
        status_code=status,
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    content = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {
            "code": "RESOURCE_NOT_FOUND"
            if exc.status_code == 404
            else "INVALID_OPERATION",
            "detail": str(exc.detail),
            "field_errors": [],
        }
    )
    content.setdefault("trace_id", uuid.uuid4().hex[:12])
    return JSONResponse(content, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error(
        "VALIDATION_FAILED",
        "Check the highlighted values.",
        422,
        [
            {"field": ".".join(map(str, e["loc"][1:])), "message": e["msg"]}
            for e in exc.errors()
        ],
    )


@app.exception_handler(OperationalError)
async def unavailable(request, exc):
    return error(
        "SERVICE_UNAVAILABLE",
        "The database is temporarily unavailable. Retry shortly.",
        503,
    )


@app.exception_handler(Exception)
async def unexpected(request, exc):
    return error(
        "INTERNAL_ERROR",
        "The operation could not be completed. Reload before retrying.",
        500,
    )


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


for router in (
    auth.router,
    services.router,
    requests.router,
    files.router,
    operations.router,
):
    app.include_router(router)


@app.api_route(
    "/api/{unknown:path}",
    methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    include_in_schema=False,
)
def unknown_api(unknown: str):
    raise HTTPException(404, "API route not found.")


# Same-origin development demonstration: build Flutter first, restart API afterward.
if (ROOT / "build/web").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "build/web", html=True), name="flutter")
