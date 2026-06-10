#!/usr/bin/env python3
"""
Cisco Phone Controller - Standalone Web App
FastAPI backend that proxies requests to Cisco IP phones.
"""

import os
import sys
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse, JSONResponse

# Determine base path (works both as script and frozen .exe)
# In PyInstaller onefile mode, bundled files live in sys._MEIPASS (temp extraction dir)
# The exe itself lives at sys.executable, but static/ etc are in _MEIPASS
if getattr(sys, 'frozen', False):
    _INTERNAL_DIR = sys._MEIPASS          # where PyInstaller extracted bundled files
    _EXE_DIR = os.path.dirname(sys.executable)  # where the .exe sits (for logs)
else:
    _INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = _INTERNAL_DIR

STATIC_DIR = os.path.join(_INTERNAL_DIR, "static")
LOG_FILE = os.path.join(_EXE_DIR, "cisco-phone-controller.log")

# Set up file logging so we can debug issues after the console closes
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("cisco-controller")

# In-memory session store (no persistent credentials)
sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    sessions.clear()
    logger.info("App started, sessions cleared")
    yield
    sessions.clear()
    logger.info("App shutting down, sessions cleared")

app = FastAPI(title="Cisco Phone Controller", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=STATIC_DIR)

# --- Helpers ---

def get_session(request: Request) -> dict:
    client = request.client.host if request.client else "unknown"
    return sessions.get(client, {})

def set_session(request: Request, data: dict):
    client = request.client.host if request.client else "unknown"
    sessions[client] = data

# Browser-like headers so the phone doesn't reject us
PHONE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}

# --- Routes ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/connect")
async def connect(
    request: Request,
    ip: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    """Test connectivity and store session credentials in memory."""
    logger.info(f"Connect attempt to {ip} with user {username}")

    url = f"http://{ip}/CGI/Screenshot"
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            logger.debug(f"GET {url}")
            resp = await client.get(
                url,
                auth=(username, password),
                headers=PHONE_HEADERS,
                timeout=10.0,
            )
            logger.debug(f"Response status: {resp.status_code}")
            logger.debug(f"Response headers: {dict(resp.headers)}")
            # Log a snippet of the body for diagnostics
            body_preview = resp.text[:500] if resp.text else "<empty>"
            logger.debug(f"Response body preview: {body_preview}")

        if resp.status_code == 401:
            logger.warning("Phone returned 401 Unauthorized")
            raise HTTPException(status_code=401, detail="Authentication failed. Check username/password.")
        if resp.status_code == 403:
            logger.warning("Phone returned 403 Forbidden")
            # 403 on Cisco phones usually means the user is valid but not authorized
            # to control this phone (missing Controlled Devices association in CUCM)
            raise HTTPException(
                status_code=403,
                detail=(
                    "Phone returned 403 Forbidden.\n\n"
                    "This usually means your CUCM user credentials are correct, "
                    "but this user is not associated with this phone under "
                    "'Controlled Devices' in CUCM.\n\n"
                    "Alternatively, the phone may require HTTPS or a specific authentication method.\n"
                    "Check the log file for details."
                ),
            )
        if resp.status_code != 200:
            logger.warning(f"Phone returned unexpected status {resp.status_code}")
            raise HTTPException(status_code=502, detail=f"Phone returned status {resp.status_code}")
    except httpx.ConnectError as e:
        logger.error(f"ConnectError: {e}")
        raise HTTPException(status_code=502, detail=f"Cannot connect to {ip}. Is the phone reachable?")
    except httpx.TimeoutException:
        logger.error("Timeout connecting to phone")
        raise HTTPException(status_code=504, detail="Connection to phone timed out.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during connect")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    logger.info(f"Connection to {ip} successful")
    set_session(request, {
        "ip": ip,
        "username": username,
        "password": password,
    })
    return {"ok": True}

@app.get("/api/screenshot")
async def screenshot(request: Request):
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=400, detail="Not connected. Connect first.")

    url = f"http://{session['ip']}/CGI/Screenshot"
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                url,
                auth=(session["username"], session["password"]),
                headers=PHONE_HEADERS,
                timeout=10.0,
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication failed.")
        media_type = resp.headers.get("content-type", "image/jpeg")
        return StreamingResponse(resp.iter_raw(), media_type=media_type)
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot connect to phone.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Phone screenshot timed out.")

@app.post("/api/execute")
async def execute(
    request: Request,
    xml: str = Form(...),
):
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=400, detail="Not connected. Connect first.")

    url = f"http://{session['ip']}/CGI/Execute"
    logger.debug(f"Execute POST to {url} with XML: {xml[:200]}...")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.post(
                url,
                auth=(session["username"], session["password"]),
                data={"XML": xml},
                timeout=10.0,
                headers={
                    **PHONE_HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        logger.debug(f"Execute response: {resp.status_code}")
        return JSONResponse(content={
            "status": resp.status_code,
            "body": resp.text,
        })
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot connect to phone.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Phone command timed out.")

@app.post("/api/disconnect")
async def disconnect(request: Request):
    client = request.client.host if request.client else "unknown"
    sessions.pop(client, None)
    logger.info(f"Session cleared for {client}")
    return {"ok": True}

# --- CLI ---

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Cisco Phone Controller on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)
