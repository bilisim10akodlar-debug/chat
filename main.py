import os
import base64
import io
import json
import math
import re
import socket
import threading
import time
import uuid
import subprocess
import sys
import zlib
import ctypes
import random
import struct
import datetime
from collections import defaultdict, deque
from dataclasses import dataclass, field

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk

# PIL kurulum kontrolü
try:
    from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True

# Ses kütüphanesi kontrolü
try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sounddevice", "numpy"])
        import sounddevice as sd
        import numpy as np
        AUDIO_AVAILABLE = True
    except Exception:
        AUDIO_AVAILABLE = False

# ===================== SABITLER =====================
APP_TITLE              = "OPSI Pro"
APP_VERSION            = "11.0"
PORT                   = 45127
BROADCAST_ADDR         = "255.255.255.255"
UI_REFRESH_MS          = 100
HEARTBEAT_SEC          = 3
STALE_USER_SEC         = 14
STALE_ROOM_SEC         = 24
MAX_HISTORY            = 200
MAX_IMAGE_SIDE         = 480
MAX_IMAGE_B64_LEN      = 60000
SOCK_TIMEOUT           = 0.20
AUDIO_SR               = 8000
AUDIO_MIN_SEC          = 0.2
MAX_AUDIO_B64_LEN      = 180000
MAX_PACKET_BYTES       = 60000
SCREEN_SHARE_INTERVAL  = 0.0166
SCREEN_SHARE_MAX_SIDE  = 1920
SCREEN_SHARE_JPEG_Q    = 78
SCREEN_SHARE_MAX_B64   = 400000
SCREEN_SHARE_CHUNK     = 45000
SCREEN_BUFFER_TTL      = 6.0
MAX_FILE_BYTES         = 400_000
FILE_CHUNK_SIZE        = 40_000
MAX_MSG_LEN            = 2000
TOAST_DURATION_MS      = 4000

CONFIG_DOSYASI = "opsi_config.json"

# ===================== XOR OBFUSCATION =====================
_XOR_KEY = b"OPS1v9#Gh0stKey!2025"

def _xor_obfuscate(data: bytes) -> bytes:
    key  = _XOR_KEY
    klen = len(key)
    return bytes(b ^ key[i % klen] for i, b in enumerate(data))

def _encode_packet(packet: dict) -> bytes:
    raw = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    obf = _xor_obfuscate(raw)
    return base64.b64encode(obf)

def _decode_packet(data: bytes) -> dict:
    try:
        decoded = base64.b64decode(data)
        plain   = _xor_obfuscate(decoded)
        return json.loads(plain.decode("utf-8"))
    except Exception:
        pass
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        raise ValueError("Paket çözülemedi")

# ===================== RENK PALETİ (Premium Dark) =====================
BG        = "#0f1117"
PANEL     = "#161b22"
PANEL_2   = "#1c2128"
PANEL_3   = "#0d1117"
INPUT     = "#1c2128"
INPUT_H   = "#252c37"
HOVER     = "#1f2937"
BORDER    = "#21262d"
BORDER_2  = "#30363d"
TEXT      = "#e6edf3"
TEXT_2    = "#c9d1d9"
MUTED     = "#7d8590"
MUTED_2   = "#6e7681"
ACCENT    = "#388bfd"
ACCENT_H  = "#4d9fff"
ACCENT_2  = "#3fb950"
ACCENT_S  = "#1f6feb"
SUCCESS   = "#3fb950"
WARN      = "#d29922"
DANGER    = "#f85149"
GOLD      = "#d29922"
PINK      = "#bc8cff"
TEAL      = "#39c5cf"
USER_BG   = "#0d1117"
MENTION   = "#1a2940"
GLASS     = "#ffffff08"
GLASS_H   = "#ffffff12"
SHADOW    = "#00000066"
REPLY_BG  = "#161b22"

AVATAR_PALETTE = [
    "#388bfd","#3fb950","#d29922","#f85149",
    "#bc8cff","#39c5cf","#ff7b72","#56d364",
    "#e3b341","#79c0ff","#ffa198","#56d364",
]

EMOJI_LIST = [
    "😀","😂","😍","😭","😤","🥺","😎","🤔","👍","👎",
    "❤️","🔥","✨","💯","🎉","👀","🙏","😴","🤣","😱",
    "🥳","🤙","💪","🫡","💀","😅","🤦","🫶","👋","🤷",
    "🎮","💻","📱","🌙","⚡","🎯","🏆","💡","🚀","🔮",
    "🌟","🎵","🎪","🦋","🌈","🍕","☕","🧠","🔑","💎",
    "🌊","🎭","🦊","🐉","⚔️","🛡️","🎲","🧪","🌺","🦅",
]

QUICK_REACTIONS = ["👍","👎","❤️","😂","😮","😢","🔥","🎉","💯","🤔"]

STATUS_ICONS  = {"online": "●", "away": "◐", "dnd": "⊘", "offline": "○"}
STATUS_COLORS = {"online": SUCCESS, "away": WARN, "dnd": DANGER, "offline": MUTED}
STATUS_LABELS = {"online": "Çevrimiçi", "away": "Uzakta", "dnd": "Rahatsız Etme", "offline": "Görünmez"}

FILE_ICONS = {
    "pdf": "📄", "zip": "🗜️", "rar": "🗜️", "7z": "🗜️",
    "py":  "🐍", "txt": "📝", "md":  "📝", "json": "📋",
    "csv": "📊", "xlsx": "📊", "xls": "📊", "html": "🌐",
    "xml": "🌐", "docx": "📘", "doc": "📘", "pptx": "📙",
    "mp3": "🎵", "wav":  "🎵", "mp4": "🎬", "avi":  "🎬",
    "png": "🖼️", "jpg":  "🖼️", "gif": "🖼️", "svg":  "🖼️",
    "exe": "⚙️", "bat":  "⚙️", "sh":  "⚙️", "iso":  "💿",
}

THEMES = {
    "Mavi (Varsayılan)": "#388bfd",
    "Yeşil":             "#3fb950",
    "Mor":               "#bc8cff",
    "Kırmızı":           "#f85149",
    "Altın":             "#d29922",
    "Teal":              "#39c5cf",
    "Pembe":             "#ff7b72",
    "Turuncu":           "#f0883e",
}

# ===================== VERİ SINIFI =====================
@dataclass
class ChatItem:
    item_id    : str
    kind       : str
    sender     : str
    ts         : float
    room       : str
    text       : str  = ""
    image_b64  : str  = ""
    image_name : str  = ""
    audio_b64  : str  = ""
    audio_name : str  = ""
    audio_sr   : int  = AUDIO_SR
    audio_codec: str  = ""
    audio_sec  : float= 0.0
    file_b64   : str  = ""
    file_name  : str  = ""
    file_size  : int  = 0
    ref_id     : str  = ""
    reactions  : dict = field(default_factory=dict)
    pinned     : bool = False
    edited     : bool = False
    reply_to   : str  = ""   # item_id of the message being replied to
    reply_sender: str = ""   # sender of the replied message
    reply_text : str  = ""   # text snippet of replied message

# ===================== UTIL =====================
def _make_rounded_rect_image(w, h, r, color, alpha=255):
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r    = min(r, w // 2, h // 2)
    cr   = int(color.lstrip("#"), 16)
    rgb  = ((cr >> 16) & 255, (cr >> 8) & 255, cr & 255, alpha)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=rgb)
    return img

def _fmt_filesize(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    elif n_bytes < 1024 * 1024:
        return f"{n_bytes/1024:.1f} KB"
    else:
        return f"{n_bytes/1024/1024:.1f} MB"

def _detect_lang(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return {"py":"Python","js":"JavaScript","ts":"TypeScript","html":"HTML",
            "css":"CSS","json":"JSON","xml":"XML","sql":"SQL","sh":"Shell",
            "md":"Markdown","txt":"Metin","csv":"CSV"}.get(ext, ext.upper())

# ===================== ANA UYGULAMA =====================
class OPSIPro:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1340x840")
        self.root.minsize(1000, 620)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._app_exit)
        self.root.bind("<Alt-F4>", self._app_exit)

        try:
            self.root.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        # Config
        self.cfg             = self._load_config()
        saved_name           = self.cfg.get("username") or f"kullanici_{uuid.uuid4().hex[:4]}"
        self.sound_enabled   = self.cfg.get("sound_enabled", True)
        self.theme_accent    = self.cfg.get("theme_accent", ACCENT)
        self.user_status     = self.cfg.get("user_status", "online")
        self.compact_mode    = self.cfg.get("compact_mode", False)
        self.show_timestamps = self.cfg.get("show_timestamps", True)
        self.notify_mentions_only = self.cfg.get("notify_mentions_only", False)
        self.font_size       = self.cfg.get("font_size", 11)
        self.message_preview = self.cfg.get("message_preview", True)

        self.username_var    = tk.StringVar(value=saved_name)
        self.avatar_b64_map  = {}
        if self.cfg.get("avatar_b64"):
            self.avatar_b64_map[saved_name] = self.cfg["avatar_b64"]

        self.room_entry_var    = tk.StringVar(value="genel")
        self.status_var        = tk.StringVar(value="Bağlı değil")
        self.audio_status_var  = tk.StringVar(value="")
        self.screen_status_var = tk.StringVar(value="")
        self.search_var        = tk.StringVar()
        self.typing_var        = tk.StringVar(value="")
        self.msg_search_var    = tk.StringVar()

        self.sock    = None
        self.running = True

        self.current_room      = ""
        self.room_history      = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
        self.room_users        = defaultdict(dict)
        self.room_join_times   = defaultdict(dict)
        self.known_rooms       = {}
        self.room_owner        = {}
        self.banned_users      = defaultdict(set)
        self.seen_packet_ids   = set()
        self.image_refs        = []
        self.embed_refs        = []
        self.selected_user     = None
        self.pinned_messages   = defaultdict(list)
        self.draft_messages    = {}
        self.typing_users      = defaultdict(dict)
        self._unread_counts    = defaultdict(int)
        self._mention_counts   = defaultdict(int)  # [İYİLEŞTİRME 1] Mention sayacı

        # Ses kaydı
        self.is_recording    = False
        self.audio_frames    = []
        self.audio_stream    = None
        self.record_start_ts = 0.0

        # Ekran paylaşımı
        self.screen_sharing        = False
        self.screen_thread         = None
        self.screen_buffers        = {}
        self.screen_preview_photo  = None
        self.current_screen_sender = ""
        self.current_screen_ts     = 0.0
        self.viewer_window         = None
        self.viewer_label          = None
        self.last_screen_ts        = 0.0

        # Avatar
        self.avatar_cache = {}
        self.avatar_refs  = []

        # Gruplama
        self._last_chat_sender = ""
        self._last_chat_ts     = 0.0

        # Chunk tampon
        self.file_buffers = {}

        # Mesaj satır haritası
        self._msg_line_map: dict[str, str] = {}

        # [İYİLEŞTİRME 2] Reply state
        self._reply_item: ChatItem | None = None

        # [İYİLEŞTİRME 3] Mesaj geçmişi (↑ ↓ navg.)
        self._sent_history = []
        self._sent_hist_idx = -1

        # [İYİLEŞTİRME 4] Toast kuyruğu
        self._toast_queue = []
        self._active_toast = None

        # [İYİLEŞTİRME 5] Bağlantı istatistikleri
        self._stats = {"sent": 0, "recv": 0, "errors": 0, "start_time": time.time()}

        # [İYİLEŞTİRME 6] Odaya göre başlıklar/açıklamalar
        self.room_topics = {}

        # [İYİLEŞTİRME 7] Kullanıcı notları
        self.user_notes = self.cfg.get("user_notes", {})

        # Context menü state
        self._ctx_item_id = None

        # [İYİLEŞTİRME 8] Animasyon state
        self._sidebar_anim_jobs = []

        self._show_splash()

        self.root.bind("<Control-v>", self._paste_image)
        self.root.bind("<Command-v>", self._paste_image)
        self.root.bind("<Control-f>", lambda e: self._focus_chat_search())
        self.root.bind("<Control-k>", lambda e: self._quick_room_switcher())
        self.root.bind("<Escape>",    self._on_escape)
        self.root.bind("<Control-comma>", lambda e: self._show_settings())

    # ==================== SPLASH =====================
    def _show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        w, h   = 460, 300
        splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        splash.configure(bg=PANEL_3)

        tk.Frame(splash, bg=self.theme_accent, height=3).pack(fill=tk.X)

        cnt = tk.Frame(splash, bg=PANEL_3)
        cnt.pack(fill=tk.BOTH, expand=True, padx=48, pady=36)

        logo_f = tk.Frame(cnt, bg=PANEL_3)
        logo_f.pack(pady=(0, 8))
        tk.Label(logo_f, text="⚡", bg=PANEL_3, fg=self.theme_accent,
                 font=("Segoe UI", 40)).pack(side=tk.LEFT)
        tk.Label(logo_f, text="OPSI", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 36, "bold")).pack(side=tk.LEFT, padx=(4, 0))
        tk.Label(logo_f, text="Pro", bg=PANEL_3, fg=self.theme_accent,
                 font=("Segoe UI", 18)).pack(side=tk.LEFT, padx=(4, 0), pady=(14, 0))

        self._splash_lbl = tk.Label(cnt, text="Başlatılıyor...", bg=PANEL_3, fg=MUTED,
                                    font=("Segoe UI", 10))
        self._splash_lbl.pack(pady=(12, 0))

        prog_frame = tk.Frame(cnt, bg=BORDER, height=4)
        prog_frame.pack(fill=tk.X, pady=(16, 0))
        prog_fill = tk.Frame(prog_frame, bg=self.theme_accent, height=4)
        prog_fill.place(x=0, y=0, width=0, height=4)

        tk.Label(cnt, text=f"v{APP_VERSION}  •  LAN Anlık Mesajlaşma",
                 bg=PANEL_3, fg=MUTED_2, font=("Segoe UI", 8)).pack(
                     anchor="se", side=tk.BOTTOM, pady=(8, 0))

        steps = [
            (15,  "Ağ soketi açılıyor…"),
            (40,  "Arayüz hazırlanıyor…"),
            (65,  "Yapılandırma yükleniyor…"),
            (85,  "Bağlantı kuruluyor…"),
            (100, "Hazır!"),
        ]
        step_idx = [0]

        def animate_progress(val=0):
            if not splash.winfo_exists():
                return
            w_total = prog_frame.winfo_width() or 364
            prog_fill.place(x=0, y=0, width=int(w_total * val / 100), height=4)
            if step_idx[0] < len(steps) and val >= steps[step_idx[0]][0]:
                if splash.winfo_exists():
                    self._splash_lbl.config(text=steps[step_idx[0]][1])
                step_idx[0] += 1
            if val < 100:
                splash.after(10, lambda: animate_progress(min(100, val + 2)))
            else:
                splash.after(300, finish)

        def finish():
            if splash.winfo_exists():
                splash.destroy()
            self._build_ui()
            self._start_network()
            self._tick_ui()
            self._system_message(f"⚡ OPSI Pro v{APP_VERSION}'e hoş geldiniz! · /help ile komutları görün", ACCENT)

        splash.after(80, lambda: animate_progress(0))

    # ==================== CONFIG ====================
    def _load_config(self):
        if not os.path.exists(CONFIG_DOSYASI):
            return {}
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(CONFIG_DOSYASI, "r", encoding=enc) as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            except OSError:
                return {}
        try:
            os.remove(CONFIG_DOSYASI)
        except Exception:
            pass
        return {}

    def _save_config(self):
        me = self.username_var.get().strip()
        data = {
            "username":           me,
            "avatar_b64":         self.avatar_b64_map.get(me, ""),
            "sound_enabled":      self.sound_enabled,
            "theme_accent":       self.theme_accent,
            "user_status":        self.user_status,
            "compact_mode":       self.compact_mode,
            "show_timestamps":    self.show_timestamps,
            "notify_mentions_only": self.notify_mentions_only,
            "font_size":          self.font_size,
            "message_preview":    self.message_preview,
            "user_notes":         self.user_notes,
        }
        try:
            tmp = CONFIG_DOSYASI + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, CONFIG_DOSYASI)
        except Exception:
            pass

    def _app_exit(self, event=None):
        if self.current_room:
            if not messagebox.askyesno("Çıkış", "OPSI Pro'dan çıkmak istediğinizden emin misiniz?"):
                return
        self.running = False
        self._save_config()
        self.leave_room()
        try:
            subprocess.Popen(["C:\\Program Files (x86)\\LanSchool\\student.exe"])
        except Exception:
            pass
        os._exit(0)

    # ==================== BİLDİRİM / SES ====================
    def _play_pop(self):
        if not self.sound_enabled or not AUDIO_AVAILABLE:
            return
        def _worker():
            try:
                sr = 22050
                t  = np.linspace(0, 0.08, int(sr * 0.08), endpoint=False)
                wave = (np.sin(2 * np.pi * 880 * t) * 0.25 *
                        np.exp(-t * 40)).astype(np.float32)
                sd.play(wave, samplerate=sr)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _play_mention_sound(self):
        """[İYİLEŞTİRME 9] Mention için farklı ses"""
        if not self.sound_enabled or not AUDIO_AVAILABLE:
            return
        def _worker():
            try:
                sr = 22050
                for freq, dur in [(660, 0.06), (880, 0.08), (1100, 0.10)]:
                    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
                    wave = (np.sin(2 * np.pi * freq * t) * 0.22 *
                            np.exp(-t * 15)).astype(np.float32)
                    sd.play(wave, samplerate=sr)
                    sd.wait()
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _play_join_sound(self):
        if not self.sound_enabled or not AUDIO_AVAILABLE:
            return
        def _worker():
            try:
                sr = 22050
                for freq, dur in [(440, 0.05), (660, 0.07)]:
                    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
                    wave = (np.sin(2 * np.pi * freq * t) * 0.2 *
                            np.exp(-t * 20)).astype(np.float32)
                    sd.play(wave, samplerate=sr)
                    sd.wait()
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _play_error_sound(self):
        if not self.sound_enabled or not AUDIO_AVAILABLE:
            return
        def _worker():
            try:
                sr = 22050
                t  = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
                wave = (np.sin(2 * np.pi * 220 * t) * 0.2 *
                        np.exp(-t * 10)).astype(np.float32)
                sd.play(wave, samplerate=sr)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    # [İYİLEŞTİRME 10] Toast bildirim sistemi - animasyonlu
    def _show_notification(self, title, message, color=None, is_mention=False):
        if self.root.focus_displayof() is not None:
            return
        if self.notify_mentions_only and not is_mention:
            return
        if is_mention:
            self._play_mention_sound()
        else:
            self._play_pop()
        self._queue_toast(title, message, color or self.theme_accent, is_mention)

    def _queue_toast(self, title, msg, color, urgent=False):
        self._toast_queue.append((title, msg, color, urgent))
        if self._active_toast is None or not self._active_toast.winfo_exists():
            self._show_next_toast()

    def _show_next_toast(self):
        if not self._toast_queue:
            self._active_toast = None
            return
        title, msg, color, urgent = self._toast_queue.pop(0)
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.0)
        w, h = 360, 90
        sw   = self.root.winfo_screenwidth()
        sh   = self.root.winfo_screenheight()
        x    = sw - w - 18
        y    = sh - h - 90
        toast.geometry(f"{w}x{h}+{x}+{y}")
        toast.configure(bg=PANEL_2)
        self._active_toast = toast

        # Accent bar + shadow frame
        tk.Frame(toast, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y)
        c = tk.Frame(toast, bg=PANEL_2)
        c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=14, pady=12)

        title_f = tk.Frame(c, bg=PANEL_2)
        title_f.pack(fill=tk.X)
        if urgent:
            tk.Label(title_f, text="🔔", bg=PANEL_2, fg=color,
                     font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0,4))
        tk.Label(title_f, text=title, bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, anchor="w")

        tk.Label(c, text=msg[:52] + ("…" if len(msg) > 52 else ""),
                 bg=PANEL_2, fg=MUTED, font=("Segoe UI", 9),
                 anchor="w", justify=tk.LEFT).pack(anchor="w")

        close_lbl = tk.Label(toast, text="×", bg=PANEL_2, fg=MUTED,
                             font=("Segoe UI", 15), cursor="hand2", padx=6)
        close_lbl.pack(side=tk.RIGHT, padx=4)
        close_lbl.bind("<Button-1>", lambda e: self._dismiss_toast(toast))
        toast.bind("<Button-1>", lambda e: self._dismiss_toast(toast))

        # Fade in
        def fade_in(a=0.0):
            if not toast.winfo_exists(): return
            a = min(a + 0.08, 0.96)
            toast.attributes("-alpha", a)
            if a < 0.96:
                toast.after(16, lambda: fade_in(a))
        fade_in()

        toast.after(TOAST_DURATION_MS, lambda: self._dismiss_toast(toast))

    def _dismiss_toast(self, toast):
        def fade_out(a=0.96):
            if not toast.winfo_exists():
                self._show_next_toast()
                return
            a = max(a - 0.12, 0.0)
            toast.attributes("-alpha", a)
            if a > 0.0:
                toast.after(16, lambda: fade_out(a))
            else:
                if toast.winfo_exists():
                    toast.destroy()
                self._show_next_toast()
        fade_out()

    # ==================== AVATAR ====================
    def _avatar_color(self, username):
        hex_c = AVATAR_PALETTE[hash(username) % len(AVATAR_PALETTE)]
        return (int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16))

    def _make_circle_from_pil(self, img, size):
        img    = img.convert("RGBA").resize((size, size), Image.LANCZOS)
        mask   = Image.new("L", (size, size), 0)
        draw   = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, size-1, size-1], fill=255)
        result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        result.paste(img, mask=mask)
        return ImageTk.PhotoImage(result)

    def _make_default_avatar(self, username, size):
        r, g, b = self._avatar_color(username)
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Gradient effect
        for i in range(size):
            ratio = i / size
            rr = int(r * (1 - ratio * 0.25))
            gg = int(g * (1 - ratio * 0.25))
            bb = int(b * (1 - ratio * 0.25))
            draw.line([(0, i), (size, i)], fill=(rr, gg, bb, 255))
        mask2 = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask2).ellipse([0, 0, size-1, size-1], fill=255)
        img.putalpha(mask2)

        initial   = (username[0].upper() if username else "?")
        font_size = max(10, size // 2)
        font      = None
        for fp in ["arial.ttf", "Arial.ttf",
                   "/System/Library/Fonts/Helvetica.ttc",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), initial, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            x = (size - tw)//2 - bbox[0]
            y = (size - th)//2 - bbox[1]
        except Exception:
            x, y = size//4, size//4
        draw.text((x, y), initial, fill=(255, 255, 255, 240), font=font)
        return ImageTk.PhotoImage(img)

    def _get_avatar_image(self, username, size=40):
        key = f"{username}_{size}"
        if key in self.avatar_cache:
            return self.avatar_cache[key]
        if username in self.avatar_b64_map:
            try:
                raw   = base64.b64decode(self.avatar_b64_map[username])
                pil   = Image.open(io.BytesIO(raw))
                photo = self._make_circle_from_pil(pil, size)
                self.avatar_cache[key] = photo
                return photo
            except Exception:
                pass
        photo = self._make_default_avatar(username, size)
        self.avatar_cache[key] = photo
        return photo

    def _pick_profile_photo(self):
        path = filedialog.askopenfilename(
            title="Profil fotoğrafı seç",
            filetypes=[("Resimler", "*.png *.jpg *.jpeg *.webp *.bmp"), ("Tümü", "*.*")])
        if not path:
            return
        try:
            pil = Image.open(path).convert("RGB")
            pil.thumbnail((128, 128))
            buf = io.BytesIO()
            pil.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            me  = self.username_var.get().strip()
            self.avatar_b64_map[me] = b64
            for k in list(self.avatar_cache):
                if k.startswith(f"{me}_"):
                    del self.avatar_cache[k]
            self._update_own_avatar_display()
            self._save_config()
            if self.current_room and len(b64) <= 28000:
                self._send_packet(self._build_packet("AVATAR", {"b64": b64}))
            self._system_message("✅ Profil fotoğrafı güncellendi.", SUCCESS)
        except Exception as exc:
            messagebox.showerror("Hata", f"Fotoğraf yüklenemedi:\n{exc}")

    def _update_own_avatar_display(self):
        me = self.username_var.get().strip()
        if not me:
            return
        photo = self._get_avatar_image(me, 34)
        self.avatar_refs.append(photo)
        if hasattr(self, "user_avatar_lbl"):
            self.user_avatar_lbl.config(image=photo)
            self.user_avatar_lbl.image = photo

    # ==================== ARAYÜZ ====================
    def _build_ui(self):
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill=tk.BOTH, expand=True)

        # Sol sidebar (kanallar)
        self.sidebar = tk.Frame(container, bg=PANEL_3, width=250)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        tk.Frame(container, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Sağ sidebar (üyeler)
        self.members_panel = tk.Frame(container, bg=PANEL, width=230)
        self.members_panel.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Frame(container, bg=BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y)

        # Ana alan
        self.main = tk.Frame(container, bg=BG)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self._build_members_panel()
        self._build_main_area()

    # ---------- SIDEBAR ----------
    def _build_sidebar(self):
        sb = self.sidebar

        # Sunucu header - gradient etkili
        srv_hdr = tk.Frame(sb, bg=PANEL_3, height=58)
        srv_hdr.pack(fill=tk.X)
        srv_hdr.pack_propagate(False)
        hdr_inner = tk.Frame(srv_hdr, bg=PANEL_3)
        hdr_inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        tk.Label(hdr_inner, text="⚡", bg=PANEL_3, fg=self.theme_accent,
                 font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr_inner, text=" OPSI Pro", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)

        # [İYİLEŞTİRME 11] İstatistik butonu
        stats_lbl = tk.Label(hdr_inner, text="📊", bg=PANEL_3, fg=MUTED,
                             font=("Segoe UI", 12), cursor="hand2")
        stats_lbl.pack(side=tk.RIGHT)
        self._hover(stats_lbl, MUTED, TEXT)
        stats_lbl.bind("<Button-1>", lambda e: self._show_stats_window())

        tk.Frame(sb, bg=self.theme_accent, height=2).pack(fill=tk.X)  # Accent line

        # Arama alanı
        search_wrap = tk.Frame(sb, bg=PANEL_3, pady=8)
        search_wrap.pack(fill=tk.X, padx=8)
        search_f = tk.Frame(search_wrap, bg=INPUT)
        search_f.pack(fill=tk.X)
        tk.Label(search_f, text=" 🔍", bg=INPUT, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.sidebar_search = tk.Entry(
            search_f, textvariable=self.search_var,
            bg=INPUT, fg=TEXT, insertbackground=TEXT,
            bd=0, font=("Segoe UI", 9), relief=tk.FLAT
        )
        self.sidebar_search.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(2, 4))
        self.sidebar_search.insert(0, "Kanal ara…")
        self.sidebar_search.config(fg=MUTED)
        self.sidebar_search.bind("<FocusIn>",  self._search_focus_in)
        self.sidebar_search.bind("<FocusOut>", self._search_focus_out)
        self.search_var.trace_add("write", lambda *a: self._do_room_search())

        # Kanallar başlık
        ch_hdr = tk.Frame(sb, bg=PANEL_3)
        ch_hdr.pack(fill=tk.X, padx=8, pady=(8, 2))
        tk.Label(ch_hdr, text="METİN KANALLARI", bg=PANEL_3, fg=MUTED_2,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        add_lbl = tk.Label(ch_hdr, text="+", bg=PANEL_3, fg=MUTED,
                           font=("Segoe UI", 14, "bold"), cursor="hand2")
        add_lbl.pack(side=tk.RIGHT)
        self._hover(add_lbl, MUTED, TEXT)
        add_lbl.bind("<Button-1>", lambda e: self.room_entry.focus_set())

        # Oda listesi
        rooms_frame = tk.Frame(sb, bg=PANEL_3)
        rooms_frame.pack(fill=tk.BOTH, expand=True)

        self.rooms_list = tk.Listbox(
            rooms_frame, bg=PANEL_3, fg=MUTED, bd=0, highlightthickness=0,
            selectbackground="#1f3050", selectforeground=TEXT,
            activestyle="none", font=("Segoe UI", 10), relief=tk.FLAT,
            cursor="hand2"
        )
        self.rooms_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.rooms_list.bind("<ButtonRelease-1>", self._on_room_click)
        self.rooms_list.bind("<Button-3>", self._show_room_ctx_menu)  # [İYİLEŞTİRME 12]

        # [İYİLEŞTİRME 12] Oda sağ-tık menüsü
        self._room_ctx_menu = tk.Menu(
            self.root, tearoff=0, bg=PANEL_2, fg=TEXT,
            activebackground=ACCENT_S, activeforeground=TEXT,
            bd=0, relief=tk.FLAT, font=("Segoe UI", 10)
        )
        self._room_ctx_menu.add_command(label="  🚀  Hızlı katıl", command=self._room_ctx_join)
        self._room_ctx_menu.add_command(label="  📋  Adı kopyala", command=self._room_ctx_copy)
        self._room_ctx_menu.add_separator()
        self._room_ctx_menu.add_command(label="  🔕  Bildirimleri kapat",
                                        command=lambda: self._mute_room())
        self._room_ctx_selected = ""

        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X)

        # Kanal giriş alanı
        join_area = tk.Frame(sb, bg=PANEL_3)
        join_area.pack(fill=tk.X)
        inner = tk.Frame(join_area, bg=PANEL_3)
        inner.pack(fill=tk.X, padx=10, pady=(10, 4))
        tk.Label(inner, text="# kanal adı", bg=PANEL_3, fg=MUTED_2,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self.room_entry = tk.Entry(
            inner, textvariable=self.room_entry_var,
            bg=INPUT, fg=TEXT, insertbackground=TEXT,
            bd=0, font=("Segoe UI", 10), relief=tk.FLAT
        )
        self.room_entry.pack(fill=tk.X, ipady=8, pady=(2, 0))
        self.room_entry.bind("<Return>", lambda e: self._join_from_entry())

        btn_row = tk.Frame(join_area, bg=PANEL_3)
        btn_row.pack(fill=tk.X, padx=10, pady=(4, 10))
        self.join_btn = tk.Button(
            btn_row, text="Katıl", bg=ACCENT_S, fg="white",
            bd=0, font=("Segoe UI", 10, "bold"), padx=0, pady=8,
            cursor="hand2", activebackground=self.theme_accent, activeforeground="white",
            command=self._join_from_entry
        )
        self.join_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.leave_btn = tk.Button(
            btn_row, text="Ayrıl", bg=PANEL_2, fg=DANGER,
            bd=0, font=("Segoe UI", 10), padx=0, pady=8,
            cursor="hand2", state=tk.DISABLED,
            activebackground="#2a1a1a",
            command=self.leave_room
        )
        self.leave_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X)
        self.user_panel = tk.Frame(sb, bg=USER_BG, height=64)
        self.user_panel.pack(fill=tk.X, side=tk.BOTTOM)
        self.user_panel.pack_propagate(False)
        self._build_user_panel()

    def _show_room_ctx_menu(self, event):
        idx = self.rooms_list.nearest(event.y)
        if idx < 0 or idx >= self.rooms_list.size():
            return
        raw  = self.rooms_list.get(idx).strip()
        room = re.sub(r'\s*\(\d+\)\s*$', '', raw.lstrip("#").strip())
        self._room_ctx_selected = room
        self._room_ctx_menu.tk_popup(event.x_root, event.y_root)

    def _room_ctx_join(self):
        if self._room_ctx_selected:
            self.join_room(self._room_ctx_selected)

    def _room_ctx_copy(self):
        if self._room_ctx_selected:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._room_ctx_selected)

    def _mute_room(self):
        self._system_message("Bu özellik yakında eklenecek.", MUTED)

    def _search_focus_in(self, event):
        if self.sidebar_search.get() == "Kanal ara…":
            self.sidebar_search.delete(0, tk.END)
            self.sidebar_search.config(fg=TEXT)

    def _search_focus_out(self, event):
        if not self.sidebar_search.get():
            self.sidebar_search.insert(0, "Kanal ara…")
            self.sidebar_search.config(fg=MUTED)

    def _do_room_search(self):
        q = self.search_var.get().strip().lower()
        if q == "kanal ara…":
            q = ""
        self._refresh_sidebar(filter_q=q)

    def _build_user_panel(self):
        p  = self.user_panel
        me = self.username_var.get().strip()
        av = self._get_avatar_image(me, 36)
        self.avatar_refs.append(av)

        av_wrap = tk.Frame(p, bg=USER_BG)
        av_wrap.pack(side=tk.LEFT, padx=(10, 6), pady=12)
        self.user_avatar_lbl = tk.Label(av_wrap, image=av, bg=USER_BG, cursor="hand2")
        self.user_avatar_lbl.image = av
        self.user_avatar_lbl.pack()
        self.user_avatar_lbl.bind("<Button-1>", lambda e: self._pick_profile_photo())

        status_dot = tk.Label(av_wrap, text="●", bg=USER_BG,
                              fg=STATUS_COLORS.get(self.user_status, SUCCESS),
                              font=("Segoe UI", 8))
        status_dot.place(relx=1.0, rely=1.0, anchor="se")
        self.user_status_dot = status_dot

        name_f = tk.Frame(p, bg=USER_BG)
        name_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=12)
        self.user_name_lbl = tk.Label(
            name_f, text=me, bg=USER_BG, fg=TEXT,
            font=("Segoe UI", 10, "bold"), anchor="w", cursor="hand2"
        )
        self.user_name_lbl.pack(anchor="w")
        self.user_name_lbl.bind("<Button-1>", lambda e: self._show_settings())

        # [İYİLEŞTİRME 13] Durum yazısı tıklanabilir
        self.user_status_lbl = tk.Label(
            name_f, text=STATUS_LABELS.get(self.user_status, "Çevrimiçi"),
            bg=USER_BG, fg=STATUS_COLORS.get(self.user_status, SUCCESS),
            font=("Segoe UI", 8), anchor="w", cursor="hand2"
        )
        self.user_status_lbl.pack(anchor="w")
        self.user_status_lbl.bind("<Button-1>", lambda e: self._quick_status_menu())

        btn_f = tk.Frame(p, bg=USER_BG)
        btn_f.pack(side=tk.RIGHT, padx=6)
        for sym, tip, cmd in [
            ("🔇" if not self.sound_enabled else "🔔", "Ses",     self._toggle_sound),
            ("⚙️", "Ayarlar", self._show_settings),
        ]:
            lbl = tk.Label(btn_f, text=sym, bg=USER_BG, fg=MUTED,
                           font=("Segoe UI", 13), cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=2)
            self._hover(lbl, MUTED, TEXT)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            if tip == "Ses":
                self.sound_panel_lbl = lbl

    # [İYİLEŞTİRME 13] Hızlı durum menüsü
    def _quick_status_menu(self):
        menu = tk.Menu(self.root, tearoff=0, bg=PANEL_2, fg=TEXT,
                       activebackground=ACCENT_S, activeforeground=TEXT,
                       bd=0, relief=tk.FLAT, font=("Segoe UI", 10))
        for status, label, col in [
            ("online",  "🟢  Çevrimiçi",       SUCCESS),
            ("away",    "🟡  Uzakta",           WARN),
            ("dnd",     "🔴  Rahatsız Etme",    DANGER),
            ("offline", "⚫  Görünmez",         MUTED),
        ]:
            menu.add_command(
                label=f"  {label}",
                command=lambda s=status, c=col: self._set_status(s, c)
            )
        try:
            x = self.user_status_lbl.winfo_rootx()
            y = self.user_status_lbl.winfo_rooty() - 100
            menu.tk_popup(x, y)
        except Exception:
            pass

    def _set_status(self, status, color):
        self.user_status = status
        if hasattr(self, "user_status_dot"):
            self.user_status_dot.config(fg=STATUS_COLORS.get(status, SUCCESS))
        if hasattr(self, "user_status_lbl"):
            self.user_status_lbl.config(
                text=STATUS_LABELS.get(status, status),
                fg=STATUS_COLORS.get(status, SUCCESS)
            )
        self._save_config()

    # ---------- ÜYELER PANELİ ----------
    def _build_members_panel(self):
        mp = self.members_panel

        hdr = tk.Frame(mp, bg=PANEL, height=58)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        hdr_inner = tk.Frame(hdr, bg=PANEL)
        hdr_inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=16)
        tk.Label(hdr_inner, text="ÜYELER", bg=PANEL, fg=MUTED_2,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.member_count_lbl = tk.Label(hdr_inner, text="", bg=PANEL, fg=MUTED,
                                         font=("Segoe UI", 9))
        self.member_count_lbl.pack(side=tk.LEFT, padx=(4, 0))

        tk.Frame(mp, bg=self.theme_accent, height=2).pack(fill=tk.X)

        # Üye arama
        msearch_f = tk.Frame(mp, bg=PANEL, pady=6)
        msearch_f.pack(fill=tk.X, padx=8)
        msearch_inner = tk.Frame(msearch_f, bg=INPUT)
        msearch_inner.pack(fill=tk.X)
        tk.Label(msearch_inner, text=" 🔍", bg=INPUT, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.member_search_entry = tk.Entry(
            msearch_inner, textvariable=self.msg_search_var,
            bg=INPUT, fg=TEXT, insertbackground=TEXT,
            bd=0, font=("Segoe UI", 9), relief=tk.FLAT
        )
        self.member_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=2)
        self.msg_search_var.trace_add("write", lambda *a: self._refresh_member_list())

        self.users_list = tk.Listbox(
            mp, bg=PANEL, fg=TEXT, bd=0, highlightthickness=0,
            selectbackground="#1f3050", selectforeground=TEXT,
            activestyle="none", font=("Segoe UI", 10), relief=tk.FLAT
        )
        self.users_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.users_list.bind("<Button-3>",       self._show_user_menu)
        self.users_list.bind("<ButtonRelease-1>", self._select_user)
        self.users_list.bind("<Double-Button-1>", lambda e: self._show_selected_user_info())

        self.user_menu = tk.Menu(
            self.root, tearoff=0, bg=PANEL_2, fg=TEXT,
            activebackground=ACCENT_S, activeforeground=TEXT,
            bd=0, relief=tk.FLAT, font=("Segoe UI", 10)
        )
        self.user_menu.add_command(label="  👁  Profili gör",       command=self._show_selected_user_info)
        self.user_menu.add_command(label="  🧹  Mesajlarını sil",    command=self._purge_selected_user_messages)
        self.user_menu.add_command(label="  🔨  Banla",              command=self._ban_selected_user_cmd)
        self.user_menu.add_separator()
        self.user_menu.add_command(label="  📋  Adı kopyala",        command=self._copy_selected_user_name)
        self.user_menu.add_command(label="  💬  Bahset",             command=self._mention_user)
        self.user_menu.add_command(label="  📝  Not ekle",           command=self._add_user_note)  # [İYİLEŞTİRME 14]

    # ---------- ANA ALAN ----------
    def _build_main_area(self):
        main = self.main

        # Üst başlık
        ch_hdr = tk.Frame(main, bg=BG, height=58)
        ch_hdr.pack(fill=tk.X)
        ch_hdr.pack_propagate(False)

        hdr_left = tk.Frame(ch_hdr, bg=BG)
        hdr_left.pack(side=tk.LEFT, padx=16, pady=12)
        tk.Label(hdr_left, text="#", bg=BG, fg=MUTED_2,
                 font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT)
        self.chat_title = tk.Label(hdr_left, text="kanal seçilmedi", bg=BG, fg=TEXT,
                                   font=("Segoe UI", 15, "bold"))
        self.chat_title.pack(side=tk.LEFT, padx=(4, 0))
        sep = tk.Frame(hdr_left, bg=BORDER_2, width=1, height=22)
        sep.pack(side=tk.LEFT, padx=16)

        # [İYİLEŞTİRME 15] Tıklanabilir başlık (topic düzenleme)
        self.chat_subtitle = tk.Label(hdr_left, text="Bir kanala katılın",
                                      bg=BG, fg=MUTED, font=("Segoe UI", 9),
                                      cursor="hand2")
        self.chat_subtitle.pack(side=tk.LEFT)
        self.chat_subtitle.bind("<Button-1>", lambda e: self._edit_room_topic())

        hdr_right = tk.Frame(ch_hdr, bg=BG)
        hdr_right.pack(side=tk.RIGHT, padx=16)

        for sym, tip, cmd in [
            ("🔍", "Mesajlarda ara",      self._focus_chat_search),
            ("📌", "Sabitlenmiş mesajlar", self._show_pinned),
            ("📊", "İstatistikler",        self._show_room_stats),  # [İYİLEŞTİRME 11]
            ("🔔" if self.sound_enabled else "🔕", "Bildirim", self._toggle_sound),
        ]:
            lbl = tk.Label(hdr_right, text=sym, bg=BG, fg=MUTED,
                           font=("Segoe UI", 13), cursor="hand2", padx=4)
            lbl.pack(side=tk.RIGHT, padx=4)
            self._hover(lbl, MUTED, TEXT)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            if tip == "Bildirim":
                self.sound_lbl = lbl

        tk.Label(hdr_right, textvariable=self.screen_status_var,
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        tk.Frame(main, bg=BORDER, height=1).pack(fill=tk.X)

        # Mesaj arama çubuğu (gizli)
        self.chat_search_frame = tk.Frame(main, bg=PANEL_2, height=44)
        self.chat_search_frame.pack_propagate(False)
        sch_inner = tk.Frame(self.chat_search_frame, bg=PANEL_2)
        sch_inner.pack(fill=tk.X, padx=16, pady=8)
        tk.Label(sch_inner, text="🔍", bg=PANEL_2, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.search_var2 = tk.StringVar()
        self.chat_search_entry = tk.Entry(
            sch_inner, textvariable=self.search_var2,
            bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
            bd=0, font=("Segoe UI", 10), relief=tk.FLAT
        )
        self.chat_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2, padx=8)
        self.chat_search_entry.bind("<Return>", lambda e: self._do_chat_search())
        self.chat_search_entry.bind("<Escape>", lambda e: self._close_chat_search())
        self.search_var2.trace_add("write", lambda *a: self._do_chat_search())

        # [İYİLEŞTİRME 16] İleri/geri arama navigasyonu
        self._search_positions = []
        self._search_pos_idx   = -1
        nav_f = tk.Frame(sch_inner, bg=PANEL_2)
        nav_f.pack(side=tk.LEFT)
        self._prev_search_btn = tk.Label(nav_f, text="↑", bg=PANEL_2, fg=MUTED,
                                          font=("Segoe UI", 12), cursor="hand2")
        self._prev_search_btn.pack(side=tk.LEFT, padx=2)
        self._prev_search_btn.bind("<Button-1>", lambda e: self._search_nav(-1))
        self._next_search_btn = tk.Label(nav_f, text="↓", bg=PANEL_2, fg=MUTED,
                                          font=("Segoe UI", 12), cursor="hand2")
        self._next_search_btn.pack(side=tk.LEFT, padx=2)
        self._next_search_btn.bind("<Button-1>", lambda e: self._search_nav(1))

        self.search_result_lbl = tk.Label(
            sch_inner, text="", bg=PANEL_2, fg=MUTED, font=("Segoe UI", 9)
        )
        self.search_result_lbl.pack(side=tk.LEFT, padx=(6, 0))

        close_sch = tk.Label(sch_inner, text="✕", bg=PANEL_2, fg=MUTED,
                             font=("Segoe UI", 11), cursor="hand2")
        close_sch.pack(side=tk.RIGHT)
        self._hover(close_sch, MUTED, TEXT)
        close_sch.bind("<Button-1>", lambda e: self._close_chat_search())
        self._chat_search_open = False

        # [İYİLEŞTİRME 17] Reply önizleme bandı
        self.reply_bar = tk.Frame(main, bg=PANEL_2, height=44)
        self.reply_bar.pack_propagate(False)
        reply_inner = tk.Frame(self.reply_bar, bg=PANEL_2)
        reply_inner.pack(fill=tk.X, padx=14, pady=8)
        self.reply_icon_lbl = tk.Label(reply_inner, text="↩", bg=PANEL_2, fg=self.theme_accent,
                                        font=("Segoe UI", 12))
        self.reply_icon_lbl.pack(side=tk.LEFT, padx=(0, 6))
        reply_text_f = tk.Frame(reply_inner, bg=PANEL_2)
        reply_text_f.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.reply_sender_lbl = tk.Label(reply_text_f, text="", bg=PANEL_2, fg=self.theme_accent,
                                          font=("Segoe UI", 9, "bold"), anchor="w")
        self.reply_sender_lbl.pack(anchor="w")
        self.reply_preview_lbl = tk.Label(reply_text_f, text="", bg=PANEL_2, fg=MUTED,
                                           font=("Segoe UI", 9), anchor="w")
        self.reply_preview_lbl.pack(anchor="w")
        cancel_reply_lbl = tk.Label(reply_inner, text="✕", bg=PANEL_2, fg=MUTED,
                                     font=("Segoe UI", 11), cursor="hand2")
        cancel_reply_lbl.pack(side=tk.RIGHT)
        self._hover(cancel_reply_lbl, MUTED, TEXT)
        cancel_reply_lbl.bind("<Button-1>", lambda e: self._cancel_reply())
        self._reply_bar_visible = False

        # Chat kutusu
        self.chat_box = scrolledtext.ScrolledText(
            main, bg=BG, fg=TEXT, insertbackground=TEXT,
            bd=0, highlightthickness=0, padx=16, pady=12,
            font=("Segoe UI", self.font_size), wrap=tk.WORD, relief=tk.FLAT, spacing3=4
        )
        self.chat_box.pack(fill=tk.BOTH, expand=True)
        self.chat_box.configure(state=tk.DISABLED)
        self.chat_box.bind("<Button-3>", self._show_msg_context_menu)
        self.chat_box.bind("<Double-Button-1>", self._on_double_click_msg)
        self.chat_box.bind("<Button-1>",  self._on_chat_click)

        AI = 62
        fs = self.font_size
        self.chat_box.tag_configure("time",        foreground=MUTED_2, font=("Segoe UI", 8))
        self.chat_box.tag_configure("msg",         foreground=TEXT_2,  font=("Segoe UI", fs),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("msg_cont",    foreground=TEXT_2,  font=("Segoe UI", fs),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("msg_edited",  foreground=MUTED,   font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("sys",         foreground=MUTED,   font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=20, lmargin2=20)
        self.chat_box.tag_configure("warn",        foreground=WARN,    font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=20, lmargin2=20)
        self.chat_box.tag_configure("danger",      foreground=DANGER,  font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=20, lmargin2=20)
        self.chat_box.tag_configure("success_msg", foreground=SUCCESS, font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=20, lmargin2=20)
        self.chat_box.tag_configure("self_name",   foreground="#79c0ff",font=("Segoe UI", fs, "bold"))
        self.chat_box.tag_configure("user_name",   foreground=TEXT,    font=("Segoe UI", fs, "bold"))
        self.chat_box.tag_configure("owner_name",  foreground=GOLD,    font=("Segoe UI", fs, "bold"))
        self.chat_box.tag_configure("audio",       foreground=ACCENT_2,font=("Segoe UI", fs),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("owner_badge", foreground=GOLD,    font=("Segoe UI", fs-2))
        self.chat_box.tag_configure("highlight",   background="#2f3d1a",foreground="#9ee87a")
        self.chat_box.tag_configure("mention",     background=MENTION, foreground="#79c0ff")
        self.chat_box.tag_configure("file",        foreground=ACCENT,  font=("Segoe UI", fs),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("pinned_mark", foreground=GOLD,    font=("Segoe UI", fs-2))
        self.chat_box.tag_configure("date_sep",    foreground=MUTED_2, font=("Segoe UI", 8, "bold"),
                                     justify="center")
        self.chat_box.tag_configure("link",        foreground=ACCENT,  font=("Segoe UI", fs, "underline"),
                                     lmargin1=AI, lmargin2=AI)
        self.chat_box.tag_configure("reply_quote", foreground=MUTED,   font=("Segoe UI", fs-2, "italic"),
                                     lmargin1=AI+8, lmargin2=AI+8, background=REPLY_BG)  # [İYİLEŞTİRME 17]
        self.chat_box.tag_configure("code_inline", foreground=TEAL,    font=("Courier New", fs-1),
                                     background="#161b22")  # [İYİLEŞTİRME 18]

        # Yazıyor... göstergesi
        self.typing_lbl = tk.Label(
            main, textvariable=self.typing_var,
            bg=BG, fg=MUTED, font=("Segoe UI", 8, "italic"),
            anchor="w", height=1
        )
        self.typing_lbl.pack(fill=tk.X, padx=20)

        # [İYİLEŞTİRME 19] Scroll-to-bottom butonu
        self._scroll_btn_visible = False
        self.scroll_btn = tk.Label(
            main, text="▼  Aşağı", bg=PANEL_2, fg=MUTED_2,
            font=("Segoe UI", 9), cursor="hand2", padx=10, pady=4
        )
        self.scroll_btn.bind("<Button-1>", lambda e: self._scroll_to_bottom())
        self.chat_box.bind("<MouseWheel>",   self._on_chat_scroll)
        self.chat_box.bind("<Button-4>",     self._on_chat_scroll)
        self.chat_box.bind("<Button-5>",     self._on_chat_scroll)

        # Giriş alanı
        input_outer = tk.Frame(main, bg=BG)
        input_outer.pack(fill=tk.X, padx=16, pady=(2, 14))

        input_box = tk.Frame(input_outer, bg=INPUT, bd=0, highlightthickness=1,
                             highlightcolor=BORDER_2, highlightbackground=BORDER)
        input_box.pack(fill=tk.X)

        def icon_btn(parent, text, cmd=None, hover_fg=TEXT, size=14):
            lbl = tk.Label(parent, text=text, bg=INPUT, fg=MUTED,
                           font=("Segoe UI", size), cursor="hand2", padx=4)
            lbl.pack(side=tk.LEFT, padx=(4, 0), pady=6)
            self._hover(lbl, MUTED, hover_fg)
            if cmd:
                lbl.bind("<Button-1>", lambda e: cmd())
            return lbl

        icon_btn(input_box, "🖼️",  self.send_image)
        icon_btn(input_box, "📎",  self.send_file)
        self.screen_icon = icon_btn(input_box, "🖥️", self._toggle_screen_share)
        icon_btn(input_box, "🎁",  self._show_gif_window)  # [İYİLEŞTİRME 20]

        tk.Frame(input_box, bg=BORDER, width=1, height=24).pack(side=tk.LEFT, padx=4, pady=8)

        self.msg_entry = tk.Text(
            input_box, bg=INPUT, fg=TEXT,
            insertbackground=TEXT, bd=0,
            font=("Segoe UI", self.font_size), relief=tk.FLAT,
            height=1, wrap=tk.WORD, undo=True
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=8, padx=6)
        self.msg_entry.bind("<Return>",         self._on_entry_return)
        self.msg_entry.bind("<Shift-Return>",   self._on_shift_return)  # [İYİLEŞTİRME 21]
        self.msg_entry.bind("<KeyRelease>",     self._on_typing)
        self.msg_entry.bind("<Up>",             self._hist_prev)        # [İYİLEŞTİRME 3]
        self.msg_entry.bind("<Down>",           self._hist_next)
        self.msg_entry.bind("<Tab>",            self._autocomplete_mention)  # [İYİLEŞTİRME 22]
        self.msg_entry.bind("<Configure>",      self._auto_resize_entry)

        # Sağ ikonlar
        emoji_lbl = icon_btn(input_box, "😊", self._show_emoji_picker, WARN, size=15)
        self.mic_btn = tk.Label(
            input_box, text="🎤", bg=INPUT, fg=MUTED,
            font=("Segoe UI", 15), cursor="hand2", padx=4
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 2))
        self._hover(self.mic_btn, MUTED, DANGER)
        self.mic_btn.bind("<ButtonPress-1>",   self._start_audio_record)
        self.mic_btn.bind("<ButtonRelease-1>", self._stop_audio_record)

        self.send_btn = tk.Label(
            input_box, text="➤", bg=INPUT, fg=self.theme_accent,
            font=("Segoe UI", 14, "bold"), cursor="hand2", padx=8
        )
        self.send_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._hover(self.send_btn, self.theme_accent, ACCENT_H)
        self.send_btn.bind("<Button-1>", lambda e: self.send_message())

        # Alt bilgi çubuğu
        info_row = tk.Frame(input_outer, bg=BG)
        info_row.pack(fill=tk.X, pady=(3, 0))

        self.char_count_lbl = tk.Label(
            info_row, text="", bg=BG, fg=MUTED_2, font=("Segoe UI", 7)
        )
        self.char_count_lbl.pack(side=tk.RIGHT)

        tk.Label(info_row, textvariable=self.audio_status_var,
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT)

        # [İYİLEŞTİRME 23] Klavye ipuçları
        shortcut_lbl = tk.Label(info_row, text="Enter: Gönder  •  Shift+Enter: Yeni satır  •  ↑/↓: Geçmiş  •  Tab: @tamamla",
                                 bg=BG, fg=MUTED_2, font=("Segoe UI", 7))
        shortcut_lbl.pack(side=tk.LEFT, padx=6)

        # Context menü
        self.msg_ctx_menu = tk.Menu(
            self.root, tearoff=0, bg=PANEL_2, fg=TEXT,
            activebackground=ACCENT_S, activeforeground=TEXT,
            bd=0, relief=tk.FLAT, font=("Segoe UI", 10)
        )
        self.msg_ctx_menu.add_command(label="  ✏️  Düzenle",           command=self._edit_my_message)
        self.msg_ctx_menu.add_command(label="  🗑️  Sil",                command=self._delete_my_message)
        self.msg_ctx_menu.add_command(label="  📌  Sabitle / Kaldır",   command=self._pin_message)
        self.msg_ctx_menu.add_separator()
        self.msg_ctx_menu.add_command(label="  📋  Kopyala",            command=self._copy_message_text)
        self.msg_ctx_menu.add_command(label="  💬  Yanıtla",            command=self._set_reply_from_ctx)
        self.msg_ctx_menu.add_command(label="  😊  Tepki ver",          command=self._add_reaction)
        self.msg_ctx_menu.add_separator()
        self.msg_ctx_menu.add_command(label="  🔗  Mesaj ID kopyala",   command=self._copy_msg_id)  # [İYİLEŞTİRME 24]
        self._ctx_item_id = None

        self._toggle_inputs(False)
        self.msg_entry.config(state=tk.DISABLED)

    # ==================== YARDIMCI ====================
    def _hover(self, widget, fg_normal, fg_hover):
        widget.bind("<Enter>", lambda e: widget.config(fg=fg_hover))
        widget.bind("<Leave>", lambda e: widget.config(fg=fg_normal))

    def _toggle_inputs(self, state: bool):
        s = tk.NORMAL if state else tk.DISABLED
        self.msg_entry.config(state=s)
        self.leave_btn.config(state=s)

    def _on_escape(self, event=None):
        if self._chat_search_open:
            self._close_chat_search()
        elif self._reply_bar_visible:
            self._cancel_reply()

    def _on_entry_return(self, event):
        self.send_message()
        return "break"

    def _on_shift_return(self, event):
        """[İYİLEŞTİRME 21] Shift+Enter yeni satır ekler"""
        self.msg_entry.insert(tk.INSERT, "\n")
        self._auto_resize_entry()
        return "break"

    def _auto_resize_entry(self, event=None):
        """Giriş kutusu içeriğe göre büyür (maks 4 satır)"""
        lines = int(self.msg_entry.index(tk.END).split(".")[0])
        new_h = min(max(1, lines), 4)
        self.msg_entry.config(height=new_h)

    def _get_entry_text(self) -> str:
        return self.msg_entry.get("1.0", tk.END).rstrip("\n")

    def _clear_entry(self):
        self.msg_entry.delete("1.0", tk.END)
        self.msg_entry.config(height=1)

    # ==================== SCROLL ====================
    def _on_chat_scroll(self, event=None):
        """Yukarı kaydırıldığında 'Aşağı' butonu göster"""
        try:
            pos = self.chat_box.yview()
            if pos[1] < 0.99 and not self._scroll_btn_visible:
                self.scroll_btn.place(relx=0.5, rely=0.99, anchor="s",
                                      in_=self.chat_box, x=0, y=-6)
                self._scroll_btn_visible = True
            elif pos[1] >= 0.99 and self._scroll_btn_visible:
                self.scroll_btn.place_forget()
                self._scroll_btn_visible = False
        except Exception:
            pass

    def _scroll_to_bottom(self):
        self.chat_box.see(tk.END)
        try:
            self.scroll_btn.place_forget()
            self._scroll_btn_visible = False
        except Exception:
            pass

    # ==================== AYARLAR ====================
    def _show_settings(self):
        if hasattr(self, "_swin") and self._swin.winfo_exists():
            self._swin.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("Kullanıcı Ayarları — OPSI Pro")
        win.geometry("560x620")
        win.configure(bg=PANEL)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self._swin = win

        # Header
        hdr = tk.Frame(win, bg=PANEL_3, height=60)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Ayarlar", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=20, pady=18)
        tk.Label(hdr, text=f"v{APP_VERSION}", bg=PANEL_3, fg=MUTED_2,
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=20)
        tk.Frame(win, bg=self.theme_accent, height=2).pack(fill=tk.X)

        # Scroll frame
        canvas = tk.Canvas(win, bg=PANEL, highlightthickness=0)
        sb_sc  = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb_sc.set)
        sb_sc.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(canvas, bg=PANEL)
        canvas.create_window((0, 0), window=inner, anchor="nw", width=560)
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        def section(t, parent=inner):
            tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=(18, 8))
            tk.Label(parent, text=t, bg=PANEL, fg=MUTED_2,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(0, 8))

        # Profil
        section("PROFİL")
        prof_f = tk.Frame(inner, bg=PANEL)
        prof_f.pack(fill=tk.X, padx=20, pady=4)
        me  = self.username_var.get().strip()
        av  = self._get_avatar_image(me, 56)
        self.avatar_refs.append(av)
        av_lbl = tk.Label(prof_f, image=av, bg=PANEL, cursor="hand2")
        av_lbl.image = av
        av_lbl.pack(side=tk.LEFT)
        av_lbl.bind("<Button-1>", lambda e: (self._pick_profile_photo(), win.lift()))

        name_col = tk.Frame(prof_f, bg=PANEL)
        name_col.pack(side=tk.LEFT, padx=14, fill=tk.X, expand=True)
        tk.Label(name_col, text="Kullanıcı adı", bg=PANEL, fg=MUTED_2,
                 font=("Segoe UI", 8)).pack(anchor="w")
        name_entry = tk.Entry(name_col, textvariable=self.username_var,
                              bg=INPUT, fg=TEXT, insertbackground=TEXT,
                              bd=0, font=("Segoe UI", 11))
        name_entry.pack(fill=tk.X, ipady=7)

        btn_col = tk.Frame(prof_f, bg=PANEL)
        btn_col.pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(btn_col, text="📷 Fotoğraf", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
                  activebackground=self.theme_accent,
                  command=lambda: (self._pick_profile_photo(), win.lift())
                  ).pack(pady=(0, 4))
        tk.Button(btn_col, text="🗑️ Sıfırla", bg=PANEL_2, fg=MUTED,
                  bd=0, font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
                  command=lambda: self._reset_avatar(me, win)).pack()

        # Durum
        section("DURUM")
        status_var = tk.StringVar(value=self.user_status)
        status_f   = tk.Frame(inner, bg=PANEL)
        status_f.pack(fill=tk.X, padx=20, pady=4)
        for i, (status, label, col) in enumerate([
            ("online",  "🟢  Çevrimiçi",    SUCCESS),
            ("away",    "🟡  Uzakta",        WARN),
            ("dnd",     "🔴  Rahatsız Etme", DANGER),
            ("offline", "⚫  Görünmez",      MUTED),
        ]):
            rb = tk.Radiobutton(status_f, text=label, variable=status_var, value=status,
                                bg=PANEL, fg=TEXT, selectcolor=INPUT, indicatoron=True,
                                activebackground=PANEL, font=("Segoe UI", 10))
            rb.grid(row=i//2, column=i%2, sticky="w", padx=8, pady=2)

        # Bildirim & Ses
        section("BİLDİRİM & SES")
        snd_var     = tk.BooleanVar(value=self.sound_enabled)
        mention_var = tk.BooleanVar(value=self.notify_mentions_only)
        prev_var    = tk.BooleanVar(value=self.message_preview)

        for var, text, cmd in [
            (snd_var,     "Mesaj sesi etkin",           lambda: None),
            (mention_var, "Yalnız @mention'da bildir",  lambda: None),
            (prev_var,    "Toast bildirim içeriği göster", lambda: None),
        ]:
            tk.Checkbutton(inner, text=text, variable=var,
                           bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL,
                           font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=2)

        # Görünüm
        section("GÖRÜNÜM")
        compact_var = tk.BooleanVar(value=self.compact_mode)
        ts_var      = tk.BooleanVar(value=self.show_timestamps)
        for var, text in [
            (compact_var, "Kompakt mesaj görünümü"),
            (ts_var,      "Zaman damgaları göster"),
        ]:
            tk.Checkbutton(inner, text=text, variable=var,
                           bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL,
                           font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=2)

        # Yazı boyutu
        fs_row = tk.Frame(inner, bg=PANEL)
        fs_row.pack(fill=tk.X, padx=20, pady=6)
        tk.Label(fs_row, text="Yazı boyutu:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        fs_var = tk.IntVar(value=self.font_size)
        for sz in [9, 10, 11, 12, 13, 14]:
            tk.Radiobutton(fs_row, text=str(sz), variable=fs_var, value=sz,
                           bg=PANEL, fg=TEXT, selectcolor=INPUT,
                           activebackground=PANEL, font=("Segoe UI", 10)
                           ).pack(side=tk.LEFT, padx=4)

        # Tema rengi
        section("TEMA AKSANI")
        theme_f = tk.Frame(inner, bg=PANEL)
        theme_f.pack(fill=tk.X, padx=20, pady=4)
        selected_color = tk.StringVar(value=self.theme_accent)
        for name, color in THEMES.items():
            col_f = tk.Frame(theme_f, bg=PANEL)
            col_f.pack(side=tk.LEFT, padx=4)
            c_lbl = tk.Label(col_f, bg=color, cursor="hand2", width=3, height=1)
            c_lbl.pack()
            tk.Label(col_f, text=name.split()[0], bg=PANEL, fg=MUTED_2,
                     font=("Segoe UI", 7)).pack()
            if color == self.theme_accent:
                c_lbl.config(relief="ridge", bd=2)
            c_lbl.bind("<Button-1>", lambda e, col=color, lbl=c_lbl:
                       (selected_color.set(col), self._preview_accent(col)))

        # Kaydet
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=18)
        btn_row = tk.Frame(inner, bg=PANEL)
        btn_row.pack(fill=tk.X, padx=20, pady=(0, 24))

        def on_save():
            self.compact_mode         = compact_var.get()
            self.show_timestamps      = ts_var.get()
            self.sound_enabled        = snd_var.get()
            self.notify_mentions_only = mention_var.get()
            self.message_preview      = prev_var.get()
            self.font_size            = fs_var.get()
            new_status = status_var.get()
            if new_status != self.user_status:
                col = STATUS_COLORS.get(new_status, SUCCESS)
                self._set_status(new_status, col)
            new_accent = selected_color.get()
            if new_accent != self.theme_accent:
                self.theme_accent = new_accent
            self.sound_lbl.config(text="🔔" if self.sound_enabled else "🔕")
            if hasattr(self, "sound_panel_lbl"):
                self.sound_panel_lbl.config(text="🔇" if not self.sound_enabled else "🔔")
            self._save_config()
            win.destroy()
            self._system_message("✅ Ayarlar kaydedildi.", SUCCESS)

        tk.Button(btn_row, text="Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 10, "bold"), padx=28, pady=9,
                  cursor="hand2", activebackground=self.theme_accent, command=on_save
                  ).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="İptal", bg=PANEL_2, fg=MUTED,
                  bd=0, font=("Segoe UI", 10), padx=22, pady=9,
                  cursor="hand2", activebackground=HOVER, command=win.destroy
                  ).pack(side=tk.RIGHT, padx=(0, 8))

    def _reset_avatar(self, me, win=None):
        self.avatar_b64_map.pop(me, None)
        for k in list(self.avatar_cache):
            if k.startswith(f"{me}_"):
                del self.avatar_cache[k]
        self._update_own_avatar_display()
        if win:
            win.lift()

    def _preview_accent(self, color):
        """Geçici tema önizleme"""
        pass

    def _toggle_sound(self, event=None):
        self.sound_enabled = not self.sound_enabled
        sym = "🔔" if self.sound_enabled else "🔕"
        self.sound_lbl.config(text=sym)
        if hasattr(self, "sound_panel_lbl"):
            self.sound_panel_lbl.config(text="🔇" if not self.sound_enabled else "🔔")
        self._save_config()

    # ==================== İSTATİSTİK ====================
    def _show_stats_window(self):
        """[İYİLEŞTİRME 11] Global istatistik penceresi"""
        win = tk.Toplevel(self.root)
        win.title("OPSI Pro — Oturum İstatistikleri")
        win.geometry("420x380")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tk.Frame(win, bg=self.theme_accent, height=3).pack(fill=tk.X)
        tk.Label(win, text="📊  Oturum İstatistikleri", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(padx=20, pady=(20, 12), anchor="w")

        uptime = int(time.time() - self._stats["start_time"])
        h, r   = divmod(uptime, 3600)
        m, s   = divmod(r, 60)

        data = [
            ("⏱  Oturum süresi",      f"{h:02d}:{m:02d}:{s:02d}"),
            ("📤  Gönderilen paket",   str(self._stats["sent"])),
            ("📥  Alınan paket",       str(self._stats["recv"])),
            ("❌  Hata sayısı",        str(self._stats["errors"])),
            ("🏠  Bilinen oda",        str(len(self.known_rooms))),
            ("💬  Aktif oda",          self.current_room or "—"),
            ("👤  Kullanıcı adı",      self.username_var.get().strip()),
            ("🌐  Port",               str(PORT)),
        ]
        if AUDIO_AVAILABLE:
            data.append(("🎤  Ses desteği", "Aktif"))
        else:
            data.append(("🎤  Ses desteği", "Yok (sounddevice eksik)"))

        for label, value in data:
            row = tk.Frame(win, bg=PANEL_2)
            row.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(row, text=f"  {label}", bg=PANEL_2, fg=MUTED,
                     font=("Segoe UI", 10), width=22, anchor="w").pack(side=tk.LEFT, pady=6)
            tk.Label(row, text=value, bg=PANEL_2, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(side=tk.LEFT, padx=8)

        tk.Button(win, text="Kapat", bg=PANEL_3, fg=MUTED,
                  bd=0, font=("Segoe UI", 9), padx=16, pady=7,
                  cursor="hand2", command=win.destroy).pack(pady=16)

    def _show_room_stats(self):
        """Mevcut oda istatistikleri"""
        if not self.current_room:
            return
        items  = list(self.room_history[self.current_room])
        msgs   = [x for x in items if x.kind == "MSG"]
        imgs   = [x for x in items if x.kind == "IMG"]
        audios = [x for x in items if x.kind == "AUDIO"]
        files  = [x for x in items if x.kind == "FILE"]
        users  = self.room_users.get(self.current_room, {})
        now    = time.time()
        online = [u for u, t in users.items() if now - t < STALE_USER_SEC]

        sender_count = defaultdict(int)
        for m in msgs:
            sender_count[m.sender] += 1
        top_sender = max(sender_count, key=sender_count.get) if sender_count else "—"

        win = tk.Toplevel(self.root)
        win.title(f"#{self.current_room} — İstatistikler")
        win.geometry("380x400")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tk.Frame(win, bg=self.theme_accent, height=3).pack(fill=tk.X)
        tk.Label(win, text=f"📊  #{self.current_room}", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(padx=20, pady=(18, 12), anchor="w")

        data = [
            ("💬  Toplam mesaj",    str(len(msgs))),
            ("🖼️  Fotoğraf",        str(len(imgs))),
            ("🎤  Ses mesajı",      str(len(audios))),
            ("📎  Dosya",           str(len(files))),
            ("👥  Çevrimiçi üye",  str(len(online))),
            ("👑  Oda kurucusu",    self.room_owner.get(self.current_room, "—")),
            ("🏆  En aktif üye",    f"{top_sender} ({sender_count.get(top_sender, 0)})"),
        ]
        for label, value in data:
            row = tk.Frame(win, bg=PANEL_2)
            row.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(row, text=f"  {label}", bg=PANEL_2, fg=MUTED,
                     font=("Segoe UI", 10), width=18, anchor="w").pack(side=tk.LEFT, pady=7)
            tk.Label(row, text=value, bg=PANEL_2, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(side=tk.LEFT, padx=8)

        tk.Button(win, text="Kapat", bg=PANEL_3, fg=MUTED,
                  bd=0, font=("Segoe UI", 9), padx=16, pady=7,
                  cursor="hand2", command=win.destroy).pack(pady=16)

    # ==================== TOPIC ====================
    def _edit_room_topic(self):
        """[İYİLEŞTİRME 15] Oda başlığı düzenleme"""
        if not self.current_room or not self._is_owner(self.current_room):
            return
        win = tk.Toplevel(self.root)
        win.title("Kanal Konusu")
        win.geometry("440x160")
        win.configure(bg=PANEL)
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Label(win, text="Kanal konusu:", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(16, 4))
        entry = tk.Entry(win, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                         bd=0, font=("Segoe UI", 11))
        entry.pack(fill=tk.X, padx=20, ipady=9)
        entry.insert(0, self.room_topics.get(self.current_room, ""))
        entry.focus_set()

        def save():
            topic = entry.get().strip()
            self.room_topics[self.current_room] = topic
            display = topic or f"Kurucu: {self.room_owner.get(self.current_room, 'bilinmiyor')}"
            self.chat_subtitle.config(text=display)
            win.destroy()

        entry.bind("<Return>", lambda e: save())
        btn_row = tk.Frame(win, bg=PANEL)
        btn_row.pack(fill=tk.X, padx=20, pady=12)
        tk.Button(btn_row, text="Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 10, "bold"), padx=20, pady=7,
                  cursor="hand2", activebackground=self.theme_accent, command=save
                  ).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="İptal", bg=PANEL_2, fg=MUTED,
                  bd=0, font=("Segoe UI", 10), padx=16, pady=7,
                  cursor="hand2", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    # ==================== MESAJ ARAMA ====================
    def _focus_search(self, event=None):
        self._focus_chat_search()

    def _focus_chat_search(self):
        if not self._chat_search_open:
            self.chat_search_frame.pack(fill=tk.X, before=self.chat_box)
            self._chat_search_open = True
        self.chat_search_entry.focus_set()
        self.chat_search_entry.select_range(0, tk.END)

    def _close_chat_search(self):
        self.chat_search_frame.pack_forget()
        self._chat_search_open = False
        self.chat_box.tag_remove("highlight", "1.0", tk.END)
        self.search_result_lbl.config(text="")
        self._search_positions.clear()
        self._search_pos_idx = -1

    def _do_chat_search(self):
        query = self.search_var2.get().strip().lower()
        self.chat_box.tag_remove("highlight", "1.0", tk.END)
        self._search_positions.clear()
        self._search_pos_idx = -1
        if not query:
            self.search_result_lbl.config(text="")
            return
        start = "1.0"
        while True:
            pos = self.chat_box.search(query, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(query)}c"
            self.chat_box.tag_add("highlight", pos, end)
            self._search_positions.append(pos)
            start = end
        count = len(self._search_positions)
        if count:
            self._search_pos_idx = 0
            self.chat_box.see(self._search_positions[0])
        self.search_result_lbl.config(
            text=f"{count} sonuç" if count else "Sonuç yok",
            fg=MUTED if count else DANGER
        )

    def _search_nav(self, direction):
        """[İYİLEŞTİRME 16] İleri/geri arama navigasyonu"""
        if not self._search_positions:
            return
        self._search_pos_idx = (self._search_pos_idx + direction) % len(self._search_positions)
        self.chat_box.see(self._search_positions[self._search_pos_idx])
        self.search_result_lbl.config(
            text=f"{self._search_pos_idx + 1} / {len(self._search_positions)}"
        )

    # ==================== EMOJİ ====================
    def _show_emoji_picker(self, event=None):
        if hasattr(self, "_emoji_win") and self._emoji_win.winfo_exists():
            self._emoji_win.destroy()
            return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=PANEL_2)
        cols = 8
        rows = math.ceil(len(EMOJI_LIST) / cols)
        w, h = cols * 44 + 20, rows * 44 + 56
        try:
            x = self.msg_entry.winfo_rootx()
            y = self.msg_entry.winfo_rooty() - h - 8
        except Exception:
            x, y = 400, 400
        win.geometry(f"{w}x{h}+{x}+{y}")
        self._emoji_win = win

        # Başlık + arama
        top_f = tk.Frame(win, bg=PANEL_2)
        top_f.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(top_f, text="Emoji Seç", bg=PANEL_2, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        close_e = tk.Label(top_f, text="✕", bg=PANEL_2, fg=MUTED,
                           font=("Segoe UI", 10), cursor="hand2")
        close_e.pack(side=tk.RIGHT)
        close_e.bind("<Button-1>", lambda e: win.destroy())

        grid = tk.Frame(win, bg=PANEL_2)
        grid.pack(padx=8, pady=(0, 8))
        for i, emoji in enumerate(EMOJI_LIST):
            r, c = divmod(i, cols)
            lbl  = tk.Label(grid, text=emoji, bg=PANEL_2, fg=TEXT,
                            font=("Segoe UI", 18), cursor="hand2", padx=3, pady=3)
            lbl.grid(row=r, column=c)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=HOVER))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=PANEL_2))
            lbl.bind("<Button-1>", lambda e, em=emoji: self._insert_emoji(em, win))

        win.bind("<FocusOut>", lambda e: win.destroy() if win.winfo_exists() else None)
        win.focus_set()

    def _insert_emoji(self, emoji, win):
        self.msg_entry.insert(tk.INSERT, emoji)
        win.destroy()
        self.msg_entry.focus_set()

    # [İYİLEŞTİRME 20] GIF placeholder penceresi
    def _show_gif_window(self):
        win = tk.Toplevel(self.root)
        win.title("GIF Gönder")
        win.geometry("360x200")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tk.Label(win, text="🎁", bg=PANEL, fg=self.theme_accent,
                 font=("Segoe UI", 40)).pack(pady=(24, 8))
        tk.Label(win, text="GIF Desteği Yakında!", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(win, text="Bu özellik bir sonraki sürümde eklenecek.", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(pady=4)
        tk.Button(win, text="Tamam", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 10, "bold"), padx=20, pady=7,
                  cursor="hand2", activebackground=self.theme_accent, command=win.destroy).pack(pady=12)

    # ==================== MESAJ CONTEXT MENÜ ====================
    def _show_msg_context_menu(self, event):
        idx     = self.chat_box.index(f"@{event.x},{event.y}")
        item_id = None
        for tag in self.chat_box.tag_names(idx):
            if tag.startswith("item_"):
                item_id = tag[5:]
                break
        self._ctx_item_id = item_id
        me  = self.username_var.get().strip()
        own = False
        if item_id and self.current_room:
            for item in self.room_history[self.current_room]:
                if item.item_id == item_id and item.sender == me and item.kind == "MSG":
                    own = True
                    break
        self.msg_ctx_menu.entryconfig(0, state=tk.NORMAL if own else tk.DISABLED)
        self.msg_ctx_menu.entryconfig(1, state=tk.NORMAL if own else tk.DISABLED)
        self.msg_ctx_menu.tk_popup(event.x_root, event.y_root)

    def _on_double_click_msg(self, event):
        idx = self.chat_box.index(f"@{event.x},{event.y}")
        for tag in self.chat_box.tag_names(idx):
            if tag.startswith("item_"):
                self._ctx_item_id = tag[5:]
                me = self.username_var.get().strip()
                item = self._get_ctx_item()
                if item and item.sender == me and item.kind == "MSG":
                    self._edit_my_message()
                return

    def _on_chat_click(self, event):
        """Link tıklama desteği"""
        idx = self.chat_box.index(f"@{event.x},{event.y}")
        tags = self.chat_box.tag_names(idx)
        if "link" in tags:
            # URL'yi al
            range_start = self.chat_box.tag_prevrange("link", idx)
            if range_start:
                url = self.chat_box.get(*range_start)
                try:
                    import webbrowser
                    webbrowser.open(url)
                except Exception:
                    pass

    def _get_ctx_item(self):
        if not self._ctx_item_id or not self.current_room:
            return None
        for item in self.room_history[self.current_room]:
            if item.item_id == self._ctx_item_id:
                return item
        return None

    def _edit_my_message(self):
        item = self._get_ctx_item()
        if not item or item.sender != self.username_var.get().strip():
            return
        win = tk.Toplevel(self.root)
        win.title("Mesajı Düzenle")
        win.geometry("520x180")
        win.configure(bg=PANEL)
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Frame(win, bg=self.theme_accent, height=3).pack(fill=tk.X)
        tk.Label(win, text="✏️  Mesajı Düzenle", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(14, 6))
        entry = tk.Entry(win, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                         bd=0, font=("Segoe UI", 12))
        entry.pack(fill=tk.X, padx=20, ipady=10)
        entry.insert(0, item.text)
        entry.focus_set()
        entry.select_range(0, tk.END)

        def do_edit():
            new_text = entry.get().strip()
            if not new_text or new_text == item.text:
                win.destroy()
                return
            item.text  = new_text
            item.edited = True
            self._send_packet(self._build_packet(
                "EDIT", {"ref_id": item.item_id, "new_text": new_text}))
            self._render_history(self.current_room)
            win.destroy()

        entry.bind("<Return>", lambda e: do_edit())
        entry.bind("<Escape>", lambda e: win.destroy())
        btn_row = tk.Frame(win, bg=PANEL)
        btn_row.pack(fill=tk.X, padx=20, pady=12)
        tk.Button(btn_row, text="Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 10, "bold"), padx=22, pady=7,
                  cursor="hand2", activebackground=self.theme_accent, command=do_edit
                  ).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="İptal", bg=PANEL_2, fg=MUTED,
                  bd=0, font=("Segoe UI", 10), padx=18, pady=7,
                  cursor="hand2", command=win.destroy
                  ).pack(side=tk.RIGHT, padx=(0, 8))

    def _edit_last_message(self, event=None):
        if not self.current_room:
            return
        me = self.username_var.get().strip()
        for item in reversed(list(self.room_history[self.current_room])):
            if item.sender == me and item.kind == "MSG":
                self._ctx_item_id = item.item_id
                self._edit_my_message()
                return

    # [İYİLEŞTİRME 3] Mesaj geçmişi navigasyonu
    def _hist_prev(self, event=None):
        if self.msg_entry.cget("state") == tk.DISABLED:
            return
        cur_text = self._get_entry_text()
        if cur_text and self._sent_hist_idx == -1:
            return "break"
        if not self._sent_history:
            return "break"
        if self._sent_hist_idx == -1:
            self._sent_hist_idx = len(self._sent_history) - 1
        elif self._sent_hist_idx > 0:
            self._sent_hist_idx -= 1
        self._clear_entry()
        self.msg_entry.insert("1.0", self._sent_history[self._sent_hist_idx])
        return "break"

    def _hist_next(self, event=None):
        if self._sent_hist_idx == -1:
            return "break"
        if self._sent_hist_idx < len(self._sent_history) - 1:
            self._sent_hist_idx += 1
            self._clear_entry()
            self.msg_entry.insert("1.0", self._sent_history[self._sent_hist_idx])
        else:
            self._sent_hist_idx = -1
            self._clear_entry()
        return "break"

    def _delete_my_message(self):
        item = self._get_ctx_item()
        if not item:
            return
        if not messagebox.askyesno("Sil", "Bu mesaj kalıcı olarak silinsin mi?",
                                   icon="warning"):
            return
        kept = deque(
            [x for x in self.room_history[self.current_room] if x.item_id != item.item_id],
            maxlen=MAX_HISTORY
        )
        self.room_history[self.current_room] = kept
        self._send_packet(self._build_packet("DELETE", {"ref_id": item.item_id}))
        self._render_history(self.current_room)

    def _pin_message(self):
        item = self._get_ctx_item()
        if not item or not self.current_room:
            return
        if item not in self.pinned_messages[self.current_room]:
            self.pinned_messages[self.current_room].append(item)
            item.pinned = True
            self._system_message(f"📌 Mesaj sabitlendi.", GOLD)
        else:
            self.pinned_messages[self.current_room].remove(item)
            item.pinned = False
            self._system_message("📌 Mesaj sabitlemesi kaldırıldı.", MUTED)
        self._render_history(self.current_room)

    def _show_pinned(self):
        if not self.current_room:
            return
        pins = self.pinned_messages.get(self.current_room, [])
        win  = tk.Toplevel(self.root)
        win.title(f"#{self.current_room} — Sabitlenmiş Mesajlar")
        win.geometry("460x420")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tk.Frame(win, bg=GOLD, height=3).pack(fill=tk.X)
        tk.Label(win, text="📌  Sabitlenmiş Mesajlar", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(padx=20, pady=(18, 10), anchor="w")

        if not pins:
            tk.Label(win, text="Bu kanalda sabitlenmiş mesaj yok.", bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 10)).pack(pady=40)
            tk.Button(win, text="Kapat", bg=PANEL_3, fg=MUTED, bd=0,
                      font=("Segoe UI", 9), padx=16, pady=6, cursor="hand2",
                      command=win.destroy).pack()
            return

        scroll_area = scrolledtext.ScrolledText(win, bg=PANEL, bd=0, state=tk.DISABLED,
                                                 highlightthickness=0, wrap=tk.WORD,
                                                 font=("Segoe UI", 10))
        scroll_area.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        scroll_area.config(state=tk.NORMAL)
        for i, pin in enumerate(pins, 1):
            ts = time.strftime("%d.%m %H:%M", time.localtime(pin.ts))
            scroll_area.insert(tk.END, f"[{i}] {pin.sender}  ·  {ts}\n", "bold_tag")
            scroll_area.insert(tk.END, f"    {pin.text[:200]}\n\n", "text_tag")
        scroll_area.tag_configure("bold_tag", foreground=GOLD, font=("Segoe UI", 10, "bold"))
        scroll_area.tag_configure("text_tag", foreground=TEXT_2)
        scroll_area.config(state=tk.DISABLED)

        tk.Button(win, text="Kapat", bg=PANEL_3, fg=MUTED, bd=0,
                  font=("Segoe UI", 9), padx=16, pady=6, cursor="hand2",
                  command=win.destroy).pack(pady=8)

    # [İYİLEŞTİRME 17] Reply sistemi
    def _set_reply_from_ctx(self):
        item = self._get_ctx_item()
        if not item:
            return
        self._set_reply(item)

    def _set_reply(self, item: ChatItem):
        self._reply_item = item
        if not self._reply_bar_visible:
            self.reply_bar.pack(fill=tk.X, before=self.typing_lbl)
            self._reply_bar_visible = True
        self.reply_sender_lbl.config(text=f"  ↩  {item.sender}'e yanıtlıyorsunuz")
        preview = (item.text[:60] + "…") if len(item.text) > 60 else item.text
        if item.kind == "IMG":
            preview = "🖼️ Fotoğraf"
        elif item.kind == "AUDIO":
            preview = f"🎤 Ses mesajı ({item.audio_sec:.1f}s)"
        elif item.kind == "FILE":
            preview = f"📎 {item.file_name}"
        self.reply_preview_lbl.config(text=f"  {preview}")
        self.msg_entry.focus_set()

    def _cancel_reply(self):
        self._reply_item = None
        if self._reply_bar_visible:
            self.reply_bar.pack_forget()
            self._reply_bar_visible = False

    def _reply_to_message(self):
        item = self._get_ctx_item()
        if item:
            self._set_reply(item)

    def _add_reaction(self):
        item = self._get_ctx_item()
        if not item:
            return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=PANEL_2)
        f = tk.Frame(win, bg=PANEL_2)
        f.pack(padx=8, pady=8)
        for em in QUICK_REACTIONS:
            lbl = tk.Label(f, text=em, bg=PANEL_2, font=("Segoe UI", 20), cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=3)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=HOVER))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=PANEL_2))
            lbl.bind("<Button-1>", lambda e, em2=em: self._do_react(item, em2, win))
        win.geometry(f"+{self.root.winfo_pointerx()-80}+{self.root.winfo_pointery()-60}")
        win.bind("<FocusOut>", lambda e: win.destroy() if win.winfo_exists() else None)
        win.focus_set()

    def _do_react(self, item, emoji, win):
        me = self.username_var.get().strip()
        if emoji not in item.reactions:
            item.reactions[emoji] = []
        if me not in item.reactions[emoji]:
            item.reactions[emoji].append(me)
        else:
            item.reactions[emoji].remove(me)
            if not item.reactions[emoji]:
                del item.reactions[emoji]
        win.destroy()
        self._render_history(self.current_room)
        # Ağa gönder
        self._send_packet(self._build_packet("REACT", {
            "ref_id": item.item_id, "emoji": emoji, "user": me
        }))

    def _copy_message_text(self):
        item = self._get_ctx_item()
        if not item:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(item.text)

    # [İYİLEŞTİRME 24] Mesaj ID kopyalama
    def _copy_msg_id(self):
        item = self._get_ctx_item()
        if not item:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(item.item_id)
        self._system_message("📋 Mesaj ID kopyalandı.", MUTED)

    # ==================== YAZMA GÖSTERGESİ ====================
    def _on_typing(self, event=None):
        text = self._get_entry_text()
        n    = len(text)
        if n > 1800:
            self.char_count_lbl.config(text=f"{n}/2000", fg=DANGER)
        elif n > 1500:
            self.char_count_lbl.config(text=f"{n}/2000", fg=WARN)
        elif n > 0:
            self.char_count_lbl.config(text=f"{n}", fg=MUTED_2)
        else:
            self.char_count_lbl.config(text="")

        if self.current_room and text:
            self._send_packet(self._build_packet("TYPING", {"typing": True}))

    def _update_typing_indicator(self, room):
        if room != self.current_room:
            return
        now    = time.time()
        typers = [u for u, ts in self.typing_users.get(room, {}).items()
                  if now - ts < 3.0 and u != self.username_var.get().strip()]
        if not typers:
            self.typing_var.set("")
        elif len(typers) == 1:
            self.typing_var.set(f"  ✏  {typers[0]} yazıyor…")
        elif len(typers) <= 3:
            self.typing_var.set(f"  ✏  {', '.join(typers)} yazıyor…")
        else:
            self.typing_var.set(f"  ✏  {len(typers)} kişi yazıyor…")

    # [İYİLEŞTİRME 22] @mention otomatik tamamlama
    def _autocomplete_mention(self, event=None):
        text = self._get_entry_text()
        cursor_pos = self.msg_entry.index(tk.INSERT)
        # @ sonrasındaki kelimeyi bul
        before = self.msg_entry.get("1.0", tk.INSERT)
        m = re.search(r'@(\w*)$', before)
        if not m or not self.current_room:
            return
        prefix = m.group(1).lower()
        users  = list(self.room_users.get(self.current_room, {}).keys())
        me     = self.username_var.get().strip()
        matches = [u for u in users if u.lower().startswith(prefix) and u != me]
        if not matches:
            return "break"
        if len(matches) == 1:
            start = f"insert-{len(m.group(1))}c"
            self.msg_entry.delete(start, tk.INSERT)
            self.msg_entry.insert(tk.INSERT, matches[0] + " ")
        else:
            # Popup
            popup = tk.Toplevel(self.root)
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.configure(bg=PANEL_2)
            try:
                x = self.msg_entry.winfo_rootx()
                y = self.msg_entry.winfo_rooty() - len(matches) * 30 - 10
            except Exception:
                x, y = 400, 400
            popup.geometry(f"200x{min(len(matches)*30+10, 180)}+{x}+{y}")
            for match in matches[:6]:
                lbl = tk.Label(popup, text=f"  @{match}", bg=PANEL_2, fg=TEXT,
                               font=("Segoe UI", 10), cursor="hand2", anchor="w")
                lbl.pack(fill=tk.X, pady=2)
                lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=HOVER))
                lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=PANEL_2))
                def select(u=match, p=popup):
                    start = f"insert-{len(m.group(1))}c"
                    self.msg_entry.delete(start, tk.INSERT)
                    self.msg_entry.insert(tk.INSERT, u + " ")
                    p.destroy()
                    self.msg_entry.focus_set()
                lbl.bind("<Button-1>", lambda e, s=select: s())
            popup.bind("<FocusOut>", lambda e: popup.destroy() if popup.winfo_exists() else None)
            popup.focus_set()
        return "break"

    # ==================== CHAT GÖSTERİMİ ====================
    def _clear_chat(self):
        self.chat_box.config(state=tk.NORMAL)
        try:
            self.chat_box.delete("1.0", tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)
        self.image_refs.clear()
        self.embed_refs.clear()
        self.avatar_refs.clear()
        self._last_chat_sender = ""
        self._last_chat_ts     = 0.0
        self._msg_line_map.clear()

    def _render_history(self, room):
        if not room:
            return
        self._clear_chat()
        prev_ts  = 0.0
        prev_day = ""
        for item in self.room_history[room]:
            # Gün ayraçı (daha akıllı)
            if item.ts:
                day_str = time.strftime("%Y-%m-%d", time.localtime(item.ts))
                if day_str != prev_day:
                    self._insert_date_separator(item.ts)
                    prev_day = day_str
            prev_ts = item.ts or prev_ts

            if item.kind == "IMG":
                self._append_image_message(item)
            elif item.kind == "AUDIO":
                self._append_audio_message(item)
            elif item.kind == "FILE":
                self._append_file_message(item)
            else:
                self._append_text_message(item)

        owner = self.room_owner.get(room, "bilinmiyor")
        topic = self.room_topics.get(room, "")
        display = topic if topic else f"Kurucu: {owner}"
        self.chat_subtitle.config(text=display)
        self._scroll_to_bottom()

    def _insert_date_separator(self, ts):
        self.chat_box.config(state=tk.NORMAL)
        now     = time.time()
        diff    = now - ts
        if diff < 86400:
            date_str = "Bugün"
        elif diff < 172800:
            date_str = "Dün"
        else:
            date_str = time.strftime("%d %B %Y", time.localtime(ts))
        self.chat_box.insert(tk.END, f"\n  ─── {date_str} ───\n\n", "date_sep")
        self.chat_box.config(state=tk.DISABLED)

    def _fmt_time(self, ts):
        if not ts:
            return ""
        if self.show_timestamps:
            return time.strftime("%H:%M", time.localtime(ts))
        return ""

    def _fmt_full_time(self, ts):
        if not ts:
            return ""
        return time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(ts))

    def _name_tag(self, sender):
        me = self.username_var.get().strip()
        if sender == me:
            return "self_name"
        if sender == self.room_owner.get(self.current_room, ""):
            return "owner_name"
        return "user_name"

    def _should_group(self, sender, ts):
        if self.compact_mode:
            return False
        if sender != self._last_chat_sender:
            return False
        if not self._last_chat_ts or not ts:
            return False
        return (ts - self._last_chat_ts) < 300

    def _insert_avatar_header(self, sender, ts):
        self.chat_box.insert(tk.END, "\n")
        av = self._get_avatar_image(sender, 40 if not self.compact_mode else 24)
        self.avatar_refs.append(av)
        self.chat_box.image_create(tk.END, image=av, padx=10, pady=4)
        self.chat_box.insert(tk.END, " ")
        self.chat_box.insert(tk.END, sender, self._name_tag(sender))
        if sender == self.room_owner.get(self.current_room, ""):
            self.chat_box.insert(tk.END, " 👑", "owner_badge")
        ts_str = self._fmt_time(ts)
        if ts_str:
            self.chat_box.insert(tk.END, f"  {ts_str}", "time")
        self.chat_box.insert(tk.END, "\n")

    def _tag_for_item(self, item_id):
        return f"item_{item_id}"

    def _auto_linkify(self, text):
        url_re = re.compile(r'(https?://[^\s]+)')
        parts  = []
        last   = 0
        for m in url_re.finditer(text):
            if m.start() > last:
                parts.append((text[last:m.start()], False))
            parts.append((m.group(), True))
            last = m.end()
        if last < len(text):
            parts.append((text[last:], False))
        return parts if parts else [(text, False)]

    def _parse_inline_code(self, text):
        """[İYİLEŞTİRME 18] `kod` sözdizimi ayrıştırma"""
        parts = []
        code_re = re.compile(r'`([^`]+)`')
        last = 0
        for m in code_re.finditer(text):
            if m.start() > last:
                parts.append((text[last:m.start()], "normal"))
            parts.append((m.group(1), "code"))
            last = m.end()
        if last < len(text):
            parts.append((text[last:], "normal"))
        return parts if parts else [(text, "normal")]

    def _append_text_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            grouped   = self._should_group(item.sender, item.ts)
            tag       = self._tag_for_item(item.item_id)
            start_idx = self.chat_box.index(tk.END)
            if not grouped:
                self._insert_avatar_header(item.sender, item.ts)

            # [İYİLEŞTİRME 17] Reply quote
            if item.reply_to and item.reply_sender:
                self.chat_box.insert(tk.END, f"  ↩ {item.reply_sender}: {item.reply_text[:60]}\n",
                                     ("reply_quote", tag))

            me       = self.username_var.get().strip()
            base_tag = "msg_cont" if grouped else "msg"

            # [İYİLEŞTİRME 18] Inline code parse
            inline_parts = self._parse_inline_code(item.text)
            for part_text, part_type in inline_parts:
                if part_type == "code":
                    self.chat_box.insert(tk.END, part_text, ("code_inline", tag))
                else:
                    url_parts = self._auto_linkify(part_text)
                    for segment, is_link in url_parts:
                        if f"@{me}" in segment:
                            segs = segment.split(f"@{me}")
                            for i, seg in enumerate(segs):
                                if seg:
                                    self.chat_box.insert(tk.END, seg, (base_tag, tag))
                                if i < len(segs) - 1:
                                    self.chat_box.insert(tk.END, f"@{me}", ("mention", tag))
                        else:
                            self.chat_box.insert(tk.END, segment,
                                                 ("link" if is_link else base_tag, tag))

            # Düzenlendi işareti
            if item.edited:
                self.chat_box.insert(tk.END, "  (düzenlendi)", ("msg_edited", tag))

            self.chat_box.insert(tk.END, "\n")

            # Tepkiler
            if item.reactions:
                react_text = "  "
                for em, users in item.reactions.items():
                    if users:
                        react_text += f" {em} {len(users)}"
                if react_text.strip():
                    self.chat_box.insert(tk.END, react_text + "\n", "time")

            # Sabitlendi işareti
            if item.pinned:
                self.chat_box.insert(tk.END, "  📌 sabitlendi\n", "pinned_mark")

            self._msg_line_map[item.item_id] = start_idx
            self._last_chat_sender = item.sender
            self._last_chat_ts     = item.ts
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    def _append_image_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            grouped = self._should_group(item.sender, item.ts)
            if not grouped:
                self._insert_avatar_header(item.sender, item.ts)
            tag = self._tag_for_item(item.item_id)
            try:
                raw   = base64.b64decode(item.image_b64.encode("ascii"))
                img   = Image.open(io.BytesIO(raw))
                img.thumbnail((480, 360))
                photo = ImageTk.PhotoImage(img)
                self.image_refs.append(photo)
                # Tıklanabilir resim (tam ekran)
                img_lbl = tk.Label(self.chat_box, image=photo, bg=BG, cursor="hand2")
                img_lbl.image = photo
                img_lbl.bind("<Button-1>",
                             lambda e, b=item.image_b64, n=item.image_name:
                             self._show_image_fullscreen(b, n))
                self.embed_refs.append(img_lbl)
                self.chat_box.window_create(tk.END, window=img_lbl, padx=60, pady=4)
                self.chat_box.insert(tk.END, "\n")
                # Küçük bilgi
                self.chat_box.insert(tk.END, f"  {item.image_name}\n", ("time", tag))
            except Exception:
                self.chat_box.insert(tk.END, f"  [Fotoğraf: {item.image_name}]\n", "warn")
            self._last_chat_sender = item.sender
            self._last_chat_ts     = item.ts
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    # [İYİLEŞTİRME 25] Tam ekran resim görüntüleyici
    def _show_image_fullscreen(self, b64, name):
        try:
            raw = base64.b64decode(b64.encode("ascii"))
            img = Image.open(io.BytesIO(raw))
        except Exception:
            return
        win = tk.Toplevel(self.root)
        win.title(f"🖼️  {name}")
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        max_w, max_h = int(sw * 0.85), int(sh * 0.85)
        win.geometry(f"{max_w}x{max_h}+{(sw-max_w)//2}+{(sh-max_h)//2}")
        win.configure(bg=PANEL_3)
        win.attributes("-topmost", True)

        # Toolbar
        tb = tk.Frame(win, bg=PANEL_3, height=44)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)
        tk.Label(tb, text=f"  🖼️  {name}", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=12, pady=12)

        def save_img():
            path = filedialog.asksaveasfilename(initialfile=name,
                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("Tümü", "*.*")])
            if path:
                img.save(path)
                self._system_message(f"✅ Resim kaydedildi: {os.path.basename(path)}", SUCCESS)

        tk.Button(tb, text="⬇ Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
                  activebackground=self.theme_accent, command=save_img).pack(side=tk.RIGHT, padx=8, pady=6)
        close_b = tk.Label(tb, text="✕  Kapat", bg=PANEL_3, fg=MUTED,
                           font=("Segoe UI", 9), cursor="hand2", padx=10)
        close_b.pack(side=tk.RIGHT, pady=12)
        self._hover(close_b, MUTED, TEXT)
        close_b.bind("<Button-1>", lambda e: win.destroy())

        canvas = tk.Canvas(win, bg=PANEL_3, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        def render_image(event=None):
            cw = canvas.winfo_width() or max_w
            ch = canvas.winfo_height() or max_h - 44
            display = img.copy()
            display.thumbnail((cw, ch), Image.LANCZOS)
            photo = ImageTk.PhotoImage(display)
            canvas._photo = photo
            canvas.delete("all")
            canvas.create_image(cw//2, ch//2, anchor="center", image=photo)

        win.bind("<Configure>", render_image)
        win.after(50, render_image)
        win.bind("<Escape>", lambda e: win.destroy())

    def _append_audio_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            grouped = self._should_group(item.sender, item.ts)
            if not grouped:
                self._insert_avatar_header(item.sender, item.ts)
            tag = self._tag_for_item(item.item_id)

            # [İYİLEŞTİRME 26] Gelişmiş ses player widget
            player_f = tk.Frame(self.chat_box, bg=PANEL_2, padx=10, pady=8)
            waveform_lbl = tk.Label(player_f, text="▬▬▬▬▬▬▬▬▬▬▬▬",
                                     bg=PANEL_2, fg=MUTED_2, font=("Segoe UI", 8))
            waveform_lbl.pack(side=tk.LEFT, padx=(0, 8))

            dur_str = f"{item.audio_sec:.1f}s" if item.audio_sec else ""
            is_playing = [False]

            def toggle_play(btn=None, it=item, wv=waveform_lbl):
                if is_playing[0]:
                    try:
                        sd.stop()
                    except Exception:
                        pass
                    is_playing[0] = False
                    play_btn.config(text="  ▶  Dinle  ")
                    wv.config(fg=MUTED_2)
                else:
                    is_playing[0] = True
                    play_btn.config(text="  ■  Durdur  ")
                    wv.config(fg=self.theme_accent)
                    def worker():
                        self._play_audio_worker(it)
                        is_playing[0] = False
                        try:
                            play_btn.config(text="  ▶  Dinle  ")
                            wv.config(fg=MUTED_2)
                        except Exception:
                            pass
                    threading.Thread(target=worker, daemon=True).start()

            play_btn = tk.Button(
                player_f, text="  ▶  Dinle  ",
                bg=ACCENT_S, fg="white", bd=0,
                activebackground=self.theme_accent, activeforeground="white",
                font=("Segoe UI", 10), padx=10, pady=5, cursor="hand2",
                command=toggle_play
            )
            play_btn.pack(side=tk.LEFT)

            if dur_str:
                tk.Label(player_f, text=f"  {dur_str}",
                         bg=PANEL_2, fg=MUTED, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

            self.embed_refs.append(player_f)
            self.chat_box.window_create(tk.END, window=player_f, padx=62, pady=2)
            self.chat_box.insert(tk.END, "\n")
            self._last_chat_sender = item.sender
            self._last_chat_ts     = item.ts
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    def _append_file_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            grouped = self._should_group(item.sender, item.ts)
            if not grouped:
                self._insert_avatar_header(item.sender, item.ts)
            tag      = self._tag_for_item(item.item_id)
            ext      = os.path.splitext(item.file_name)[1].lower().lstrip(".")
            ext_icon = FILE_ICONS.get(ext, "📎")
            size_str = _fmt_filesize(item.file_size)
            lang     = _detect_lang(item.file_name)

            file_f = tk.Frame(self.chat_box, bg=PANEL_2, padx=10, pady=8)
            info_f = tk.Frame(file_f, bg=PANEL_2)
            info_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tk.Label(info_f, text=f"{ext_icon}  {item.file_name}", bg=PANEL_2, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w")
            tk.Label(info_f, text=f"{size_str}  ·  {lang}", bg=PANEL_2, fg=MUTED,
                     font=("Segoe UI", 8), anchor="w").pack(anchor="w")

            btns = tk.Frame(file_f, bg=PANEL_2)
            btns.pack(side=tk.RIGHT, padx=(12, 0))
            tk.Button(
                btns, text="⬇ İndir",
                bg="#1e4d2b", fg="#3fb950", bd=0,
                activebackground="#2a6b3c", activeforeground="white",
                font=("Segoe UI", 9), padx=10, pady=5, cursor="hand2",
                command=lambda it=item: self._save_received_file(it)
            ).pack(side=tk.LEFT, padx=2)

            # [İYİLEŞTİRME 27] Metin dosyalarını önizle
            if ext in ("txt", "py", "json", "csv", "md", "html", "xml", "js", "ts"):
                tk.Button(
                    btns, text="👁 Önizle",
                    bg=PANEL_3, fg=MUTED, bd=0,
                    activebackground=HOVER,
                    font=("Segoe UI", 9), padx=10, pady=5, cursor="hand2",
                    command=lambda it=item: self._preview_file(it)
                ).pack(side=tk.LEFT, padx=2)

            self.embed_refs.append(file_f)
            self.chat_box.window_create(tk.END, window=file_f, padx=62, pady=2)
            self.chat_box.insert(tk.END, "\n")
            self._last_chat_sender = item.sender
            self._last_chat_ts     = item.ts
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    # [İYİLEŞTİRME 27] Dosya önizleme
    def _preview_file(self, item: ChatItem):
        try:
            raw  = base64.b64decode(item.file_b64.encode("ascii"))
            text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            messagebox.showerror("Önizleme Hatası", str(e))
            return

        win = tk.Toplevel(self.root)
        win.title(f"👁️  {item.file_name}  —  Önizleme")
        win.geometry("700x520")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tb = tk.Frame(win, bg=PANEL_3, height=44)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)
        tk.Label(tb, text=f"  👁️  {item.file_name}  ({_fmt_filesize(item.file_size)})",
                 bg=PANEL_3, fg=TEXT, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=12, pady=12)
        tk.Button(tb, text="⬇ Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
                  activebackground=self.theme_accent,
                  command=lambda: self._save_received_file(item)).pack(side=tk.RIGHT, padx=8, pady=6)

        st = scrolledtext.ScrolledText(win, bg=PANEL_3, fg=TEXT_2,
                                        font=("Courier New", 10), bd=0, wrap=tk.NONE,
                                        highlightthickness=0)
        st.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        st.insert("1.0", text[:50000])
        st.config(state=tk.DISABLED)

    def _system_message(self, text: str, color: str = MUTED):
        self.chat_box.config(state=tk.NORMAL)
        try:
            tag_map = {MUTED: "sys", WARN: "warn", DANGER: "danger",
                       SUCCESS: "success_msg", GOLD: "warn", ACCENT: "sys",
                       ACCENT_2: "success_msg", self.theme_accent: "sys"}
            tag     = tag_map.get(color, "sys")
            self.chat_box.insert(tk.END, f"  —  {text}\n", tag)
            self.chat_box.tag_configure(tag, foreground=color)
            self.chat_box.see(tk.END)
            self._last_chat_sender = ""
            self._last_chat_ts     = 0.0
        finally:
            self.chat_box.config(state=tk.DISABLED)

    # ==================== SIDEBAR GÜNCELLEME ====================
    def _refresh_member_list(self):
        q   = self.msg_search_var.get().strip().lower()
        self.users_list.delete(0, tk.END)
        if not self.current_room:
            return
        now   = time.time()
        users = self.room_users.get(self.current_room, {})
        owner = self.room_owner.get(self.current_room, "")
        me    = self.username_var.get().strip()
        count = len([u for u in users if now - users[u] < STALE_USER_SEC])
        if hasattr(self, "member_count_lbl"):
            self.member_count_lbl.config(text=f"— {count}")

        if owner and (not q or q in owner.lower()):
            self.users_list.insert(tk.END, "  KURUCU")
            self.users_list.itemconfig(self.users_list.size()-1,
                fg=MUTED_2, selectbackground=PANEL, selectforeground=MUTED_2)
            suffix = "  (Sen)" if owner == me else ""
            note   = " 📝" if owner in self.user_notes else ""
            self.users_list.insert(tk.END, f"  👑 {owner}{suffix}{note}")
            self.users_list.itemconfig(self.users_list.size()-1, fg=GOLD, bg=PANEL)

        others   = sorted([u for u in users if u != owner], key=str.lower)
        filtered = [u for u in others if not q or q in u.lower()]
        if filtered:
            self.users_list.insert(tk.END, "  ÜYELER")
            self.users_list.itemconfig(self.users_list.size()-1,
                fg=MUTED_2, selectbackground=PANEL, selectforeground=MUTED_2)
            for user in filtered:
                ts_u   = users[user]
                online = (now - ts_u) < STALE_USER_SEC
                dot    = STATUS_ICONS["online"] if online else STATUS_ICONS["offline"]
                color  = STATUS_COLORS["online"] if online else STATUS_COLORS["offline"]
                suffix = "  (Sen)" if user == me else ""
                note   = " 📝" if user in self.user_notes else ""
                self.users_list.insert(tk.END, f"  {dot} {user}{suffix}{note}")
                self.users_list.itemconfig(self.users_list.size()-1,
                    fg=color if online else MUTED, bg=PANEL)

    def _refresh_sidebar(self, filter_q=""):
        self.rooms_list.delete(0, tk.END)
        now   = time.time()
        rooms = sorted(
            [r for r, seen in self.known_rooms.items() if now - seen <= STALE_ROOM_SEC],
            key=str.lower
        )
        if filter_q:
            rooms = [r for r in rooms if filter_q in r.lower()]

        for room in rooms:
            unread   = self._unread_counts.get(room, 0)
            mentions = self._mention_counts.get(room, 0)
            if mentions > 0 and room != self.current_room:
                badge = f" (@{mentions})"
            elif unread > 0 and room != self.current_room:
                badge = f" ({unread})"
            else:
                badge = ""
            self.rooms_list.insert(tk.END, f"  # {room}{badge}")
            last = self.rooms_list.size() - 1
            if room == self.current_room:
                self.rooms_list.itemconfig(last, fg=TEXT, bg=HOVER)
            else:
                fg = PINK if mentions > 0 else (WARN if unread > 0 else MUTED)
                self.rooms_list.itemconfig(last, fg=fg, bg=PANEL_3)

        self._refresh_member_list()

        if hasattr(self, "user_name_lbl"):
            self.user_name_lbl.config(text=self.username_var.get().strip())

    def _on_room_click(self, event):
        idx = self.rooms_list.nearest(event.y)
        if idx < 0 or idx >= self.rooms_list.size():
            return
        raw  = self.rooms_list.get(idx).strip()
        room = re.sub(r'\s*[\(@][^)]*\)\s*$', '', raw.lstrip("#").strip())
        if room and room != self.current_room:
            self.join_room(room)

    # ==================== KULLANICI İŞLEMLERİ ====================
    def _selected_user_from_list(self):
        try:
            idx = self.users_list.curselection()
            if not idx:
                return None
            text = self.users_list.get(idx[0]).strip()
            for prefix in ("👑 ", "👤 ", "● ", "○ ", "◐ ", "⊘ "):
                if text.startswith(prefix):
                    text = text[len(prefix):].strip()
            if text.endswith("  (Sen)"):
                text = text[:-7].strip()
            text = text.replace(" 📝", "")
            return text if text not in ("KURUCU", "ÜYELER") else None
        except Exception:
            return None

    def _select_user(self, _event=None):
        self.selected_user = self._selected_user_from_list()

    def _show_user_menu(self, event):
        self.users_list.selection_clear(0, tk.END)
        idx = self.users_list.nearest(event.y)
        if idx < 0 or idx >= self.users_list.size():
            return
        self.users_list.selection_set(idx)
        self.users_list.activate(idx)
        self.selected_user = self._selected_user_from_list()
        if not self.selected_user:
            return
        is_owner = self._is_owner(self.current_room)
        me       = self.username_var.get().strip()
        can_mod  = is_owner and self.selected_user != me
        try:
            self.user_menu.entryconfig(1, state=tk.NORMAL if can_mod else tk.DISABLED)
            self.user_menu.entryconfig(2, state=tk.NORMAL if can_mod else tk.DISABLED)
        except tk.TclError:
            pass
        self.user_menu.tk_popup(event.x_root, event.y_root)

    def _mention_user(self):
        user = self.selected_user or self._selected_user_from_list()
        if not user:
            return
        self.msg_entry.focus_set()
        self.msg_entry.insert(tk.END, f"@{user} ")

    # [İYİLEŞTİRME 14] Kullanıcı notu ekleme
    def _add_user_note(self):
        user = self.selected_user or self._selected_user_from_list()
        if not user:
            return
        win = tk.Toplevel(self.root)
        win.title(f"{user} — Not")
        win.geometry("400x200")
        win.configure(bg=PANEL)
        win.attributes("-topmost", True)

        tk.Label(win, text=f"📝  {user} için not:", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(16, 4))
        txt = tk.Text(win, bg=INPUT, fg=TEXT, insertbackground=TEXT,
                      bd=0, font=("Segoe UI", 10), height=4, wrap=tk.WORD)
        txt.pack(fill=tk.X, padx=20, pady=(0, 8))
        existing = self.user_notes.get(user, "")
        txt.insert("1.0", existing)
        txt.focus_set()

        def save():
            note = txt.get("1.0", tk.END).strip()
            if note:
                self.user_notes[user] = note
            else:
                self.user_notes.pop(user, None)
            self._save_config()
            win.destroy()
            self._refresh_member_list()

        btn_row = tk.Frame(win, bg=PANEL)
        btn_row.pack(fill=tk.X, padx=20, pady=4)
        tk.Button(btn_row, text="Kaydet", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 10, "bold"), padx=18, pady=6,
                  cursor="hand2", activebackground=self.theme_accent, command=save
                  ).pack(side=tk.RIGHT)
        tk.Button(btn_row, text="İptal", bg=PANEL_2, fg=MUTED,
                  bd=0, font=("Segoe UI", 10), padx=14, pady=6,
                  cursor="hand2", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _show_selected_user_info(self):
        user = self.selected_user or self._selected_user_from_list()
        if not user or not self.current_room:
            return
        msgs      = [x for x in list(self.room_history[self.current_room]) if x.sender == user]
        last_seen = self.room_users[self.current_room].get(user)
        online    = last_seen and time.time() - last_seen < STALE_USER_SEC
        is_owner  = self.room_owner.get(self.current_room) == user

        win = tk.Toplevel(self.root)
        win.title(f"{user} — Profil")
        win.geometry("360x380")
        win.configure(bg=PANEL)
        win.resizable(False, False)
        win.attributes("-topmost", True)

        tk.Frame(win, bg=self.theme_accent, height=3).pack(fill=tk.X)

        av  = self._get_avatar_image(user, 72)
        self.avatar_refs.append(av)
        av_lbl = tk.Label(win, image=av, bg=PANEL)
        av_lbl.image = av
        av_lbl.pack(pady=(24, 8))

        tk.Label(win, text=user, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack()
        if is_owner:
            tk.Label(win, text="👑 Oda Kurucusu", bg=PANEL, fg=GOLD,
                     font=("Segoe UI", 9)).pack(pady=2)
        status_txt = "🟢 Çevrimiçi" if online else "⚫ Çevrimdışı"
        status_col = SUCCESS if online else MUTED
        tk.Label(win, text=status_txt, bg=PANEL, fg=status_col,
                 font=("Segoe UI", 10)).pack(pady=2)

        # Kullanıcı notu varsa göster
        note = self.user_notes.get(user)
        if note:
            note_f = tk.Frame(win, bg=PANEL_2)
            note_f.pack(fill=tk.X, padx=24, pady=6)
            tk.Label(note_f, text=f"📝  {note[:80]}", bg=PANEL_2, fg=MUTED,
                     font=("Segoe UI", 9, "italic"), anchor="w", wraplength=280).pack(
                fill=tk.X, padx=10, pady=6)

        info_f = tk.Frame(win, bg=PANEL_2)
        info_f.pack(fill=tk.X, padx=24, pady=6)
        msg_count  = len([m for m in msgs if m.kind == "MSG"])
        img_count  = len([m for m in msgs if m.kind == "IMG"])
        tk.Label(info_f, text=f"  💬 {msg_count} mesaj  ·  🖼️ {img_count} fotoğraf",
                 bg=PANEL_2, fg=TEXT_2, font=("Segoe UI", 10), anchor="w").pack(fill=tk.X, pady=6)
        if last_seen:
            ts_str = time.strftime("%d.%m.%Y %H:%M", time.localtime(last_seen))
            tk.Label(info_f, text=f"  🕐 Son görülme: {ts_str}", bg=PANEL_2, fg=MUTED,
                     font=("Segoe UI", 9), anchor="w").pack(fill=tk.X, pady=(0, 6))

        btn_row = tk.Frame(win, bg=PANEL)
        btn_row.pack(pady=10)
        tk.Button(btn_row, text="💬 Bahset", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 9), padx=14, pady=6, cursor="hand2",
                  activebackground=self.theme_accent,
                  command=lambda: (self._mention_user(), win.destroy())).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text="Kapat", bg=PANEL_3, fg=MUTED,
                  bd=0, font=("Segoe UI", 9), padx=14, pady=6,
                  cursor="hand2", command=win.destroy).pack(side=tk.LEFT, padx=4)

    def _ban_user(self, user):
        if not user or not self.current_room or user == self.username_var.get().strip():
            return
        if not self._is_owner(self.current_room):
            messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
            return
        self.banned_users[self.current_room].add(user)
        self._purge_user_messages(self.current_room, user)
        self._send_packet(self._build_packet("BAN", {"target_user": user}, target=user))
        self._send_packet(self._build_packet("BAN", {"target_user": user}))
        self._system_message(f"🔨 {user} banlandı.", DANGER)

    def _ban_selected_user_cmd(self):
        user = self.selected_user or self._selected_user_from_list()
        if user and messagebox.askyesno("Banla", f"⚠️  {user} bu odadan banlansın mı?",
                                        icon="warning"):
            self._ban_user(user)

    def _purge_user_messages_cmd(self, user):
        if not user or not self.current_room or user == self.username_var.get().strip():
            return
        if not self._is_owner(self.current_room):
            messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
            return
        self._purge_user_messages(self.current_room, user)
        self._send_packet(self._build_packet("PURGE", {"target_user": user}))
        self._system_message(f"🧹 {user} mesajları silindi.", WARN)

    def _purge_selected_user_messages(self):
        user = self.selected_user or self._selected_user_from_list()
        if user and messagebox.askyesno("Temizle", f"{user} tüm mesajları silinsin mi?"):
            self._purge_user_messages_cmd(user)

    def _copy_selected_user_name(self):
        user = self.selected_user or self._selected_user_from_list()
        if user:
            self.root.clipboard_clear()
            self.root.clipboard_append(user)

    def clear_room_history(self):
        if not self.current_room:
            return
        if not self._is_owner(self.current_room):
            messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
            return
        if not messagebox.askyesno("Temizle", "Tüm sohbet geçmişi silinsin mi?", icon="warning"):
            return
        self.room_history[self.current_room].clear()
        self._clear_chat()
        self._system_message("Tüm geçmiş temizlendi.", DANGER)
        self._send_packet(self._build_packet("CLEAR", {"all": True}))

    def _purge_user_messages(self, room, user):
        if not room or not user:
            return
        kept = deque([x for x in self.room_history[room] if x.sender != user], maxlen=MAX_HISTORY)
        self.room_history[room] = kept
        self._render_history(room)

    def _is_owner(self, room, sender=None):
        if not room:
            return False
        owner  = self.room_owner.get(room)
        sender = sender or self.username_var.get().strip()
        return bool(owner and owner == sender)

    def _tick_ui(self):
        if not self.running:
            return
        self._refresh_sidebar()
        self._update_typing_indicator(self.current_room)
        self.root.after(UI_REFRESH_MS, self._tick_ui)

    # [İYİLEŞTİRME 28] Hızlı oda değiştirici (Ctrl+K)
    def _quick_room_switcher(self):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=PANEL_2)
        w, h = 380, 320
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win.geometry(f"{w}x{h}+{(sw-w)//2}+{sh//4}")

        tk.Label(win, text="  ⚡  Kanala hızlı geç  (Ctrl+K)",
                 bg=PANEL_2, fg=MUTED_2, font=("Segoe UI", 9)).pack(fill=tk.X, padx=10, pady=6)

        search_f = tk.Frame(win, bg=INPUT)
        search_f.pack(fill=tk.X, padx=10)
        entry_var = tk.StringVar()
        entry = tk.Entry(search_f, textvariable=entry_var, bg=INPUT, fg=TEXT,
                         insertbackground=TEXT, bd=0, font=("Segoe UI", 13), relief=tk.FLAT)
        entry.pack(fill=tk.X, padx=8, ipady=12)
        entry.focus_set()

        lb = tk.Listbox(win, bg=PANEL_2, fg=TEXT, bd=0, highlightthickness=0,
                        selectbackground="#1f3050", selectforeground=TEXT,
                        activestyle="none", font=("Segoe UI", 11), relief=tk.FLAT)
        lb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tk.Label(win, text="  Enter: Geç  ·  Esc: Kapat",
                 bg=PANEL_2, fg=MUTED_2, font=("Segoe UI", 8)).pack(fill=tk.X, padx=10, pady=4)

        def populate(q=""):
            lb.delete(0, tk.END)
            now   = time.time()
            rooms = sorted([r for r, t in self.known_rooms.items()
                            if now - t <= STALE_ROOM_SEC], key=str.lower)
            for r in rooms:
                if not q or q.lower() in r.lower():
                    prefix = "● " if r == self.current_room else "  "
                    lb.insert(tk.END, f"{prefix}# {r}")
            if lb.size() > 0:
                lb.selection_set(0)

        populate()
        entry_var.trace_add("write", lambda *a: populate(entry_var.get()))

        def go(event=None):
            sel = lb.curselection()
            if not sel:
                q = entry_var.get().strip()
                if q:
                    win.destroy()
                    self.join_room(q)
                return
            raw  = lb.get(sel[0]).strip()
            room = re.sub(r'^[●\s#]+', '', raw).strip()
            if room:
                win.destroy()
                self.join_room(room)

        def nav(event):
            sel = lb.curselection()
            cur = sel[0] if sel else -1
            if event.keysym == "Down" and cur < lb.size() - 1:
                lb.selection_clear(0, tk.END)
                lb.selection_set(cur + 1)
            elif event.keysym == "Up" and cur > 0:
                lb.selection_clear(0, tk.END)
                lb.selection_set(cur - 1)

        entry.bind("<Return>", go)
        entry.bind("<Escape>", lambda e: win.destroy())
        entry.bind("<Down>",   nav)
        entry.bind("<Up>",     nav)
        lb.bind("<ButtonRelease-1>", go)
        win.bind("<FocusOut>", lambda e: win.destroy() if win.winfo_exists() else None)

    # ==================== ODA YÖNETİMİ ====================
    def _fix_username(self, base_name: str, room: str) -> str:
        users_in_room = self.room_users.get(room, {})
        me = self.username_var.get().strip()
        if base_name == me and base_name in users_in_room:
            ts = users_in_room[base_name]
            if time.time() - ts < STALE_USER_SEC:
                return base_name
        if base_name not in users_in_room:
            return base_name
        m = re.match(r'^(.*?)_(\d+)$', base_name)
        if m:
            stem = m.group(1)
            num  = int(m.group(2)) + 1
        else:
            stem = base_name
            num  = 1
        candidate = f"{stem}_{num}"
        while candidate in users_in_room:
            num += 1
            candidate = f"{stem}_{num}"
        return candidate

    def _join_from_entry(self):
        room = self.room_entry_var.get().strip()
        if room:
            self.join_room(room)

    def join_room(self, room_name: str):
        room_name = room_name.strip()
        username  = self.username_var.get().strip()
        if not room_name or not username:
            if not username:
                messagebox.showwarning("Eksik", "Kullanıcı adı boş olamaz.")
            return
        username = self._fix_username(username, room_name)
        self.username_var.set(username)
        if self.current_room and self.current_room != room_name:
            self._send_packet(self._build_packet("PART", {"reason": "switch"}, room=self.current_room))

        self.current_room = room_name
        self.status_var.set(f"#{room_name}")
        self.chat_title.config(text=room_name)
        self.chat_subtitle.config(text="Geçmiş yükleniyor…")
        self._toggle_inputs(True)
        self.msg_entry.focus_set()
        self._unread_counts[room_name]  = 0
        self._mention_counts[room_name] = 0

        now = time.time()
        self.known_rooms[room_name]               = now
        self.room_users[room_name][username]      = now
        self.room_join_times[room_name][username] = now
        self.room_owner.pop(room_name, None)
        self._recalculate_room_owner(room_name)
        self._clear_chat()
        self._render_history(room_name)
        self._system_message(f"#{room_name} kanalına katıldınız. 👋", SUCCESS)
        self._send_packet(self._build_packet("JOIN", {"room": room_name}))
        self._send_packet(self._build_packet("HISTORY_REQ", {"need": True}, target=username))
        self._refresh_sidebar()
        self._play_join_sound()

        me = self.username_var.get().strip()
        if me in self.avatar_b64_map:
            av = self.avatar_b64_map[me]
            if len(av) <= 28000:
                self._send_packet(self._build_packet("AVATAR", {"b64": av}))

    def leave_room(self):
        if not self.current_room:
            return
        old = self.current_room
        self._stop_screen_share(silent=True)
        self._cancel_reply()
        self._send_packet(self._build_packet("PART", {"reason": "leave"}, room=old))
        self.current_room = ""
        self.status_var.set("Bağlı değil")
        self.chat_title.config(text="kanal seçilmedi")
        self.chat_subtitle.config(text="Bir kanala katılın")
        self.screen_status_var.set("")
        self._set_screen_preview(None, sender=None)
        self._clear_entry()
        self._toggle_inputs(False)
        self._clear_chat()
        self._system_message(f"#{old} kanalından ayrıldınız.", WARN)
        self._refresh_sidebar()

    # ==================== MESAJ GÖNDER ====================
    def send_message(self):
        text = self._get_entry_text().strip()
        if not text or not self.current_room:
            return
        if len(text) > MAX_MSG_LEN:
            messagebox.showwarning("Çok uzun", f"Mesaj {MAX_MSG_LEN} karakterden uzun olamaz.")
            return
        if text.startswith("/"):
            self._handle_commands(text)
            self._clear_entry()
            return

        # Geçmişe ekle
        if not self._sent_history or self._sent_history[-1] != text:
            self._sent_history.append(text)
            if len(self._sent_history) > 50:
                self._sent_history.pop(0)
        self._sent_hist_idx = -1

        user      = self.username_var.get().strip() or "Anon"
        packet_id = str(uuid.uuid4())
        self.seen_packet_ids.add(packet_id)

        # Reply bilgisi
        reply_to = reply_sender = reply_text = ""
        if self._reply_item:
            reply_to     = self._reply_item.item_id
            reply_sender = self._reply_item.sender
            if self._reply_item.kind == "MSG":
                reply_text = self._reply_item.text[:60]
            elif self._reply_item.kind == "IMG":
                reply_text = "🖼️ Fotoğraf"
            elif self._reply_item.kind == "AUDIO":
                reply_text = "🎤 Ses mesajı"
            elif self._reply_item.kind == "FILE":
                reply_text = f"📎 {self._reply_item.file_name}"

        item = ChatItem(item_id=packet_id, kind="MSG", sender=user,
                        ts=time.time(), room=self.current_room, text=text,
                        reply_to=reply_to, reply_sender=reply_sender, reply_text=reply_text)
        self.room_history[self.current_room].append(item)
        self._append_text_message(item)
        pkt_data = {"text": text}
        if reply_to:
            pkt_data.update({"reply_to": reply_to, "reply_sender": reply_sender,
                              "reply_text": reply_text})
        self._send_packet(self._build_packet("MSG", pkt_data, packet_id=packet_id))
        self._clear_entry()
        self.char_count_lbl.config(text="")
        self._cancel_reply()
        self._stats["sent"] += 1

    def _handle_commands(self, text):
        parts  = text.split(" ", 1)
        cmd    = parts[0].lower()
        target = parts[1].strip() if len(parts) > 1 else ""
        cmds = {
            "/leave":   self.leave_room,
            "/clear":   self.clear_room_history,
            "/screen":  self._toggle_screen_share,
            "/help":    self._show_help,
            "/stats":   self._show_stats_window,
            "/rooms":   self._show_all_rooms,
        }
        if cmd in cmds:
            cmds[cmd]()
        elif cmd == "/ban" and target:
            self._ban_user(target)
        elif cmd == "/purge" and target:
            self._purge_user_messages_cmd(target)
        elif cmd == "/nick" and target:
            old = self.username_var.get().strip()
            self.username_var.set(target)
            if hasattr(self, "user_name_lbl"):
                self.user_name_lbl.config(text=target)
            self._system_message(f"✅ Kullanıcı adın '{target}' olarak değiştirildi.", SUCCESS)
        elif cmd == "/me" and target:
            user      = self.username_var.get().strip()
            packet_id = str(uuid.uuid4())
            self.seen_packet_ids.add(packet_id)
            text2     = f"* {user} {target}"
            item = ChatItem(item_id=packet_id, kind="MSG", sender=user,
                            ts=time.time(), room=self.current_room, text=text2)
            self.room_history[self.current_room].append(item)
            self._append_text_message(item)
            self._send_packet(self._build_packet("MSG", {"text": text2}, packet_id=packet_id))
        elif cmd == "/topic" and target:
            if self._is_owner(self.current_room):
                self.room_topics[self.current_room] = target
                self.chat_subtitle.config(text=target)
                self._system_message(f"📝 Kanal konusu: {target}", ACCENT)
            else:
                self._system_message("Kanal konusunu yalnız kurucu değiştirebilir.", WARN)
        elif cmd == "/shrug":
            text2 = "¯\\_(ツ)_/¯"
            self.msg_entry.delete("1.0", tk.END)
            self.msg_entry.insert("1.0", text2)
        else:
            self._system_message(f"❌ Bilinmeyen komut: {cmd}  —  /help ile komutları görün", WARN)
            self._play_error_sound()

    def _show_help(self):
        help_text = (
            "📖 Komut listesi:\n"
            "  /leave         — Kanaldan ayrıl\n"
            "  /clear         — Geçmişi temizle (kurucu)\n"
            "  /screen        — Ekran paylaşımını aç/kapat\n"
            "  /ban <kişi>    — Banla (kurucu)\n"
            "  /purge <kişi>  — Mesajlarını sil (kurucu)\n"
            "  /nick <ad>     — Kullanıcı adını değiştir\n"
            "  /me <eylem>    — Eylem mesajı gönder\n"
            "  /topic <metin> — Kanal konusu ayarla (kurucu)\n"
            "  /shrug         — ¯\\_(ツ)_/¯\n"
            "  /stats         — İstatistikleri göster\n"
            "  /rooms         — Tüm odaları göster\n\n"
            "⌨️  Kısayollar:\n"
            "  ↑ / ↓          — Mesaj geçmişi\n"
            "  Ctrl+F         — Mesajlarda ara\n"
            "  Ctrl+K         — Hızlı oda değiştir\n"
            "  Ctrl+,         — Ayarlar\n"
            "  Tab            — @mention tamamla\n"
            "  Shift+Enter    — Yeni satır"
        )
        self._system_message(help_text, ACCENT)

    # [İYİLEŞTİRME 29] Tüm odaları göster
    def _show_all_rooms(self):
        now   = time.time()
        rooms = sorted([r for r, t in self.known_rooms.items()
                        if now - t <= STALE_ROOM_SEC], key=str.lower)
        if not rooms:
            self._system_message("Bilinen oda yok.", MUTED)
            return
        lines = ["📋 Bilinen odalar:"]
        for r in rooms:
            user_count = len([u for u, t in self.room_users.get(r, {}).items()
                               if now - t < STALE_USER_SEC])
            marker = " ← (şu an)" if r == self.current_room else ""
            lines.append(f"  # {r}  ({user_count} üye){marker}")
        self._system_message("\n".join(lines), ACCENT)

    # ==================== GÖRÜNTÜ ====================
    def send_image(self):
        if not self.current_room:
            return
        path = filedialog.askopenfilename(
            title="Fotoğraf seç",
            filetypes=[("Resimler", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Tümü", "*.*")])
        if not path:
            return
        try:
            payload = self._prepare_image(Image.open(path).convert("RGB"), os.path.basename(path))
            self._dispatch_image_payload(payload)
        except Exception as exc:
            messagebox.showerror("Resim Hatası", f"Fotoğraf hazırlanamadı:\n{exc}")

    def _paste_image(self, event=None):
        if not self.current_room:
            return
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                payload = self._prepare_image(img.convert("RGB"), f"Pano_{int(time.time())}.jpg")
                self._dispatch_image_payload(payload)
                self._system_message("📋 Panodaki resim gönderildi.", SUCCESS)
        except Exception:
            pass

    def _prepare_image(self, img, name):
        side, quality = MAX_IMAGE_SIDE, 78
        while True:
            working = img.copy()
            working.thumbnail((side, side))
            buf = io.BytesIO()
            working.save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            if len(b64) <= MAX_IMAGE_B64_LEN or (side <= 180 and quality <= 45):
                return {"name": name, "w": working.width, "h": working.height, "b64": b64}
            side    = max(160, side - 40)
            quality = max(40, quality - 8)

    def _dispatch_image_payload(self, payload):
        if len(payload["b64"]) > MAX_IMAGE_B64_LEN:
            messagebox.showwarning("Boyut", "Fotoğraf çok büyük, sıkıştırılamadı.")
            return
        user      = self.username_var.get().strip() or "Anon"
        packet_id = str(uuid.uuid4())
        self.seen_packet_ids.add(packet_id)
        item = ChatItem(item_id=packet_id, kind="IMG", sender=user,
                        ts=time.time(), room=self.current_room,
                        image_b64=payload["b64"], image_name=payload["name"])
        self.room_history[self.current_room].append(item)
        self._append_image_message(item)
        self._send_packet(self._build_packet("IMG", payload, packet_id=packet_id))
        self._stats["sent"] += 1

    # ==================== DOSYA GÖNDER ====================
    def send_file(self):
        if not self.current_room:
            return
        path = filedialog.askopenfilename(
            title="Dosya seç",
            filetypes=[("Desteklenen", "*.txt *.pdf *.zip *.json *.csv *.py *.html *.xml *.md *.docx *.xlsx *.js *.ts *.sh"),
                       ("Tümü", "*.*")])
        if not path:
            return
        try:
            file_bytes = open(path, "rb").read()
            if len(file_bytes) > MAX_FILE_BYTES:
                messagebox.showwarning("Boyut", f"Dosya çok büyük (max {MAX_FILE_BYTES//1024} KB).")
                return
            b64       = base64.b64encode(file_bytes).decode("ascii")
            fname     = os.path.basename(path)
            packet_id = str(uuid.uuid4())
            self.seen_packet_ids.add(packet_id)

            total = math.ceil(len(b64) / FILE_CHUNK_SIZE)
            user  = self.username_var.get().strip() or "Anon"

            for idx in range(total):
                chunk = b64[idx * FILE_CHUNK_SIZE:(idx + 1) * FILE_CHUNK_SIZE]
                self._send_packet(self._build_packet("FILE_CHUNK", {
                    "file_id": packet_id, "name": fname, "size": len(file_bytes),
                    "index": idx, "total": total, "chunk": chunk,
                }, packet_id=str(uuid.uuid4())))

            item = ChatItem(item_id=packet_id, kind="FILE", sender=user,
                            ts=time.time(), room=self.current_room,
                            file_b64=b64, file_name=fname, file_size=len(file_bytes))
            self.room_history[self.current_room].append(item)
            self._append_file_message(item)
            self._system_message(f"📎 {fname} gönderildi ({_fmt_filesize(len(file_bytes))}).", SUCCESS)
            self._stats["sent"] += 1
        except Exception as exc:
            messagebox.showerror("Dosya Hatası", f"Gönderilemedi:\n{exc}")

    def _save_received_file(self, item: ChatItem):
        path = filedialog.asksaveasfilename(
            initialfile=item.file_name,
            filetypes=[("Tümü", "*.*")])
        if not path:
            return
        try:
            raw = base64.b64decode(item.file_b64.encode("ascii"))
            with open(path, "wb") as f:
                f.write(raw)
            self._system_message(f"✅ {os.path.basename(path)} kaydedildi.", SUCCESS)
        except Exception as exc:
            messagebox.showerror("Kayıt Hatası", str(exc))

    # ==================== SES ====================
    def _start_audio_record(self, event=None):
        if not self.current_room:
            return
        if not AUDIO_AVAILABLE:
            messagebox.showinfo("Modül Eksik", "Ses için:\npip install sounddevice numpy")
            return
        if self.is_recording:
            return
        try:
            self.is_recording    = True
            self.audio_frames    = []
            self.record_start_ts = time.time()
            self.audio_status_var.set("🔴  Kayıt devam ediyor… (maks 30 sn, bırak = gönder)")
            self.mic_btn.config(fg=DANGER)
            self.audio_timer = self.root.after(30000, self._stop_audio_record)
            def callback(indata, frames, time_info, status):
                if self.is_recording:
                    self.audio_frames.append(indata.copy())
            self.audio_stream = sd.InputStream(
                samplerate=AUDIO_SR, channels=1, dtype="int16", callback=callback)
            self.audio_stream.start()
        except Exception as exc:
            self.is_recording = False
            self.audio_status_var.set("")
            self.mic_btn.config(fg=MUTED)
            messagebox.showerror("Ses kaydı", f"Başlatılamadı:\n{exc}")

    def _stop_audio_record(self, event=None):
        if not getattr(self, "is_recording", False):
            return
        if hasattr(self, "audio_timer"):
            self.root.after_cancel(self.audio_timer)
        self.is_recording = False
        self.mic_btn.config(fg=MUTED)
        self.audio_status_var.set("İşleniyor…")
        try:
            if getattr(self, "audio_stream", None):
                self.audio_stream.stop()
                self.audio_stream.close()
        except Exception:
            pass
        finally:
            self.audio_stream = None
        if not self.audio_frames:
            self.audio_status_var.set("")
            return
        try:
            audio    = np.concatenate(self.audio_frames, axis=0).reshape(-1).astype(np.int16)
            duration = len(audio) / AUDIO_SR
            if duration < AUDIO_MIN_SEC:
                self.audio_status_var.set("Kayıt çok kısa")
                self.root.after(1500, lambda: self.audio_status_var.set(""))
                return
            raw        = audio.tobytes()
            compressed = zlib.compress(raw, level=9)
            b64        = base64.b64encode(compressed).decode("ascii")
            if len(b64) > MAX_AUDIO_B64_LEN:
                messagebox.showwarning("Ses çok büyük", "Daha kısa bir ses gönder.")
                self.audio_status_var.set("")
                return
            user      = self.username_var.get().strip() or "Anon"
            packet_id = str(uuid.uuid4())
            self.seen_packet_ids.add(packet_id)
            payload = {"b64": b64, "sr": AUDIO_SR, "codec": "zlib_pcm16",
                       "duration": round(duration, 2),
                       "name": f"Ses_{int(time.time())}.audio"}
            item = ChatItem(item_id=packet_id, kind="AUDIO", sender=user,
                            ts=time.time(), room=self.current_room,
                            audio_b64=b64, audio_name=payload["name"],
                            audio_sr=AUDIO_SR, audio_codec="zlib_pcm16",
                            audio_sec=duration)
            raw_p = _encode_packet(self._build_packet("AUDIO", payload, packet_id=packet_id))
            if len(raw_p) > MAX_PACKET_BYTES:
                messagebox.showwarning("Ses çok büyük", "UDP sınırı aşıldı.")
                self.audio_status_var.set("")
                return
            self.room_history[self.current_room].append(item)
            self._append_audio_message(item)
            self.sock.sendto(raw_p, (BROADCAST_ADDR, PORT))
            self.audio_status_var.set(f"✓  {duration:.1f}s ses gönderildi")
            self.root.after(2000, lambda: self.audio_status_var.set(""))
            self._stats["sent"] += 1
        except Exception as exc:
            messagebox.showerror("Ses işleme hatası", f"Gönderilemedi:\n{exc}")
            self.audio_status_var.set("")

    def _play_audio_item(self, item: ChatItem):
        if not AUDIO_AVAILABLE:
            messagebox.showwarning("Ses yok", "sounddevice/numpy gerekli.")
            return
        threading.Thread(target=self._play_audio_worker, args=(item,), daemon=True).start()

    def _play_audio_worker(self, item: ChatItem):
        try:
            raw   = base64.b64decode(item.audio_b64.encode("ascii"))
            codec = (item.audio_codec or "zlib_pcm16").lower()
            if codec == "zlib_pcm16":
                raw = zlib.decompress(raw)
            audio = np.frombuffer(raw, dtype=np.int16)
            if audio.size == 0:
                raise ValueError("Boş ses verisi")
            sd.stop()
            sd.play(audio, samplerate=item.audio_sr or AUDIO_SR)
            sd.wait()
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror(
                "Oynatma Hatası", f"{item.sender}:\n{exc}"))

    # ==================== EKRAN PAYLAŞIMI ====================
    def _toggle_screen_share(self):
        if not self.current_room:
            return
        self._stop_screen_share() if self.screen_sharing else self._start_screen_share()

    def _start_screen_share(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("PIL eksik", "Pillow gerekli.")
            return
        if self.screen_sharing:
            return
        if (getattr(self, "current_screen_sender", None) and
                self.current_screen_sender != self.username_var.get().strip() and
                time.time() - getattr(self, "last_screen_ts", 0) < 4.0):
            if not messagebox.askyesno("Uyarı",
                f"{self.current_screen_sender} zaten paylaşıyor.\nYine de başlatmak istiyor musun?"):
                return
        self.screen_sharing = True
        self.screen_status_var.set("🔴  Ekran paylaşılıyor")
        if hasattr(self, "screen_icon"):
            self.screen_icon.config(text="🔴", fg=DANGER)
        self._system_message("🖥️ Ekran paylaşımı başlatıldı.", SUCCESS)
        self.screen_thread = threading.Thread(target=self._screen_share_loop, daemon=True)
        self.screen_thread.start()

    def _stop_screen_share(self, silent=False):
        if not self.screen_sharing:
            if hasattr(self, "screen_icon"):
                self.screen_icon.config(text="🖥️", fg=MUTED)
            return
        self.screen_sharing = False
        self.screen_status_var.set("")
        if hasattr(self, "screen_icon"):
            self.screen_icon.config(text="🖥️", fg=MUTED)
        if not silent:
            self._system_message("🖥️ Ekran paylaşımı durduruldu.", WARN)

    def _screen_share_loop(self):
        try:
            rf = Image.Resampling.NEAREST
        except Exception:
            rf = Image.NEAREST
        while self.running and self.screen_sharing:
            try:
                if not self.current_room:
                    time.sleep(SCREEN_SHARE_INTERVAL)
                    continue
                img = ImageGrab.grab()
                if img is None:
                    time.sleep(SCREEN_SHARE_INTERVAL)
                    continue
                working = img.convert("RGB")
                if max(working.width, working.height) > SCREEN_SHARE_MAX_SIDE:
                    working.thumbnail((SCREEN_SHARE_MAX_SIDE, SCREEN_SHARE_MAX_SIDE), rf)
                buf = io.BytesIO()
                working.save(buf, format="JPEG", quality=SCREEN_SHARE_JPEG_Q)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                if len(b64) > SCREEN_SHARE_MAX_B64:
                    smaller = img.convert("RGB")
                    smaller.thumbnail((max(480, SCREEN_SHARE_MAX_SIDE // 2),
                                       max(270, SCREEN_SHARE_MAX_SIDE // 2)), rf)
                    buf = io.BytesIO()
                    smaller.save(buf, format="JPEG", quality=max(18, SCREEN_SHARE_JPEG_Q - 10))
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                if len(b64) > SCREEN_SHARE_MAX_B64:
                    time.sleep(SCREEN_SHARE_INTERVAL)
                    continue
                frame_id = str(uuid.uuid4())
                total    = (len(b64) + SCREEN_SHARE_CHUNK - 1) // SCREEN_SHARE_CHUNK
                base_p   = {"frame_id": frame_id, "total": total,
                            "name": f"screen_{int(time.time())}.jpg",
                            "w": working.width, "h": working.height}
                for idx in range(total):
                    if not self.screen_sharing or not self.current_room:
                        break
                    chunk = b64[idx * SCREEN_SHARE_CHUNK:(idx + 1) * SCREEN_SHARE_CHUNK]
                    raw_p = _encode_packet(
                        self._build_packet("SCREEN", {**base_p, "index": idx, "chunk": chunk}))
                    if len(raw_p) <= 65507:
                        self.sock.sendto(raw_p, (BROADCAST_ADDR, PORT))
                time.sleep(SCREEN_SHARE_INTERVAL)
            except Exception as exc:
                self.root.after(0, lambda: self.screen_status_var.set(f"Ekran hatası"))
                time.sleep(SCREEN_SHARE_INTERVAL)

    def _handle_screen_packet(self, pkt, room, sender, data):
        frame_id = str(data.get("frame_id") or "").strip()
        if not frame_id:
            return
        total  = int(data.get("total") or 0)
        index  = int(data.get("index") or 0)
        chunk  = str(data.get("chunk") or "")
        width  = int(data.get("w") or 0)
        height = int(data.get("h") or 0)
        entry  = self.screen_buffers.get(frame_id)
        now    = time.time()
        if not entry:
            entry = {"sender": sender or "Anon", "room": room, "ts": now,
                     "total": max(total, 1), "width": width, "height": height, "chunks": {}}
            self.screen_buffers[frame_id] = entry
        entry["ts"] = now
        entry["sender"] = sender or entry.get("sender", "Anon")
        if total:  entry["total"]  = total
        if width:  entry["width"]  = width
        if height: entry["height"] = height
        entry["chunks"][index] = chunk
        if len(entry["chunks"]) >= entry["total"]:
            try:
                ordered = [entry["chunks"][i] for i in range(entry["total"])]
                threading.Thread(target=self._decode_screen_frame,
                                 args=(ordered, entry["sender"]), daemon=True).start()
            except KeyError:
                pass
            finally:
                self.screen_buffers.pop(frame_id, None)

    def _decode_screen_frame(self, chunks, sender):
        try:
            b64 = "".join(chunks)
            raw = base64.b64decode(b64.encode("ascii"))
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            self.root.after(0, self._set_screen_preview, img, sender)
        except Exception:
            pass

    def _set_screen_preview(self, img, sender):
        if img is None:
            self.screen_status_var.set("")
            self.screen_preview_photo = None
            if self.viewer_window and self.viewer_window.winfo_exists():
                self.viewer_window.destroy()
            self.viewer_window = None
            self.viewer_label  = None
            return
        self.last_screen_ts = time.time()
        if not self.viewer_window or not self.viewer_window.winfo_exists():
            self.viewer_window = tk.Toplevel(self.root)
            self.viewer_window.title(f"📡  {sender}  —  Ekran Yayını")
            self.viewer_window.geometry("1100x720")
            self.viewer_window.configure(bg=BG)

            toolbar = tk.Frame(self.viewer_window, bg=PANEL_3, height=44)
            toolbar.pack(fill=tk.X)
            toolbar.pack_propagate(False)
            tk.Label(toolbar, text=f"  📡  {sender} ekranını paylaşıyor",
                     bg=PANEL_3, fg=TEXT, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=12, pady=12)
            tk.Label(toolbar, text="🔴 CANLI", bg=PANEL_3, fg=DANGER,
                     font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            tk.Button(toolbar, text="✕ Kapat", bg=PANEL_3, fg=MUTED,
                      bd=0, font=("Segoe UI", 9), padx=10, pady=6, cursor="hand2",
                      command=lambda: self.viewer_window.destroy()).pack(side=tk.RIGHT, padx=8, pady=6)

            self.viewer_label = tk.Label(self.viewer_window, bg=BG)
            self.viewer_label.pack(fill=tk.BOTH, expand=True)

            def on_close():
                self.viewer_window.destroy()
                self.viewer_window = None
            self.viewer_window.protocol("WM_DELETE_WINDOW", on_close)

        win_w = self.viewer_window.winfo_width()
        win_h = self.viewer_window.winfo_height() - 44
        if win_w > 10 and win_h > 10:
            try:
                rf = Image.Resampling.LANCZOS
            except Exception:
                rf = Image.LANCZOS
            display_img = img.copy()
            display_img.thumbnail((win_w, win_h), rf)
        else:
            display_img = img
        photo = ImageTk.PhotoImage(display_img)
        self.screen_preview_photo = photo
        self.viewer_label.configure(image=photo)
        self.viewer_label.image = photo
        self.screen_status_var.set(f"📡  {sender} ekranı paylaşıyor")
        self.current_screen_sender = sender
        self.current_screen_ts     = time.time()

    def _prune_screen_buffers(self):
        if not self.screen_buffers:
            return
        now = time.time()
        for fid in list(self.screen_buffers):
            if now - self.screen_buffers[fid].get("ts", now) > SCREEN_BUFFER_TTL:
                self.screen_buffers.pop(fid, None)

    # ==================== AĞ ====================
    def _start_network(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(("", PORT))
            self.sock.settimeout(SOCK_TIMEOUT)
        except OSError as exc:
            messagebox.showerror("Ağ Hatası",
                f"UDP soketi başlatılamadı:\n{exc}\n\nPort {PORT} kullanımda olabilir.")
            raise SystemExit(1)
        threading.Thread(target=self._receiver_loop,  daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _build_packet(self, kind, data=None, *, target=None, room=None, packet_id=None):
        return {
            "v":      5,
            "id":     packet_id or str(uuid.uuid4()),
            "ts":     time.time(),
            "room":   room or self.current_room,
            "user":   self.username_var.get().strip(),
            "type":   kind,
            "target": target,
            "data":   data,
        }

    def _send_packet(self, packet: dict) -> bool:
        if not self.sock:
            return False
        try:
            raw = _encode_packet(packet)
            if len(raw) > 65507:
                return False
            self.sock.sendto(raw, (BROADCAST_ADDR, PORT))
            return True
        except Exception:
            self._stats["errors"] += 1
            return False

    def _receiver_loop(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(65507)
                try:
                    pkt = _decode_packet(data)
                except Exception:
                    self._stats["errors"] += 1
                    continue
                self._stats["recv"] += 1
                self.root.after(0, self._process_packet, pkt)
            except (socket.timeout,):
                continue
            except OSError:
                break
            except Exception:
                continue

    def _heartbeat_loop(self):
        while self.running:
            if self.current_room:
                me = self.username_var.get().strip()
                self.room_users[self.current_room][me] = time.time()
                ping_data = {"online": True, "status": self.user_status}
                if me in self.avatar_b64_map:
                    av = self.avatar_b64_map[me]
                    if len(av) <= 6000:
                        ping_data["avatar_b64"] = av
                self._send_packet(self._build_packet("PING", ping_data))
                if self.room_owner.get(self.current_room) == me:
                    self._send_packet(self._build_packet("OWNER", {"owner": me}))

            now = time.time()
            for room in list(self.room_users):
                users = self.room_users[room]
                for user in list(users):
                    if now - users[user] > STALE_USER_SEC:
                        users.pop(user, None)
                        self.room_join_times[room].pop(user, None)
                if (room != self.current_room and
                        room in self.known_rooms and
                        now - self.known_rooms[room] > STALE_ROOM_SEC):
                    self.known_rooms.pop(room, None)
                    self.room_owner.pop(room, None)
                    self.room_users.pop(room, None)
                    self.room_join_times.pop(room, None)
                    self.banned_users.pop(room, None)
                else:
                    self._recalculate_room_owner(room)

            if getattr(self, "viewer_window", None) and self.viewer_window.winfo_exists():
                if time.time() - getattr(self, "last_screen_ts", 0) > 4.0:
                    self.root.after(0, lambda: self._set_screen_preview(None, None))

            self._prune_screen_buffers()
            self.root.after(0, self._refresh_sidebar)
            time.sleep(HEARTBEAT_SEC)

    def _recalculate_room_owner(self, room):
        users = self.room_users.get(room, {})
        if not users:
            self.room_owner.pop(room, None)
            return None
        join_times = self.room_join_times.get(room, {})
        candidates = [(join_times.get(u, time.time()), u.lower(), u) for u in users]
        if candidates:
            candidates.sort()
            new_owner = candidates[0][2]
            self.room_owner[room] = new_owner
            return new_owner
        self.room_owner.pop(room, None)
        return None

    # ==================== PAKET İŞLE ====================
    def _process_packet(self, pkt: dict):
        if not isinstance(pkt, dict) or pkt.get("v") not in {3, 4, 5}:
            return
        kind      = str(pkt.get("type") or "").upper()
        packet_id = str(pkt.get("id") or "")
        room      = str(pkt.get("room") or "").strip()
        sender    = str(pkt.get("user") or "").strip()
        target    = str(pkt.get("target") or "").strip()
        data      = pkt.get("data") or {}

        if packet_id and packet_id in self.seen_packet_ids:
            return
        if sender and sender == self.username_var.get().strip() and \
                kind in {"MSG", "IMG", "JOIN", "PART", "PING", "AUDIO", "SCREEN", "AVATAR",
                         "FILE_CHUNK", "EDIT", "DELETE", "TYPING", "REACT"}:
            return
        if target and target != self.username_var.get().strip():
            return
        if room:
            self.known_rooms[room] = time.time()
        if sender and room:
            self.room_users[room][sender] = time.time()
            if sender not in self.room_join_times[room]:
                self.room_join_times[room][sender] = time.time()

        # AVATAR
        if kind == "AVATAR":
            b64 = str(data.get("b64") or "").strip()
            if b64 and sender:
                self.avatar_b64_map[sender] = b64
                for k in list(self.avatar_cache):
                    if k.startswith(f"{sender}_"):
                        del self.avatar_cache[k]
            return

        # OWNER
        if kind == "OWNER" and room:
            ann = str(data.get("owner") or sender or "").strip()
            if ann and ann in self.room_users.get(room, {}):
                self.room_owner[room] = ann
            self._refresh_sidebar()
            return

        # TYPING
        if kind == "TYPING" and sender and room:
            if room == self.current_room:
                self.typing_users[room][sender] = time.time()
                self._update_typing_indicator(room)
            return

        # PING
        if kind == "PING" and sender and room:
            av_b64 = str(data.get("avatar_b64") or "").strip()
            if av_b64 and sender not in self.avatar_b64_map:
                self.avatar_b64_map[sender] = av_b64
                for k in list(self.avatar_cache):
                    if k.startswith(f"{sender}_"):
                        del self.avatar_cache[k]

        # JOIN / PART / PING
        if kind in {"JOIN", "PART", "PING"} and room:
            if kind == "PART" and sender:
                self.room_users[room].pop(sender, None)
                self.room_join_times[room].pop(sender, None)
                if room == self.current_room and sender != self.username_var.get().strip():
                    self._system_message(f"◀  {sender} kanaldan ayrıldı.", WARN)
            if kind == "JOIN" and sender:
                if room == self.current_room and sender != self.username_var.get().strip():
                    self._system_message(f"▶  {sender} kanala katıldı.", SUCCESS)
                    self._play_join_sound()
            self._recalculate_room_owner(room)
            self._refresh_sidebar()
            return

        if room != self.current_room:
            return
        if sender in self.banned_users.get(room, set()) and \
                kind in {"MSG", "IMG", "AUDIO", "HISTORY", "SCREEN", "FILE_CHUNK", "EDIT",
                         "DELETE", "REACT"}:
            return

        # HISTORY_REQ
        if kind == "HISTORY_REQ":
            if room and self._is_owner(room):
                self._send_history_to(target)
            return

        # HISTORY
        if kind == "HISTORY":
            items = data if isinstance(data, list) else []
            for raw_item in items:
                if not isinstance(raw_item, dict):
                    continue
                item_id = str(raw_item.get("item_id") or raw_item.get("id") or "")
                if not item_id or item_id in self.seen_packet_ids:
                    continue
                if str(raw_item.get("sender") or "") == self.username_var.get().strip():
                    continue
                self.seen_packet_ids.add(item_id)
                item_kind = str(raw_item.get("kind") or "MSG").upper()
                ts        = float(raw_item.get("ts") or time.time())
                snd       = str(raw_item.get("sender") or "Anon")
                if item_kind == "IMG":
                    item = ChatItem(item_id=item_id, kind="IMG", sender=snd, ts=ts, room=room,
                                    image_b64=str(raw_item.get("image_b64") or ""),
                                    image_name=str(raw_item.get("image_name") or "image.jpg"))
                elif item_kind == "AUDIO":
                    item = ChatItem(item_id=item_id, kind="AUDIO", sender=snd, ts=ts, room=room,
                                    audio_b64=str(raw_item.get("audio_b64") or ""),
                                    audio_name=str(raw_item.get("audio_name") or "voice.audio"),
                                    audio_sr=int(raw_item.get("audio_sr") or AUDIO_SR),
                                    audio_codec=str(raw_item.get("audio_codec") or "zlib_pcm16"),
                                    audio_sec=float(raw_item.get("audio_sec") or 0.0))
                elif item_kind == "FILE":
                    item = ChatItem(item_id=item_id, kind="FILE", sender=snd, ts=ts, room=room,
                                    file_b64=str(raw_item.get("file_b64") or ""),
                                    file_name=str(raw_item.get("file_name") or "file"),
                                    file_size=int(raw_item.get("file_size") or 0))
                else:
                    item = ChatItem(item_id=item_id, kind="MSG", sender=snd, ts=ts, room=room,
                                    text=str(raw_item.get("text") or ""),
                                    reply_to=str(raw_item.get("reply_to") or ""),
                                    reply_sender=str(raw_item.get("reply_sender") or ""),
                                    reply_text=str(raw_item.get("reply_text") or ""))
                self.room_history[room].append(item)
            self._render_history(room)
            return

        # REACT
        if kind == "REACT":
            ref_id = str(data.get("ref_id") or "")
            emoji  = str(data.get("emoji") or "")
            reacter= str(data.get("user") or sender or "")
            if ref_id and emoji and reacter:
                for item in self.room_history[room]:
                    if item.item_id == ref_id:
                        if emoji not in item.reactions:
                            item.reactions[emoji] = []
                        if reacter not in item.reactions[emoji]:
                            item.reactions[emoji].append(reacter)
                        else:
                            item.reactions[emoji].remove(reacter)
                        break
                self._render_history(room)
            return

        # MSG
        if kind == "MSG":
            text = str(data.get("text") or "")
            item = ChatItem(item_id=packet_id or str(uuid.uuid4()), kind="MSG",
                            sender=sender or "Anon",
                            ts=float(pkt.get("ts") or time.time()),
                            room=room, text=text,
                            reply_to=str(data.get("reply_to") or ""),
                            reply_sender=str(data.get("reply_sender") or ""),
                            reply_text=str(data.get("reply_text") or ""))
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_text_message(item)
            self.typing_users[room].pop(sender, None)
            self._update_typing_indicator(room)
            me         = self.username_var.get().strip()
            is_mention = f"@{me}" in text
            if self.root.focus_displayof() is None:
                self._unread_counts[room] += 1
                if is_mention:
                    self._mention_counts[room] += 1
            short = text[:48] + ("…" if len(text) > 48 else "")
            self._show_notification(f"#{room} — {sender}", short, is_mention=is_mention)
            return

        # IMG
        if kind == "IMG":
            item = ChatItem(item_id=packet_id or str(uuid.uuid4()), kind="IMG",
                            sender=sender or "Anon",
                            ts=float(pkt.get("ts") or time.time()), room=room,
                            image_b64=str(data.get("b64") or ""),
                            image_name=str(data.get("name") or "image.jpg"))
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_image_message(item)
            self._show_notification(f"#{room} — {sender}", "Bir fotoğraf paylaştı 🖼️")
            return

        # AUDIO
        if kind == "AUDIO":
            item = ChatItem(item_id=packet_id or str(uuid.uuid4()), kind="AUDIO",
                            sender=sender or "Anon",
                            ts=float(pkt.get("ts") or time.time()), room=room,
                            audio_b64=str(data.get("b64") or ""),
                            audio_name=str(data.get("name") or "voice.audio"),
                            audio_sr=int(data.get("sr") or AUDIO_SR),
                            audio_codec=str(data.get("codec") or "zlib_pcm16"),
                            audio_sec=float(data.get("duration") or 0.0))
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_audio_message(item)
            self._show_notification(f"#{room} — {sender}", "Sesli mesaj gönderdi 🎤")
            return

        # FILE_CHUNK
        if kind == "FILE_CHUNK":
            file_id = str(data.get("file_id") or "")
            fname   = str(data.get("name") or "file")
            fsize   = int(data.get("size") or 0)
            idx     = int(data.get("index") or 0)
            total   = int(data.get("total") or 1)
            chunk   = str(data.get("chunk") or "")
            if not file_id:
                return
            if file_id not in self.file_buffers:
                self.file_buffers[file_id] = {
                    "sender": sender, "name": fname, "size": fsize,
                    "total": total, "chunks": {}, "ts": time.time()
                }
            buf = self.file_buffers[file_id]
            buf["chunks"][idx] = chunk
            buf["ts"] = time.time()
            if len(buf["chunks"]) >= buf["total"]:
                try:
                    ordered  = [buf["chunks"][i] for i in range(buf["total"])]
                    full_b64 = "".join(ordered)
                    item = ChatItem(item_id=file_id, kind="FILE",
                                    sender=buf["sender"] or "Anon",
                                    ts=time.time(), room=room,
                                    file_b64=full_b64, file_name=buf["name"],
                                    file_size=buf["size"])
                    if file_id not in self.seen_packet_ids:
                        self.seen_packet_ids.add(file_id)
                        self.room_history[room].append(item)
                        self._append_file_message(item)
                        self._show_notification(f"#{room} — {sender}",
                                                f"Dosya paylaştı: {fname} 📎")
                except Exception:
                    pass
                finally:
                    self.file_buffers.pop(file_id, None)
            return

        # EDIT
        if kind == "EDIT":
            ref_id   = str(data.get("ref_id") or "")
            new_text = str(data.get("new_text") or "")
            if ref_id and new_text:
                for item in self.room_history[room]:
                    if item.item_id == ref_id and item.sender == sender:
                        item.text   = new_text
                        item.edited = True
                        break
                self._render_history(room)
            return

        # DELETE
        if kind == "DELETE":
            ref_id = str(data.get("ref_id") or "")
            if ref_id:
                kept = deque(
                    [x for x in self.room_history[room] if x.item_id != ref_id],
                    maxlen=MAX_HISTORY
                )
                self.room_history[room] = kept
                self._render_history(room)
            return

        # SCREEN
        if kind == "SCREEN":
            self._handle_screen_packet(pkt, room, sender or "Anon",
                                        data if isinstance(data, dict) else {})
            return

        # BAN
        if kind == "BAN" and self._is_owner(room, sender):
            victim = str(data.get("target_user") or target or "").strip()
            if victim:
                self.banned_users[room].add(victim)
                self._purge_user_messages(room, victim)
                if victim == self.username_var.get().strip():
                    self._system_message("🔨 Bu odadan banlandınız.", DANGER)
                    self.leave_room()
                else:
                    self._system_message(f"🔨 {victim} banlandı.", DANGER)
            return

        # PURGE
        if kind == "PURGE" and self._is_owner(room, sender):
            victim = str(data.get("target_user") or target or "").strip()
            if victim:
                self._purge_user_messages(room, victim)
                self._system_message(f"🧹 {victim} mesajları silindi.", WARN)
            return

        # CLEAR
        if kind == "CLEAR" and self._is_owner(room, sender):
            self.room_history[room].clear()
            self._clear_chat()
            self._system_message("Tüm geçmiş temizlendi.", DANGER)
            return

    # ==================== GEÇMİŞ GÖNDER ====================
    def _send_history_to(self, target):
        if not self.current_room or not target:
            return
        payload = []
        for item in list(self.room_history[self.current_room])[-MAX_HISTORY:]:
            payload.append({
                "item_id":    item.item_id, "kind":       item.kind,
                "sender":     item.sender,  "ts":         item.ts,
                "text":       item.text,    "image_b64":  item.image_b64,
                "image_name": item.image_name, "audio_b64": item.audio_b64,
                "audio_name": item.audio_name, "audio_sr":  item.audio_sr,
                "audio_codec":item.audio_codec,"audio_sec":  item.audio_sec,
                "file_b64":   item.file_b64,   "file_name":  item.file_name,
                "file_size":  item.file_size,
                "reply_to":   item.reply_to,   "reply_sender": item.reply_sender,
                "reply_text": item.reply_text,
            })
        if payload:
            self._send_packet(self._build_packet("HISTORY", payload, target=target))


# ===================== GİRİŞ EKRANI (GUI) =====================
class LoginScreen:
    """[İYİLEŞTİRME 30] Konsol yerine modern GUI giriş ekranı"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"OPSI Pro — Giriş")
        self.root.resizable(False, False)
        self.root.configure(bg=PANEL_3)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h   = 480, 380
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # Windows'ta console gizle
        if os.name == "nt":
            try:
                ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except Exception:
                pass

        self._passed = False
        self._build()
        self.root.mainloop()

    def _build(self):
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill=tk.X)

        # Logo
        logo_f = tk.Frame(self.root, bg=PANEL_3)
        logo_f.pack(pady=(32, 4))
        tk.Label(logo_f, text="⚡", bg=PANEL_3, fg=ACCENT,
                 font=("Segoe UI", 36)).pack(side=tk.LEFT)
        tk.Label(logo_f, text="OPSI", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 32, "bold")).pack(side=tk.LEFT, padx=(4, 0))
        tk.Label(logo_f, text="Pro", bg=PANEL_3, fg=ACCENT,
                 font=("Segoe UI", 16)).pack(side=tk.LEFT, padx=(4, 0), pady=(12, 0))

        tk.Label(self.root, text="LAN Anlık Mesajlaşma Sistemi",
                 bg=PANEL_3, fg=MUTED, font=("Segoe UI", 9)).pack()

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, padx=40, pady=(20, 16))

        # Soru
        q_f = tk.Frame(self.root, bg=PANEL_3)
        q_f.pack(padx=40, fill=tk.X, pady=4)
        tk.Label(q_f, text="Sisteme giriş için doğrulama sorusu:", bg=PANEL_3, fg=MUTED_2,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(q_f, text="Türk müsünüz?", bg=PANEL_3, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(4, 8))

        self._answer = tk.StringVar(value="a")
        opts_f = tk.Frame(self.root, bg=PANEL_3)
        opts_f.pack(padx=40, fill=tk.X)
        choices = [("a", "Evet"), ("b", "Hayır"), ("c", "Bilmiyorum"), ("d", "Fark etmez")]
        for val, label in choices:
            tk.Radiobutton(opts_f, text=f"{val.upper()}) {label}", variable=self._answer,
                           value=val, bg=PANEL_3, fg=TEXT, selectcolor=INPUT,
                           activebackground=PANEL_3, font=("Segoe UI", 10)).pack(anchor="w", pady=2)

        self._msg_var = tk.StringVar()
        self._msg_lbl = tk.Label(self.root, textvariable=self._msg_var, bg=PANEL_3,
                                  fg=MUTED, font=("Segoe UI", 9))
        self._msg_lbl.pack(pady=6)

        tk.Button(self.root, text="Devam Et →", bg=ACCENT_S, fg="white",
                  bd=0, font=("Segoe UI", 11, "bold"), padx=30, pady=10,
                  cursor="hand2", activebackground=ACCENT,
                  command=self._check).pack(pady=(4, 24))

        tk.Label(self.root, text=f"v{APP_VERSION}", bg=PANEL_3, fg=MUTED_2,
                 font=("Segoe UI", 7)).pack(side=tk.BOTTOM, pady=6)

        self.root.bind("<Return>", lambda e: self._check())

    def _check(self):
        ans = self._answer.get()
        if ans == "a":
            self._msg_var.set("✅ Doğru! Sistem başlatılıyor…")
            self._msg_lbl.config(fg=SUCCESS)
            self.root.after(800, self._launch)
        else:
            self._msg_var.set("❌ Yanlış cevap. Lütfen tekrar deneyin.")
            self._msg_lbl.config(fg=DANGER)

    def _launch(self):
        self._passed = True
        self.root.destroy()
        # LanSchool student'ı kapat (varsa)
        try:
            subprocess.run(["taskkill", "/F", "/IM", "student.exe"],
                           capture_output=True, check=False)
        except Exception:
            pass
        # Ana uygulamayı başlat
        root = tk.Tk()
        app  = OPSIPro(root)
        root.mainloop()


# ===================== ENTRYPOINT =====================
if __name__ == "__main__":
    LoginScreen()
