# web-telly

**A free, open-source local-network Tally light system for video switchers.**

Turn any phone, tablet, or computer into a real-time tally indicator — no extra hardware needed. Camera operators open a web page, select their position, and see red (PGM) or green (PVW) fullscreen when the director switches to them.

> © Weifang Industrial and Commercial Media Center (潍坊工商融媒体中心)

---

## How It Works

```
┌──────────────┐    TCP :19010     ┌──────────────┐   WebSocket    ┌─────────────┐
│   Switcher   │ ────────────────→ │  web-telly   │ ─────────────→ │  Phone/iPad  │
│  OSEE / BMD  │   JSON protocol   │  (your PC)   │   real-time    │  (browser)   │
└──────────────┘                   └──────────────┘                └─────────────┘
                                         │
                                    Web GUI + EXE
                                  one-click startup
```

1. **Run web-telly** on a Windows PC connected to the same LAN as the switcher.
2. **Enter the switcher IP** (e.g. `192.168.3.208`) and click Connect.
3. **Open the generated URL** on any phone/tablet to select a camera position.
4. The screen turns **Red** when live (PGM), **Green** when preview (PVW), **Grey** when idle.

---

## Screenshots

### Desktop — Director Monitor View
Shows all 8 channels (4 camera positions + Still1/Still2/AUX/S-SRC) with real-time color updates. Force-release occupied camera positions.

### Phone — Camera Selection
4 camera buttons + Director button. One person per camera (exclusive lock).

### Phone — Tally Fullscreen
Grey idle → Green PVW → Red PGM. Large white number in center. Transition detection: both PGM and PVW show red during AUTO transition.

---

## Features

| Feature | Description |
|---------|-------------|
| **Zero Hardware** | Phones/tablets become tally lights via web browser |
| **Plug & Play EXE** | Single `web-telly.exe` — no Python installation needed |
| **Auto IP Detection** | Automatically finds the correct LAN IP matching the switcher subnet |
| **Port Auto-Selection** | If port 7210 is occupied, tries 7211, 7212... |
| **Exclusive Locking** | One camera operator per camera position (1-4) |
| **Director Monitor** | Desktop view shows all channels with real-time colors |
| **Force Release** | Director can kick occupied camera positions |
| **AUTO Transition** | Both PGM and PVW turn red during transition |
| **Wake Lock** | Phone screen won't sleep while displaying tally |
| **Keep-Alive Polling** | 200ms polling prevents display freeze |
| **Config Persistence** | Switcher IP/port saved to `config.txt` |

---

## Quick Start

### Option 1: Portable EXE (Recommended)

1. Download `web-telly.exe` from [Releases](../../releases).
2. Double-click to run.
3. Enter your switcher's IP address and port.
4. Click **Connect**.
5. Open the displayed URLs on your devices.

### Option 2: Run from Source

```bash
# Requirements: Python 3.10+
pip install flask flask-socketio

# Run the GUI version
python gui_server.py

# Or run the CLI version
python tally_server.py
```

---

## Usage

### For the Director (Desktop)

- Open the **Computer URL** (e.g. `http://192.168.3.96:7210/director`)
- A 2×4 grid shows all camera positions and special channels
- Red = PGM (live), Green = PVW (preview), Grey = idle
- Click **Release** buttons to forcibly free an occupied camera position

### For Camera Operators (Phone/Tablet)

- Open the **Mobile URL** (e.g. `http://192.168.3.96:7210`)
- Tap a camera button (1-4) — or tap **Director** to see all channels
- The screen goes fullscreen:
  - **Grey** background with white number = standby
  - **Red** background = your camera is LIVE (PGM)
  - **Green** background = your camera is PREVIEW (PVW)
  - During AUTO transition: both PGM and PVW positions show red

---

## Supported Switchers

| Brand | Protocol | Port | Status |
|-------|----------|------|--------|
| **OSEE GoStream** | TCP JSON | 19010 | ✅ Full support |
| **BMD ATEM** | TCP JSON (compatible) | 19010 | ✅ Supported |
| Others with compatible protocol | TCP JSON | configurable | ✅ Should work |

The switcher protocol uses JSON messages like:
```json
{"id": "pgmIndex", "type": "set", "value": [1]}
{"id": "pvwIndex", "type": "set", "value": [2]}
{"id": "transitionStatus", "type": "pus", "value": [1]}
```

---

## Project Structure

```
tally-web/
├── gui_server.py           # Main GUI application (tkinter)
├── tally_server.py         # CLI version
├── start.bat               # Windows launcher
├── app.ico                 # Application icon
├── config.txt              # Saved configuration (auto-generated)
│
├── core/
│   ├── network_utils.py    # IP detection, port scanning, connection test
│   └── switcher_client.py  # TCP client for switcher protocol
│
├── web/
│   ├── app.py              # Flask app, SocketIO, state management
│   ├── routes.py           # HTTP routes (/, /director, /tally/<id>, /api/state)
│   └── socket_events.py    # WebSocket event handlers
│
├── templates/
│   ├── index.html          # Phone: camera position selection page
│   ├── director.html       # Desktop: multi-channel monitor page
│   └── tally.html          # Phone/Desktop: fullscreen tally display
│
└── static/
    └── style.css            # All styles
```

---

## Build EXE

```bash
pip install pyinstaller

pyinstaller --onefile --windowed \
  --name "web-telly" \
  --icon "app.ico" \
  --add-data "templates;templates" \
  --add-data "static;static" \
  --add-data "core;core" \
  --add-data "web;web" \
  --hidden-import engineio.async_drivers.threading \
  --collect-all engineio \
  --collect-all socketio \
  gui_server.py
```

The EXE will be in `dist/web-telly.exe`.

---

## FAQ

**Q: The phone can't open the web page?**
A: Make sure the phone is on the same WiFi/LAN as the PC running web-telly. Check that no firewall is blocking port 7210.

**Q: The tally colors don't update?**
A: Verify the switcher IP and port are correct. The connection status indicator should show green.

**Q: The auto-detected IP is wrong?**
A: The program picks the IP matching the switcher's subnet. If your PC has multiple network adapters, ensure the correct one is active.

**Q: A camera position shows "Occupied" but nobody is using it?**
A: Use the Director view to force-release the position with the **Release** button.

---

## Credits

- **Author**: Weifang Industrial and Commercial Media Center (潍坊工商融媒体中心 灵感)
- **Inspired by**: [OmniTally](https://github.com/OmniDamon/OmniTally) by OmniDamon
- **Built with**: Flask, Flask-SocketIO, tkinter, PyInstaller

---

## License

This project is free and open-source. Use it, modify it, share it.
