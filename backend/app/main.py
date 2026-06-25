import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import data_quality, groups, matches, model_diagnostics, players, predictions, teams, tournament
from app.database import Base, SessionLocal, engine
from app.models.team import Team

Base.metadata.create_all(bind=engine)

# On an ephemeral filesystem (e.g. Render's free tier resets local disk on
# every deploy/restart), the SQLite file may come up empty even though the
# repo's seed JSON has real data. Auto-reseed once on startup if so, instead
# of requiring a manual SSH step after every deploy.
#
# A non-empty table is not reliable proof the seed data is current, though:
# in practice this file has been observed to outlive a deploy even without a
# Render Persistent Disk attached. Team/Player are pure reference data the
# app never mutates at runtime (see sync_reference_data()'s docstring), so
# it's always safe -- and necessary -- to resync them in place every startup
# rather than only when the table happens to be empty.
with SessionLocal() as _db:
    if _db.scalar(select(Team).limit(1)) is None:
        from scripts.seed_db import main as _seed_db

        _seed_db()
    else:
        from scripts.seed_db import sync_reference_data as _sync_reference_data

        _sync_reference_data(_db)

app = FastAPI(title="WC2026 Sim API")

_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
allowed_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Only the methods/headers this API actually uses -- narrower than "*"
    # so a misconfigured ALLOWED_ORIGINS doesn't also hand out an open-ended
    # cross-origin surface for verbs/headers nothing here needs.
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response


app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(groups.router)
app.include_router(tournament.router)
app.include_router(predictions.router)
app.include_router(data_quality.router)
app.include_router(model_diagnostics.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
