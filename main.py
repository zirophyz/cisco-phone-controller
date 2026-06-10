"""
Entry point for Cisco Phone Controller.

Default mode: pywebview native window with splash screen (single app experience).
Fallback mode (--browser): opens in system browser instead.
Headless mode (--headless): runs server only, no window (for remote/SSH usage).

Usage:
    python main.py              # Native window (default)
    python main.py --browser    # Open in system browser
    python main.py --headless   # Server only, no UI
"""

import os
import sys
import threading
import time

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


def wait_for_server():
    """Block until the FastAPI server responds, up to 10 seconds."""
    import urllib.request
    import urllib.error
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{URL}/", timeout=0.5)
            return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False


def run_webview():
    """Launch pywebview with splash screen, redirect to app when ready."""
    import webview

    def wait_and_redirect(window):
        wait_for_server()
        window.load_url(URL)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    window = webview.create_window(
        title="Cisco Phone Controller",
        html=SPLASH_HTML,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(func=wait_and_redirect, args=(window,))


def run_browser():
    """Start server and open in system browser."""
    import webbrowser

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    if wait_for_server():
        webbrowser.open(URL)
        print(f"Opened {URL} in your browser. Press Ctrl+C to stop.")
    else:
        print("Server failed to start.", file=sys.stderr)
        sys.exit(1)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")


def run_headless():
    """Start server only, no UI. Useful for remote/SSH usage."""
    print(f"Cisco Phone Controller running at {URL}")
    print("Press Ctrl+C to stop.")
    start_server()


def main():
    mode = "webview"
    if "--browser" in sys.argv:
        mode = "browser"
    elif "--headless" in sys.argv:
        mode = "headless"

    if mode == "webview":
        try:
            run_webview()
        except ImportError:
            print("pywebview not available, falling back to browser mode.", file=sys.stderr)
            print("Install pywebview for the single-window experience: pip install pywebview", file=sys.stderr)
            mode = "browser"

    if mode == "browser":
        run_browser()
    elif mode == "headless":
        run_headless()


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