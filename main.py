"""
Entry point for Cisco Phone Controller.
Starts a local FastAPI server and opens a pywebview native window.
Shows a splash screen while the server starts, then loads the app.
No console window, no external browser — single app experience.
"""

import os
import sys
import threading
import time
import webview  # pywebview

# Determine the base path (works both as script and frozen .exe)
if getattr(sys, 'frozen', False):
    _INTERNAL_DIR = sys._MEIPASS
    _EXE_DIR = os.path.dirname(sys.executable)
else:
    _INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))
    _EXE_DIR = _INTERNAL_DIR

os.chdir(_INTERNAL_DIR)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
URL = f"http://{HOST}:{PORT}"

SPLASH_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Cisco Phone Controller</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0078d4;color:#fff;display:flex;flex-direction:column;
align-items:center;justify-content:center;height:100vh;
font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif}
.logo{font-size:2rem;font-weight:700;margin-bottom:24px;letter-spacing:.02em}
.spinner{width:36px;height:36px;border:3px solid rgba(255,255,255,.3);
border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.msg{margin-top:16px;font-size:.9rem;opacity:.85}
</style></head>
<body>
<div class="logo">Cisco Phone Controller</div>
<div class="spinner"></div>
<div class="msg">Starting server...</div>
</body></html>"""


def start_server():
    """Run uvicorn in a background thread."""
    import uvicorn
    import app
    uvicorn.run(app.app, host=HOST, port=PORT, log_level="warning")


def on_window_shown(window):
    """Called when pywebview window is shown. Wait for server then load the app."""
    import urllib.request
    import urllib.error

    for _ in range(100):  # up to 10 seconds
        try:
            urllib.request.urlopen(f"{URL}/", timeout=0.5)
            break
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.1)

    # Server is ready — load the real app
    window.load_url(URL)


def main():
    # Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Open pywebview window with splash screen immediately.
    # Once the window is shown and server is ready, redirect to the app.
    window = webview.create_window(
        title="Cisco Phone Controller",
        html=SPLASH_HTML,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(shown=on_window_shown)

    # When the window closes, daemon threads die automatically


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        try:
            log_path = os.path.join(_EXE_DIR, "crash.log")
            with open(log_path, "w") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise