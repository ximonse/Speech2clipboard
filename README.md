# Speech2Clipboard

Push-to-talk dictation using [OpenAI Whisper](https://github.com/openai/whisper). Hold a hotkey, speak, release — text lands in your clipboard (or gets pasted automatically). No cloud. No subscription. Runs entirely on your machine.

A tiny colored dot in the corner of your screen shows what's happening:

| Color | State |
|-------|-------|
| ⚫ Grey | Ready |
| 🔴 Red | Recording |
| 🟠 Orange | Transcribing |
| 🟢 Green | Done — text is in clipboard |

---

## Hotkeys

### Windows
| Keys | Action |
|------|--------|
| **Right Shift + Right Ctrl** | Record → copy to clipboard |
| **AltGr + Right Ctrl** | Record → copy + auto-paste |

### Linux
| Keys | Action |
|------|--------|
| **Right Shift + Right Ctrl** | Record → copy to clipboard |
| **Right Alt + Right Ctrl** | Record → copy + auto-paste |

Hold the keys to record, release to transcribe.

---

## Installation

### Windows

**1. Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**2. Run:**
```bash
python skriv.py
```

Or double-click `skriv.bat` for a visible console window (useful for debugging).

> **Autostart:** Right-click `skriv.bat` → Create shortcut → move it to `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`

---

### Linux

You have two options:

#### Option A — Automatic (recommended)

```bash
git clone https://github.com/ximonse/Speech2clipboard.git
cd Speech2clipboard
bash install.sh
```

The script will:
- Install `python3-tk` and `xclip` via your package manager (apt / pacman / dnf)
- Install Python dependencies
- Add you to the `input` group so global hotkeys work

> **After running the script:** log out and back in once, then start the app.

#### Option B — Manual

```bash
# 1. Install system packages
sudo apt install python3-tk xclip        # Debian/Ubuntu
sudo pacman -S tk xclip                  # Arch
sudo dnf install python3-tkinter xclip  # Fedora

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Add yourself to the input group (required for global hotkeys)
sudo usermod -aG input $USER
# Log out and back in

# 4. Run
python3 skriv-linux.py
```

> **Autostart (systemd):**
> ```ini
> # ~/.config/systemd/user/speech2clipboard.service
> [Unit]
> Description=Speech2Clipboard
>
> [Service]
> ExecStart=python3 /path/to/skriv-linux.py
> Restart=on-failure
>
> [Install]
> WantedBy=default.target
> ```
> ```bash
> systemctl --user enable --now speech2clipboard
> ```

---

## First run

On first launch you'll be asked where to save transcriptions:

- **Yes (Obsidian user)** → pick your Obsidian `daily-notes` or `daily-logs` folder via file dialog
- **No** → transcriptions are saved to a `logs/` folder next to the script

Your choice is saved to `config.json` and remembered from then on.

> To change the folder later, delete `config.json` and restart.

---

## Whisper model

Whisper downloads the model automatically on first run. The default is `small` (~140 MB).

Edit `WHISPER_MODEL` at the top of the script to change it:

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `tiny` | 40 MB | Fastest | Basic |
| `base` | 75 MB | Fast | OK |
| `small` | 140 MB | Balanced | **Good — default** |
| `medium` | 470 MB | Slow | Better |
| `large` | 1.5 GB | Slowest | Best |

---

## Troubleshooting

**Dot doesn't change color / hotkeys don't respond**
- Make sure only one instance is running (the app prevents duplicates automatically)
- Linux: did you log out and back in after `install.sh`?
- Windows: use the *right-side* Shift and Ctrl keys, not left

**Wrong language transcribed**
- Whisper auto-detects language. To force a specific language, find the `transcribe()` call in the script and add `language="en"` (or `"sv"`, `"de"`, etc.)

**"No module named whisper"**
```bash
pip install openai-whisper
```

**Linux: clipboard doesn't work**
```bash
sudo apt install xclip
```

**Dot disappears off screen**
- Restart the app — the dot resets to the top-left corner

---

## License

MIT
