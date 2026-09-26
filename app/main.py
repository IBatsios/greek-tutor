import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import auth, config, db, harada_api, llm, quota, tutor
from .auth import current_user, require_user

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    llm.backend()  # fail fast: missing API key, or claude binary not on PATH
    async with db.pool().acquire() as conn:
        await llm.assert_single_learner(conn)  # claude_cli: refuse to serve >1 account
    log.info("LLM backend: %s", config.LLM_BACKEND)
    yield
    await db.close_pool()


app = FastAPI(title="Greek Tutor", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(tutor.router)
app.include_router(harada_api.router)
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Liveness + DB reachability, for the Docker HEALTHCHECK."""
    await db.pool().fetchval("SELECT 1")
    return {"ok": True}


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    used = await quota.minutes_used_today(user["id"])
    return templates.TemplateResponse(request, "dashboard.html",
                                      {"user": dict(user), "minutes_used": round(used)})


@app.get("/practice", response_class=HTMLResponse)
async def practice(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse(request, "session.html", {"user": dict(user)})
