#!/usr/bin/env python3
"""
Cisco Phone Controller - Standalone Web App
FastAPI backend that proxies requests to Cisco IP phones.
"""

import os
import sys
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse, JSONResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# In-memory session store (no persistent credentials)
sessions = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    sessions.clear()
    yield
    sessions.clear()

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
    try:
        url = f"http://{ip}/CGI/Screenshot"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, auth=(username, password), timeout=10.0)
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Authentication failed. Check username/password.")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Phone returned status {resp.status_code}")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail=f"Cannot connect to {ip}. Is the phone reachable?")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Connection to phone timed out.")

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
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                auth=(session["username"], session["password"]),
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
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                auth=(session["username"], session["password"]),
                data={"XML": xml},
                timeout=10.0,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
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
    return {"ok": True}

# --- CLI ---

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Cisco Phone Controller on http://{host}:{port}")
    uvicorn.run("app:app", host=host, port=port, reload=False)
