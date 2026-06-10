# Cisco Phone Controller — Standalone Web App

A portable desktop app for controlling Cisco IP phones, rebuilt as a standalone web application to work around breakage in modern Firefox versions.

The original [Cisco Phone Controller](https://github.com/avholloway/cisco-phone-controller) by Anthony Holloway is a browser extension (Chrome + Firefox) that injects a remote control UI onto Cisco IP phone web pages. It hasn't been updated in years and broke on newer Firefox releases — XHR requests from the content script silently fail, so screenshots load but button presses do nothing. This standalone app sidesteps browser extension sandboxing and CORS issues entirely by running a local FastAPI backend that proxies all requests directly to the phone.

## Features

- **Single-window desktop app** — launches as a native window, no browser needed
- Splash screen while the server starts up
- Landing page: enter phone IP, username, and password
- Live screenshot viewer (auto-refreshes every 6 seconds)
- Clickable phone screen (softkeys, lines, sessions)
- Full keypad (0–9, *, #) and D-pad navigation (⇧⇩⇦⇨ Select Back Vol)
- Function keys: Messages, Directories, Applications, Settings, Speaker, Headset, Mute
- Advanced actions: Make Call, Run Macro, Join/Stop Multicast Audio, Display Text
- In-app log viewer (View Logs in menu bar) — logs are in-memory only, purged on exit
- **No persistent credentials** — everything stays in memory until you disconnect or close the app
- Automatically bypasses corporate HTTP proxies so direct phone access works on managed networks

## Architecture

```
[pywebview Window] <--local HTTP--> [FastAPI Backend] <--HTTP Auth--> [Cisco IP Phone]
```

The backend handles all Basic Auth and XML proxying so the frontend never touches credentials directly.

## Running from Source

### Windows / macOS / Linux (with desktop)

Requires [pywebview](https://pywebview.flowrl.com/) for the single-window experience. On Linux you also need `python3-webkit2` or equivalent GTK webkit bindings.

```bash
git clone https://github.com/rn-bord/cisco-phone-controller.git
cd cisco-phone-controller
pip install -r requirements.txt
python main.py
```

This opens a native window with the app. If `pywebview` is not installed, it falls back to your system browser.

### Browser mode

Opens the app in your default browser instead of a native window:

```bash
python main.py --browser
```

### Headless / remote (SSH, servers)

Runs the server only — no window, no browser. Access from another machine at `http://<your-ip>:8000`:

```bash
python main.py --headless
```

You can also set `HOST=0.0.0.0` to listen on all interfaces:

```bash
HOST=0.0.0.0 python main.py --headless
```

## Windows EXE

Download the latest `.exe` from [Releases](https://github.com/rn-bord/cisco-phone-controller/releases) — no Python install needed. Just double-click and go.

## CUCM Setup

This app requires a CUCM (Cisco Unified Communications Manager) user with permission to control the target phone. Here's how to set that up:

### 1. Create an Application User

1. Log into **CUCM Administration** → **User Management** → **Application User**
2. Click **Add New**
3. Enter a **User ID** and **Password** (e.g. `remote` / your chosen password)
4. Under **Device Information**, add the target phone(s) to the **Controlled Devices** list
5. Click **Save**

### 2. Verify Phone Web Access

1. Open a browser and navigate to `http://<phone-ip>/Device_Information.html`
2. You should be prompted for credentials — enter the application user you just created
3. If you can see the Device Information page, the app will work

### 3. Allow Phone Web Server

If the phone doesn't respond on HTTP at all:

1. In CUCM, go to **Device** → **Phone** and select the phone
2. Scroll to **Web Access** and ensure it is **Enabled**
3. Save and reset the phone for the change to take effect

### Troubleshooting

- **401 Unauthorized** — Wrong username/password, or the user doesn't exist
- **403 Forbidden** — User exists but the phone is not listed under that user's **Controlled Devices** in CUCM
- **Connection refused / timeout** — Phone web server is disabled, or the phone is unreachable from your machine. Check that **Web Access** is enabled on the phone and that your network allows HTTP to the phone's IP

## Credit

Based on the original [Cisco Phone Controller](https://github.com/avholloway/cisco-phone-controller) browser extension by Anthony Holloway.

---

*This project was written by an AI assistant. There may be bugs, security issues, or unexpected behaviour. You should manually review the code before running it on your machine or network.*