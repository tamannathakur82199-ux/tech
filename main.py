import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import Base, engine, init_db
from .routers import auth, complaints, admin

init_db()

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Campus Complaints Platform")

# Serve static assets
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# ---- UI routes (pure-Python pages) ----
@app.get("/", include_in_schema=False)
def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/ui/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/ui/register", include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.get("/ui/verify", include_in_schema=False)
def verify_page(request: Request):
    return templates.TemplateResponse(request=request, name="verify.html")

@app.get("/ui/submit", include_in_schema=False)
def submit_page(request: Request):
    return templates.TemplateResponse(request=request, name="submit.html")

@app.get("/ui/suggestion", include_in_schema=False)
def suggestion_page(request: Request):
    return templates.TemplateResponse(request=request, name="suggestion.html")

@app.get("/ui/my", include_in_schema=False)
def my_page(request: Request):
    return templates.TemplateResponse(request=request, name="my.html")

@app.get("/ui/notifications", include_in_schema=False)
def notifications_page(request: Request):
    return templates.TemplateResponse(request=request, name="notifications.html")

@app.get("/ui/admin", include_in_schema=False)
def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/ui/admin-login", include_in_schema=False)
def admin_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin_login.html")



