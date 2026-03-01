"""
Push-to-talk diktering

HÖGER SHIFT + HÖGER CTRL = Kopiera till clipboard
AltGr + HÖGER CTRL          = Kopiera + klistra in automatiskt
"""

import sys
import os
import socket
sys.stdout.reconfigure(line_buffering=True)

# Singleton — bara en instans åt gången
_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    _lock_socket.bind(('127.0.0.1', 47832))
except OSError:
    print("Skriv körs redan. Avslutar.")
    sys.exit(0)

import threading
import time
import json
import numpy as np
import sounddevice as sd
import whisper
import pyperclip
from pynput import keyboard
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# Inställningar
WHISPER_MODEL = "small"  # tiny/base/small/medium/large
SAMPLE_RATE = 16000
CHANNELS = 1
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH  = os.path.join(_SCRIPT_DIR, 'config.json')
_DEFAULT_LOGS = os.path.join(_SCRIPT_DIR, 'logs')


def _first_run_setup():
    """Fråga användaren var loggarna ska sparas vid första körning."""
    root = tk.Tk()
    root.withdraw()

    use_custom = messagebox.askyesno(
        "Speech2Clipboard — First run",
        "Do you use Obsidian?\n\n"
        "Click Yes to choose a folder (e.g. your Obsidian daily-logs).\n"
        "Click No to use the default (logs/ next to the script)."
    )

    if use_custom:
        folder = filedialog.askdirectory(title="Select folder for transcription logs")
        log_dir = folder if folder else _DEFAULT_LOGS
    else:
        log_dir = _DEFAULT_LOGS

    root.destroy()

    with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'log_dir': log_dir}, f, indent=2)

    return log_dir


def _load_log_dir():
    # Env-variabel har högst prioritet (personlig override)
    if os.environ.get('SKRIV_LOG_DIR'):
        return os.environ['SKRIV_LOG_DIR']
    # Befintlig config
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f).get('log_dir', _DEFAULT_LOGS)
    # Första körning
    return _first_run_setup()


DAILY_LOG_DIR = _load_log_dir()

# Färger
COLOR_IDLE = "#555555"      # Grå - redo
COLOR_RECORDING = "#ff4444" # Röd - spelar in
COLOR_WORKING = "#ff9900"   # Orange - transkriberar
COLOR_DONE = "#44cc44"      # Grön - klar


class StatusIndicator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("")
        self.root.geometry("14x12+20+20")  # Hälften så stor
        self.root.overrideredirect(True)   # Ingen ram
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#010101')

        # Rundad rektangel (1:1.14 ratio)
        self.canvas = tk.Canvas(self.root, width=14, height=12,
                                bg='#010101', highlightthickness=0)
        self.canvas.pack()
        # Rundad rektangel via polygon med smooth
        self.lamp = self.canvas.create_polygon(
            3, 1,  11, 1,   # Topp
            13, 3, 13, 9,   # Höger
            11, 11, 3, 11,  # Botten
            1, 9,  1, 3,    # Vänster
            smooth=True, fill=COLOR_IDLE, outline=""
        )

        # Drag för att flytta
        self.canvas.bind('<Button-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.drag_data = {"x": 0, "y": 0}

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self.drag_data["x"]
        y = self.root.winfo_y() + event.y - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def set_color(self, color):
        self.root.after(0, lambda: self.canvas.itemconfig(self.lamp, fill=color))

    def idle(self):
        self.set_color(COLOR_IDLE)

    def recording(self):
        self.set_color(COLOR_RECORDING)

    def working(self):
        self.set_color(COLOR_WORKING)

    def done(self):
        self.set_color(COLOR_DONE)
        # Återgå till grå efter 2 sek
        self.root.after(2000, self.idle)

    def update(self):
        self.root.update()


class Skriv:
    def __init__(self, indicator):
        self.indicator = indicator
        self.is_recording = False
        self.audio_frames = []
        self.stream = None
        self.model = None
        self.mode = None
        self.hotkey_pressed = {'shift_r': False, 'ctrl_r': False, 'alt_gr': False}
        self.kb = keyboard.Controller()

        print("Laddar Whisper-modell...")
        indicator.working()
        indicator.update()
        self.model = whisper.load_model(WHISPER_MODEL)
        indicator.idle()
        print(f"Whisper '{WHISPER_MODEL}' laddad!")
        print("\n--- Push-to-talk diktering ---")
        print("HÖGER SHIFT + HÖGER CTRL = Kopiera till clipboard")
        print("AltGr + HÖGER CTRL        = Kopiera + klistra in")
        print("Ctrl+C för att avsluta\n")

    def start_recording(self, mode):
        if self.is_recording:
            return

        self.is_recording = True
        self.mode = mode
        self.audio_frames = []
        self.indicator.recording()

        def audio_callback(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_frames.append(indata.copy())

        input_device = sd.default.device[0]
        if input_device is None or input_device < 0:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    input_device = i
                    break

        self.stream = sd.InputStream(
            device=input_device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.int16,
            callback=audio_callback
        )
        self.stream.start()

        label = "Clipboard + Paste" if mode == "paste" else "Clipboard"
        print(f"● SPELAR IN → {label}...")

    def stop_and_process(self):
        if not self.is_recording:
            return

        self.is_recording = False
        mode = self.mode
        self.indicator.working()

        try:
            self._do_transcribe(mode)
        except Exception as e:
            print(f"Fel: {e}")
            self.indicator.idle()

    def _do_transcribe(self, mode):

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_frames:
            print("Ingen audio inspelad")
            self.indicator.idle()
            return

        print("Transkriberar...")

        audio = np.concatenate(self.audio_frames, axis=0)
        audio_float = audio.astype(np.float32) / 32768.0
        audio_float = audio_float.flatten()

        if len(audio_float) < SAMPLE_RATE * 0.5:
            print("För kort inspelning")
            self.indicator.idle()
            return

        result = self.model.transcribe(
            audio_float,
            language="sv",
            temperature=0,
            best_of=1,
            beam_size=1
        )

        text = result["text"].strip()

        if not text:
            print("Inget tal detekterat")
            self.indicator.idle()
            return

        print(f"Du sa: {text}")
        self.save_transcription(text, mode)

        pyperclip.copy(text)

        if mode == "paste":
            time.sleep(0.15)
            self.kb.press(keyboard.Key.ctrl_l)
            self.kb.tap('v')
            self.kb.release(keyboard.Key.ctrl_l)
            print("Inklistrat i aktivt fönster!")
        else:
            print("Kopierat till clipboard!")

        self.indicator.done()

    def save_transcription(self, text, mode):
        try:
            os.makedirs(DAILY_LOG_DIR, exist_ok=True)
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")
            daily_file = os.path.join(DAILY_LOG_DIR, f"{date_str}.md")

            # Skapa filen med header om den inte finns
            if not os.path.exists(daily_file):
                with open(daily_file, "w", encoding="utf-8") as f:
                    f.write(f"# {date_str} — Daily Log\n")

            # Läs befintligt innehåll
            with open(daily_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Callout-markör (fällbar, hopfälld som default)
            callout_header = "> [!mic]- Dikteringar"

            if callout_header not in content:
                # Lägg till callout-blocket längst ner
                content += f"\n\n{callout_header}\n"

            # Lägg till transkriptionen inuti callout-blocket
            entry = f"> **{time_str}** — {text}\n"
            content += entry

            with open(daily_file, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"Kunde inte spara till daily-log: {e}")

    def on_key_press(self, key):
        try:
            if key == keyboard.Key.shift_r:
                self.hotkey_pressed['shift_r'] = True
            elif key == keyboard.Key.ctrl_r:
                self.hotkey_pressed['ctrl_r'] = True
            elif key == keyboard.Key.alt_gr:
                self.hotkey_pressed['alt_gr'] = True

            # AltGr + RCtrl → paste mode
            if self.hotkey_pressed['alt_gr'] and self.hotkey_pressed['ctrl_r']:
                if not self.is_recording:
                    self.start_recording("paste")
            # RShift + RCtrl → clipboard mode
            elif self.hotkey_pressed['shift_r'] and self.hotkey_pressed['ctrl_r']:
                if not self.is_recording:
                    self.start_recording("clipboard")
        except:
            pass

    def on_key_release(self, key):
        try:
            if key == keyboard.Key.shift_r:
                self.hotkey_pressed['shift_r'] = False
                if self.is_recording and self.mode == "clipboard":
                    threading.Thread(target=self.stop_and_process, daemon=True).start()

            elif key == keyboard.Key.ctrl_r:
                self.hotkey_pressed['ctrl_r'] = False
                if self.is_recording:
                    threading.Thread(target=self.stop_and_process, daemon=True).start()

            elif key == keyboard.Key.alt_gr:
                self.hotkey_pressed['alt_gr'] = False
                if self.is_recording and self.mode == "paste":
                    threading.Thread(target=self.stop_and_process, daemon=True).start()
        except:
            pass

    def run(self):
        listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        listener.start()

        try:
            self.indicator.root.mainloop()
        except KeyboardInterrupt:
            print("\nAvslutar...")
        finally:
            listener.stop()


if __name__ == "__main__":
    # Göm konsollen men behåll tkinter-pricken
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)

    indicator = StatusIndicator()
    app = Skriv(indicator)
    app.run()
