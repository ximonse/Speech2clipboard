# Speech2Clipboard

Push-to-talk dictation using [OpenAI Whisper](https://github.com/openai/whisper). Hold a hotkey, speak, release — text lands in your clipboard (or gets pasted automatically).

No cloud. No subscription. Runs entirely on your machine.

![Status dot: grey=ready, red=recording, orange=transcribing, green=done]

---

## How it works

A tiny colored dot sits in the corner of your screen:

| Color | State |
|-------|-------|
| ⚫ Grey | Ready |
| 🔴 Red | Recording |
| 🟠 Orange | Transcribing |
| 🟢 Green | Done — text is in clipboard |

Hold the hotkey → speak → release → paste anywhere.

---

## Hotkeys

### Windows (`skriv.py`)
| Keys | Action |
|------|--------|
| **Right Shift + Right Ctrl** | Transcribe → clipboard |
| **AltGr + Right Ctrl** | Transcribe → clipboard + auto-paste |

### Linux (`skriv-linux.py`)
| Keys | Action |
|------|--------|
| **Right Shift + Right Ctrl** | Transcribe → clipboard |
| **Right Alt + Right Ctrl** | Transcribe → clipboard + auto-paste |

---

## Installation

### Requirements
- Python 3.8+
- A microphone
- ~500 MB disk space (Whisper model)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

**Linux only** — also install xclip for clipboard support:
```bash
sudo apt install xclip      # Debian/Ubuntu
sudo pacman -S xclip        # Arch
```

### 2. Run it

**Windows:**
```bash
python skriv.py
```
Or double-click `skriv.vbs` to run silently (no console window).

**Linux:**
```bash
python skriv-linux.py
```

Whisper downloads the model (~140 MB for `small`) on first run.

---

## Linux: hotkey permissions

pynput needs access to input devices. If hotkeys don't respond:

```bash
sudo usermod -aG input $USER
# Log out and back in
```

---

## Configuration

Edit the top of `skriv.py` / `skriv-linux.py`:

```python
WHISPER_MODEL = "small"  # tiny / base / small / medium / large
```

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `tiny` | 40 MB | Fastest | Basic |
| `base` | 75 MB | Fast | OK |
| `small` | 140 MB | Balanced | Good ✓ |
| `medium` | 470 MB | Slow | Better |
| `large` | 1.5 GB | Slowest | Best |

### Save transcriptions to a custom folder

Set the `SKRIV_LOG_DIR` environment variable:

```bash
# Linux / macOS
export SKRIV_LOG_DIR="$HOME/notes/dictations"

# Windows
set SKRIV_LOG_DIR=C:\Users\you\notes\dictations
```

Without this, logs are saved to a `logs/` folder next to the script.

---

## Autostart

### Windows
1. Right-click `skriv.vbs` → Create shortcut
2. Move shortcut to: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`

### Linux (systemd)
```ini
# ~/.config/systemd/user/speech2clipboard.service
[Unit]
Description=Speech2Clipboard

[Service]
ExecStart=python /path/to/skriv-linux.py
Restart=on-failure

[Install]
WantedBy=default.target
```
```bash
systemctl --user enable --now speech2clipboard
```

---

## Troubleshooting

**Hotkeys don't work**
- Windows: make sure you're pressing the *right-side* Shift and Ctrl keys
- Linux: add yourself to the `input` group (see above)

**Wrong language transcribed**
- Whisper auto-detects language. Force a language by setting `language="en"` in the `transcribe()` call

**No audio recorded**
- Check microphone permissions (Windows: Settings → Privacy → Microphone)
- Linux: check `arecord -l` to list available input devices

**Dot disappears off screen**
- Restart the app

---

## License

MIT
