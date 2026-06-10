"""
Entry point for PyInstaller executable.
Starts the FastAPI server and auto-opens the user's browser.
"""

import os
import sys
import webbrowser
import threading
import time
import uvicorn

# Determine the base path (works both as script and frozen .exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
URL = f"http://{HOST}:{PORT}"

def open_browser(delay=1.5):
    time.sleep(delay)
    webbrowser.open(URL)

def main():
    print(f"Starting Cisco Phone Controller...")
    print(f"URL: {URL}")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host=HOST, port=PORT, log_level="info")

if __name__ == "__main__":
    main()
