# Cisco Phone Controller — Portable Windows App

A portable desktop replacement for the Firefox/Chrome extension. Runs a local FastAPI server with a clean web UI — no browser extension sandboxing, no Firefox XHR bugs.

## Features

- Landing page: enter phone IP, username, and password
- Live screenshot viewer (auto-refreshes every 6 seconds)
- Clickable phone screen (softkeys, lines, sessions)
- Full keypad (0–9, *, #)
- Command centre: Messages, Nav, Volume, Mute, Speaker, Headset, etc.
- Advanced actions: Make Call, Run Macro, Join/Stop Multicast Audio, Display Text, Buzz

## Architecture

```
[Browser] <--local HTTP--> [FastAPI Backend] <--HTTP Auth--> [Cisco IP Phone]
```

The backend handles all Basic Auth and XML proxying so the frontend never touches credentials directly.

## Quick Start (Development)

```bash
cd cisco-phone-controller-app
pip install -r requirements.txt
python main.py
```

Opens `http://127.0.0.1:8000` automatically.

## Build Portable Windows .exe

### Prerequisites
- Windows 10/11
- Python 3.11+ installed

### Steps
```powershell
cd cisco-phone-controller-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
pyinstaller CiscoPhoneController.spec
```

Output: `dist\CiscoPhoneController.exe` — a single file you can copy anywhere and double-click to run.

## Troubleshooting

**Screenshot works but buttons don't?**
That was the Firefox extension bug. This app doesn't have that problem because the backend makes all authenticated requests directly.

**Phone returns 401?**
- Verify your CUCM user has the phone listed under **Controlled Devices**
- Try accessing `http://<phone-ip>/CGI/Screenshot` in a browser first

## License
MIT — based on the original extension by Anthony Holloway.
