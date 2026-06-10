"""
Entry point for PyInstaller executable.
Starts the FastAPI server and auto-opens the user's browser.
"""

import os
import sys
import webbrowser
import threading
import time

# Keep these at top level so PyInstaller discovers them for bundling
import uvicorn  # noqa: F401 — needed for PyInstaller analysis
# Note: we do NOT import app at top level here, because app.py has module-level
# side effects (mounting StaticFiles) that may crash. Instead, we import it
# inside _real_main() where the crash catcher can catch it.
# PyInstaller still bundles app.py because it's in the .spec hiddenimports.

def _crash_catcher():
    """Wrap the entire app startup so crashes keep the console open for reading."""
    try:
        _real_main()
    except Exception:
        import traceback
        print("\n*** FATAL ERROR ***")
        traceback.print_exc()
        # Also write crash log next to the exe
        try:
            if getattr(sys, 'frozen', False):
                log_dir = os.path.dirname(sys.executable)
            else:
                log_dir = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(log_dir, "crash.log")
            with open(log_path, "w") as f:
                traceback.print_exc(file=f)
            print(f"\nCrash log saved to: {log_path}")
        except Exception:
            pass
        input("\nPress Enter to exit...")
        raise


def _real_main():
    import app  # imported here so crash catcher can catch module-level errors

    # Determine the base path (works both as script and frozen .exe)
    # In PyInstaller onefile mode, sys._MEIPASS is where bundled files live
    if getattr(sys, 'frozen', False):
        _INTERNAL_DIR = sys._MEIPASS
    else:
        _INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))

    # Change to internal dir so relative paths work
    os.chdir(_INTERNAL_DIR)

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))
    URL = f"http://{HOST}:{PORT}"

    def open_browser(delay=1.5):
        time.sleep(delay)
        webbrowser.open(URL)

    print(f"Starting Cisco Phone Controller...")
    print(f"URL: {URL}")
    threading.Thread(target=open_browser, daemon=True).start()
    # Pass app object directly so PyInstaller doesn't need to resolve the string at runtime
    uvicorn.run(app.app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    _crash_catcher()