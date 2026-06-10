"""
Entry point for Cisco Phone Controller.
Starts a local FastAPI server and opens a pywebview native window.
No console window, no external browser — single app experience.
"""

import os
import sys
import threading
import time
import webview  # pywebview

# Determine the base path (works both as script and frozen .exe)
# In PyInstaller onefile mode, sys._MEIPASS is where bundled files live
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


def start_server():
    """Run uvicorn in a background thread."""
    import uvicorn
    import app

    # Suppress uvicorn's default log config so our in-memory handler controls output
    uvicorn.run(app.app, host=HOST, port=PORT, log_level="warning")


def main():
    # Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for the server to be ready
    import urllib.request
    import urllib.error
    for _ in range(50):  # up to 5 seconds
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/", timeout=0.5)
            break
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.1)

    # Open pywebview window — single window, no console
    window = webview.create_window(
        title="Cisco Phone Controller",
        url=URL,
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start()

    # When the window closes, the app exits (daemon threads die automatically)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        # Write crash log next to the exe
        try:
            log_path = os.path.join(_EXE_DIR, "crash.log")
            with open(log_path, "w") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise