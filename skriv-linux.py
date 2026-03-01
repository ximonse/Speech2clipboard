"""
Speech2Clipboard — Linux version
Push-to-talk dictation with Whisper

RIGHT SHIFT + RIGHT CTRL  = Transcribe → copy to clipboard
RIGHT ALT  + RIGHT CTRL   = Transcribe → copy + auto-paste

NOTE: On Linux, pynput requires access to input devices.
If hotkeys don't work, add yourself to the input group:
  sudo usermod -aG input $USER
Then log out and back in.

pyperclip requires xclip or xsel:
  sudo apt install xclip
"""

import sys
import os
sys.stdout.reconfigure(line_buffering=True)

import threading
import time
import numpy as np
import sounddevice as sd
import whisper
import pyperclip
from pynput import keyboard
from datetime import datetime
import tkinter as tk

# Settings
WHISPER_MODEL = "small"  # tiny/base/small/medium/large
SAMPLE_RATE = 16000
CHANNELS = 1

# Log directory — set SKRIV_LOG_DIR env var to override
DAILY_LOG_DIR = os.environ.get('SKRIV_LOG_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'))

# Status indicator colors
COLOR_IDLE      = "#555555"  # Grey  — ready
COLOR_RECORDING = "#ff4444"  # Red   — recording
COLOR_WORKING   = "#ff9900"  # Orange — transcribing
COLOR_DONE      = "#44cc44"  # Green — done


class StatusIndicator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("")
        self.root.geometry("14x12+20+20")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)

        self.canvas = tk.Canvas(self.root, width=14, height=12,
                                bg='#010101', highlightthickness=0)
        self.canvas.pack()
        self.lamp = self.canvas.create_polygon(
            3, 1,  11, 1,
            13, 3, 13, 9,
            11, 11, 3, 11,
            1, 9,  1, 3,
            smooth=True, fill=COLOR_IDLE, outline=""
        )

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

    def idle(self):      self.set_color(COLOR_IDLE)
    def recording(self): self.set_color(COLOR_RECORDING)
    def working(self):   self.set_color(COLOR_WORKING)

    def done(self):
        self.set_color(COLOR_DONE)
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
        self.hotkey_pressed = {'shift_r': False, 'ctrl_r': False, 'alt_r': False}
        self.kb = keyboard.Controller()

        print("Loading Whisper model...")
        indicator.working()
        indicator.update()
        self.model = whisper.load_model(WHISPER_MODEL)
        indicator.idle()
        print(f"Whisper '{WHISPER_MODEL}' ready!")
        print("\n--- Speech2Clipboard ---")
        print("RIGHT SHIFT + RIGHT CTRL  = Copy to clipboard")
        print("RIGHT ALT  + RIGHT CTRL   = Copy + auto-paste")
        print("Ctrl+C to quit\n")

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
        print(f"● RECORDING → {label}...")

    def stop_and_process(self):
        if not self.is_recording:
            return

        self.is_recording = False
        mode = self.mode
        self.indicator.working()

        try:
            self._do_transcribe(mode)
        except Exception as e:
            print(f"Error: {e}")
            self.indicator.idle()

    def _do_transcribe(self, mode):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_frames:
            print("No audio recorded")
            self.indicator.idle()
            return

        print("Transcribing...")

        audio = np.concatenate(self.audio_frames, axis=0)
        audio_float = audio.astype(np.float32) / 32768.0
        audio_float = audio_float.flatten()

        if len(audio_float) < SAMPLE_RATE * 0.5:
            print("Recording too short")
            self.indicator.idle()
            return

        result = self.model.transcribe(
            audio_float,
            temperature=0,
            best_of=1,
            beam_size=1
        )

        text = result["text"].strip()

        if not text:
            print("No speech detected")
            self.indicator.idle()
            return

        print(f"Transcribed: {text}")
        self.save_transcription(text)

        pyperclip.copy(text)

        if mode == "paste":
            time.sleep(0.15)
            self.kb.press(keyboard.Key.ctrl_l)
            self.kb.tap('v')
            self.kb.release(keyboard.Key.ctrl_l)
            print("Pasted!")
        else:
            print("Copied to clipboard!")

        self.indicator.done()

    def save_transcription(self, text):
        try:
            os.makedirs(DAILY_LOG_DIR, exist_ok=True)
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")
            daily_file = os.path.join(DAILY_LOG_DIR, f"{date_str}.md")

            if not os.path.exists(daily_file):
                with open(daily_file, "w", encoding="utf-8") as f:
                    f.write(f"# {date_str}\n")

            with open(daily_file, "r", encoding="utf-8") as f:
                content = f.read()

            callout_header = "> [!mic]- Dictations"
            if callout_header not in content:
                content += f"\n\n{callout_header}\n"

            content += f"> **{time_str}** — {text}\n"

            with open(daily_file, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"Could not save log: {e}")

    def on_key_press(self, key):
        try:
            if key == keyboard.Key.shift_r:
                self.hotkey_pressed['shift_r'] = True
            elif key == keyboard.Key.ctrl_r:
                self.hotkey_pressed['ctrl_r'] = True
            elif key == keyboard.Key.alt_r:
                self.hotkey_pressed['alt_r'] = True

            # Right Alt + Right Ctrl → paste mode
            if self.hotkey_pressed['alt_r'] and self.hotkey_pressed['ctrl_r']:
                if not self.is_recording:
                    self.start_recording("paste")
            # Right Shift + Right Ctrl → clipboard mode
            elif self.hotkey_pressed['shift_r'] and self.hotkey_pressed['ctrl_r']:
                if not self.is_recording:
                    self.start_recording("clipboard")
        except Exception:
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

            elif key == keyboard.Key.alt_r:
                self.hotkey_pressed['alt_r'] = False
                if self.is_recording and self.mode == "paste":
                    threading.Thread(target=self.stop_and_process, daemon=True).start()
        except Exception:
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
            print("\nQuitting...")
        finally:
            listener.stop()


if __name__ == "__main__":
    indicator = StatusIndicator()
    app = Skriv(indicator)
    app.run()
