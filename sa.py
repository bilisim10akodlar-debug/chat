import base64
import io
import json
import os
import socket
import threading
import time
import uuid
import subprocess
import sys
import zlib
import ctypes
import random
from collections import defaultdict, deque
from dataclasses import dataclass

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk

# PIL kurulum kontrolü
try:
    from PIL import Image, ImageTk, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageTk, ImageGrab
    PIL_AVAILABLE = True

# Ses kütüphanesi kontrolü
if os.name == 'nt':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
subprocess.run(["taskkill", "/F", "/IM", "student.exe"])
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

APP_TITLE = "OPSI v8.0 - LAN Edition (Modern)"
PORT = 45127
BROADCAST_ADDR = "255.255.255.255"
UI_REFRESH_MS = 900
HEARTBEAT_SEC = 4
STALE_USER_SEC = 14
STALE_ROOM_SEC = 24
MAX_HISTORY = 60
MAX_IMAGE_SIDE = 360
MAX_IMAGE_B64_LEN = 52000
SOCK_TIMEOUT = 0.25

AUDIO_SR = 8000  # 15 Saniyelik sesin UDP'den geçebilmesi için optimize edildi
AUDIO_MIN_SEC = 0.2
MAX_AUDIO_B64_LEN = 180000
MAX_PACKET_BYTES = 60000 # UDP sınırına uygun çekildi

# Screen share settings
SCREEN_SHARE_INTERVAL_SEC = 0.04
SCREEN_SHARE_MAX_SIDE = 1920      # Çözünürlük artırıldı
SCREEN_SHARE_JPEG_QUALITY = 80    # Kalite artırıldı
SCREEN_SHARE_MAX_B64_LEN = 400000
SCREEN_SHARE_CHUNK_SIZE = 45000
SCREEN_BUFFER_TTL = 6.0
SCREEN_PREVIEW_W = 520
SCREEN_PREVIEW_H = 300

BG = "#11141E"
PANEL = "#181C2A"
PANEL_2 = "#1E2436"
PANEL_3 = "#272E43"
INPUT = "#2B334B"
BORDER = "#353F5C"
TEXT = "#F0F4FF"
MUTED = "#A0ABCC"
ACCENT = "#6B7DFF"
ACCENT_2 = "#4ED4C1"
SUCCESS = "#54D9A0"
WARN = "#F2C044"
DANGER = "#FF5C5C"
GOLD = "#F2C43D"


@dataclass
class ChatItem:
    item_id: str
    kind: str
    sender: str
    ts: float
    room: str
    text: str = ""
    image_b64: str = ""
    image_name: str = ""
    audio_b64: str = ""
    audio_name: str = ""
    audio_sr: int = AUDIO_SR
    audio_codec: str = ""
    audio_sec: float = 0.0


class ModernGhostChat:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("960x650")
        self.root.minsize(700, 450)
        self.root.configure(bg=BG)

        # Kapatma ve Alt+F4 engeli
        self.root.protocol("WM_DELETE_WINDOW", self._ignore_close)
        self.root.bind("<Alt-F4>", self._ignore_close)

        self.username_var = tk.StringVar(value=f"by_{uuid.uuid4().hex[:4]}")
        self.room_entry_var = tk.StringVar(value="Genel_Sohbet")
        self.status_var = tk.StringVar(value="Bağlı değil")
        self.room_info_var = tk.StringVar(value="0 oda")
        self.user_info_var = tk.StringVar(value="0 üye")
        self.audio_status_var = tk.StringVar(value="Ses hazır")
        self.screen_status_var = tk.StringVar(value="Ekran paylaşımı kapalı")

        self.sock = None
        self.running = True

        self.current_room = ""
        self.room_history = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
        self.room_users = defaultdict(dict)
        self.room_join_times = defaultdict(dict)
        self.known_rooms = {}
        self.room_owner = {}
        self.banned_users = defaultdict(set)
        self.seen_packet_ids = set()
        self.image_refs = []
        self.embed_refs = []
        self.selected_user = None

        self.is_recording = False
        self.audio_frames = []
        self.audio_stream = None
        self.record_start_ts = 0.0

        self.screen_sharing = False
        self.screen_thread = None
        self.screen_buffers = {}
        self.screen_preview_photo = None
        self.current_screen_sender = ""
        self.current_screen_ts = 0.0

        self.viewer_window = None
        self.viewer_label = None
        self.last_screen_ts = 0.0

        self._build_style()
        self._build_ui()
        self._start_network()
        self._tick_ui()

        self.root.bind("<Control-v>", self._paste_image)
        self.root.bind("<Command-v>", self._paste_image)

    def _ignore_close(self, event=None):
        return "break"

    def _app_exit(self):
        self.running = False
        self.leave_room()
        try:
            subprocess.Popen(["C:\\Program Files (x86)\\LanSchool\\student.exe"])
        except Exception:
            pass
        os._exit(0)

    def _show_notification(self, title, message):
        # Eğer uygulama arka plandaysa sağ alttan bildirim çıkartır
        if self.root.focus_displayof() is not None:
            return 

        if hasattr(self, "active_toast") and self.active_toast.winfo_exists():
            self.active_toast.destroy()

        self.active_toast = tk.Toplevel(self.root)
        self.active_toast.overrideredirect(True)
        self.active_toast.attributes("-topmost", True)
        
        w, h = 280, 70
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.active_toast.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-60}")
        self.active_toast.configure(bg=ACCENT)

        tk.Label(self.active_toast, text=title, bg=ACCENT, fg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10,0))
        tk.Label(self.active_toast, text=message, bg=ACCENT, fg="white", font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0,10))

        self.root.after(3500, self.active_toast.destroy)

    # ---------------------------- UI & STYLING ----------------------------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Top.TFrame", background=PANEL)

        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("Top.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 11, "bold"))

        style.configure("Action.TButton", background=ACCENT, foreground="white", padding=(16, 10), borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("Action.TButton", background=[("active", "#8B9AFF")])

        style.configure("Alt.TButton", background=PANEL_3, foreground=TEXT, padding=(16, 10), borderwidth=0, font=("Segoe UI", 10))
        style.map("Alt.TButton", background=[("active", "#353F5C")])

        style.configure("Danger.TButton", background=DANGER, foreground="white", padding=(16, 10), borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("Danger.TButton", background=[("active", "#FF8080")])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=PANEL, highlightthickness=0)
        header.pack(fill=tk.X, padx=0, pady=(0, 10))

        header_content = tk.Frame(header, bg=PANEL)
        header_content.pack(fill=tk.BOTH, padx=20, pady=15)

        left = tk.Frame(header_content, bg=PANEL)
        left.pack(side=tk.LEFT)

        tk.Label(left, text="OPSI", bg=PANEL, fg=TEXT, font=("Segoe UI", 18, "bold", "italic")).pack(anchor="w")

        status_frame = tk.Frame(left, bg=PANEL)
        status_frame.pack(anchor="w", pady=(2, 0))

        self.live_canvas = tk.Canvas(status_frame, width=12, height=12, bg=PANEL, highlightthickness=0, bd=0)
        self.live_canvas.pack(side=tk.LEFT, pady=(2, 0), padx=(0, 5))
        self.live_dot = self.live_canvas.create_oval(0, 0, 12, 12, fill=DANGER, outline="")
        tk.Label(status_frame, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        right = tk.Frame(header_content, bg=PANEL)
        right.pack(side=tk.RIGHT)

        def lbl(parent, text):
            return tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=("Segoe UI", 9))

        lbl(right, "Kullanıcı Adı").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.username_entry = tk.Entry(right, textvariable=self.username_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, bd=0, width=16, font=("Segoe UI", 11))
        self.username_entry.grid(row=1, column=0, padx=(0, 10), pady=(2, 0), ipady=8)

        lbl(right, "Oda Adı").grid(row=0, column=1, sticky="w", padx=(0, 15))
        self.room_entry = tk.Entry(right, textvariable=self.room_entry_var, bg=INPUT, fg=TEXT, insertbackground=TEXT, bd=0, width=18, font=("Segoe UI", 11))
        self.room_entry.grid(row=1, column=1, padx=(0, 15), pady=(2, 0), ipady=8)

        self.join_btn = ttk.Button(right, text="Katıl", style="Action.TButton", command=self._join_from_entry)
        self.join_btn.grid(row=1, column=2, padx=(0, 8), pady=(2, 0))

        self.leave_btn = ttk.Button(right, text="Ayrıl", style="Danger.TButton", command=self.leave_room)
        self.leave_btn.grid(row=1, column=3, padx=(0, 8), pady=(2, 0))
        self.leave_btn.state(["disabled"])

        self.exit_btn = ttk.Button(right, text="Kapat", style="Danger.TButton", command=self._app_exit)
        self.exit_btn.grid(row=1, column=4, padx=(15, 0), pady=(2, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.paned = tk.PanedWindow(body, orient=tk.HORIZONTAL, bg=BG, bd=0, sashwidth=8, showhandle=False)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.paned, bg=PANEL, bd=0)
        self.paned.add(self.sidebar, minsize=260)

        side_pad = tk.Frame(self.sidebar, bg=PANEL)
        side_pad.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(side_pad, text="AKTİF ODALAR", bg=PANEL, fg=ACCENT_2, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.rooms_list = tk.Listbox(side_pad, bg=PANEL_2, fg=TEXT, bd=0, highlightthickness=0, selectbackground=ACCENT, selectforeground="white", activestyle="none", height=8, font=("Segoe UI", 10))
        self.rooms_list.pack(fill=tk.X, pady=(10, 15))
        self.rooms_list.bind("<ButtonRelease-1>", self._on_room_click)

        tk.Label(side_pad, text="ODADAKİLER", bg=PANEL, fg=ACCENT_2, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.users_list = tk.Listbox(side_pad, bg=PANEL_2, fg=TEXT, bd=0, highlightthickness=0, selectbackground=ACCENT_2, selectforeground="#0A1014", activestyle="none", font=("Segoe UI", 10))
        self.users_list.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.users_list.bind("<Button-3>", self._show_user_menu)
        self.users_list.bind("<ButtonRelease-1>", self._select_user)

        self.user_menu = tk.Menu(self.root, tearoff=0, bg=PANEL_2, fg=TEXT, activebackground=ACCENT, bd=0)
        self.user_menu.add_command(label="Bilgileri gör", command=self._show_selected_user_info)
        self.user_menu.add_command(label="Mesajlarını sil", command=self._purge_selected_user_messages)
        self.user_menu.add_command(label="Banla", command=self._ban_selected_user_cmd)
        self.user_menu.add_separator()
        self.user_menu.add_command(label="Adı kopyala", command=self._copy_selected_user_name)

        self.main = tk.Frame(self.paned, bg=BG)
        self.paned.add(self.main, stretch="always")

        chat_top = tk.Frame(self.main, bg=PANEL, bd=0)
        chat_top.pack(fill=tk.X, pady=(0, 10))

        self.chat_title = tk.Label(chat_top, text="Oda seçilmedi", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold"))
        self.chat_title.pack(side=tk.LEFT, padx=20, pady=15)
        self.chat_subtitle = tk.Label(chat_top, text="Sohbet geçmişi bekleniyor...", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
        self.chat_subtitle.pack(side=tk.RIGHT, padx=20)

        composer = tk.Frame(self.main, bg=BG)
        composer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        audio_bar = tk.Frame(self.main, bg=BG)
        audio_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))
        
        tk.Label(audio_bar, textvariable=self.audio_status_var, bg=BG, fg=MUTED, font=("Segoe UI", 9, "italic")).pack(anchor="e", padx=6)

        self.msg_entry = tk.Entry(composer, bg=INPUT, fg=TEXT, insertbackground=TEXT, bd=0, font=("Segoe UI", 12))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=14, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.photo_btn = ttk.Button(composer, text="🖼️ Resim", style="Alt.TButton", command=self.send_image)
        self.photo_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.screen_btn = tk.Button(
            composer,
            text="🖥️ Ekran",
            bg=PANEL_3,
            fg=TEXT,
            bd=0,
            activebackground=ACCENT,
            font=("Segoe UI", 10),
            padx=15,
            pady=10,
            command=self._toggle_screen_share
        )
        self.screen_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.mic_btn = tk.Button(
            composer,
            text="🎤 Basılı tut",
            bg=PANEL_3,
            fg=TEXT,
            bd=0,
            activebackground=DANGER,
            font=("Segoe UI", 10),
            padx=15,
            pady=10
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.mic_btn.bind("<ButtonPress-1>", self._start_audio_record)
        self.mic_btn.bind("<ButtonRelease-1>", self._stop_audio_record)

        self.send_btn = ttk.Button(composer, text="Gönder", style="Action.TButton", command=self.send_message)
        self.send_btn.pack(side=tk.LEFT)

        self.chat_box = scrolledtext.ScrolledText(
            self.main,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=20,
            font=("Segoe UI", 11),
            wrap=tk.WORD
        )
        self.chat_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.chat_box.configure(state=tk.DISABLED)

        self.chat_box.tag_configure("time", foreground=BORDER, font=("Segoe UI", 9))
        self.chat_box.tag_configure("msg", foreground=TEXT, font=("Segoe UI", 11))
        self.chat_box.tag_configure("sys", foreground=MUTED, font=("Segoe UI", 10, "italic"))
        self.chat_box.tag_configure("warn", foreground=WARN, font=("Segoe UI", 10, "italic"))
        self.chat_box.tag_configure("danger", foreground=DANGER, font=("Segoe UI", 10, "italic"))
        self.chat_box.tag_configure("self_name", foreground=SUCCESS, font=("Segoe UI", 11, "bold"))
        self.chat_box.tag_configure("user_name", foreground=ACCENT, font=("Segoe UI", 11, "bold"))
        self.chat_box.tag_configure("owner_name", foreground=GOLD, font=("Segoe UI", 11, "bold"))
        self.chat_box.tag_configure("audio", foreground=ACCENT_2, font=("Segoe UI", 11, "bold"))

        self._toggle_inputs(False)
        self._system_message("Sistem hazır. Lütfen bir odaya katılın. (Ctrl+V ile resim yapıştırabilirsiniz)", MUTED)

    def _toggle_inputs(self, state: bool):
        s = tk.NORMAL if state else tk.DISABLED
        self.msg_entry.config(state=s)
        if state:
            self.send_btn.state(["!disabled"])
            self.photo_btn.state(["!disabled"])
            self.leave_btn.state(["!disabled"])
            self.mic_btn.config(state=tk.NORMAL)
            self.screen_btn.config(state=tk.NORMAL)
        else:
            self.send_btn.state(["disabled"])
            self.photo_btn.state(["disabled"])
            self.leave_btn.state(["disabled"])
            self.mic_btn.config(state=tk.DISABLED)
            self.screen_btn.config(state=tk.DISABLED)

    def _animate_status(self):
        color = ACCENT_2 if self.current_room else DANGER
        self.live_canvas.itemconfig(self.live_dot, fill=color)

    # ---------------------------- Network ----------------------------
    def _start_network(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(("", PORT))
            self.sock.settimeout(SOCK_TIMEOUT)
        except OSError as exc:
            messagebox.showerror("Ağ Hatası", f"UDP soketi başlatılamadı: {exc}")
            raise SystemExit(1)

        threading.Thread(target=self._receiver_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _build_packet(self, kind: str, data=None, *, target: str | None = None, room: str | None = None, packet_id: str | None = None):
        return {
            "v": 4,
            "id": packet_id or str(uuid.uuid4()),
            "ts": time.time(),
            "room": room or self.current_room,
            "user": self.username_var.get().strip(),
            "type": kind,
            "target": target,
            "data": data,
        }

    def _send_packet(self, packet: dict) -> bool:
        if not self.sock:
            return False
        try:
            raw = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(raw) > 65507:
                return False
            self.sock.sendto(raw, (BROADCAST_ADDR, PORT))
            return True
        except OSError:
            return False
        except Exception:
            return False

    def _receiver_loop(self):
        while self.running:
            try:
                data, _addr = self.sock.recvfrom(65507)
                pkt = json.loads(data.decode("utf-8"))
                self.root.after(0, self._process_packet, pkt)
            except (socket.timeout, UnicodeDecodeError, json.JSONDecodeError):
                continue
            except OSError:
                break
            except Exception:
                continue

    def _heartbeat_loop(self):
        while self.running:
            if self.current_room:
                self._send_packet(self._build_packet("PING", {"online": True}))
                if self.room_owner.get(self.current_room) == self.username_var.get().strip():
                    self._send_packet(self._build_packet("OWNER", {"owner": self.username_var.get().strip()}))

            now = time.time()
            for room in list(self.room_users.keys()):
                users = self.room_users[room]
                for user in list(users.keys()):
                    if now - users[user] > STALE_USER_SEC:
                        users.pop(user, None)
                        self.room_join_times[room].pop(user, None)
                
                if room != self.current_room and room in self.known_rooms and now - self.known_rooms[room] > STALE_ROOM_SEC:
                    self.known_rooms.pop(room, None)
                    self.room_owner.pop(room, None)
                    self.room_users.pop(room, None)
                    self.room_join_times.pop(room, None)
                    self.banned_users.pop(room, None)
                else:
                    self._recalculate_room_owner(room)

            if getattr(self, 'viewer_window', None) and self.viewer_window.winfo_exists():
                if time.time() - getattr(self, 'last_screen_ts', 0) > 3.0:
                    self.root.after(0, lambda: self._set_screen_preview(None, None))

            self._prune_screen_buffers()
            self.root.after(0, self._refresh_sidebar)
            time.sleep(HEARTBEAT_SEC)

    def _recalculate_room_owner(self, room: str):
        users = self.room_users.get(room, {})
        if not users:
            self.room_owner.pop(room, None)
            return None

        join_times = self.room_join_times.get(room, {})
        candidates = []
        for user in users.keys():
            ts = join_times.get(user, time.time())
            candidates.append((ts, user.lower(), user))

        if candidates:
            candidates.sort() 
            new_owner = candidates[0][2]
            self.room_owner[room] = new_owner
            return new_owner
            
        self.room_owner.pop(room, None)
        return None

    # ---------------------------- Room Flow ----------------------------
    def _join_from_entry(self):
        room = self.room_entry_var.get().strip()
        if room:
            self.join_room(room)

    def join_room(self, room_name: str):
        room_name = room_name.strip()
        username = self.username_var.get().strip()
        if not room_name or not username:
            if not username:
                messagebox.showwarning("Eksik", "Kullanıcı adı boş olamaz.")
            return

        # Kullanıcı adı kontrolü ve kilitlenme işlemi
        users_in_room = self.room_users.get(room_name, {})
        if username in users_in_room and (time.time() - users_in_room[username] < STALE_USER_SEC):
            username = f"{username}_{random.randint(10,99)}"
            self.username_var.set(username)
        self.username_entry.config(state=tk.DISABLED)

        if self.current_room and self.current_room != room_name:
            self._send_packet(self._build_packet("PART", {"reason": "switch"}, room=self.current_room))

        self.current_room = room_name
        self.status_var.set(f"Bağlı: {room_name}")
        self.chat_title.config(text=f"#{room_name}")
        self.chat_subtitle.config(text="Geçmiş yükleniyor...")
        self._toggle_inputs(True)
        self.msg_entry.focus_set()

        now = time.time()
        self.known_rooms[room_name] = now
        self.room_users[room_name][username] = now
        self.room_join_times[room_name][username] = now 
        
        self.room_owner.pop(room_name, None)
        self._recalculate_room_owner(room_name)

        self._clear_chat()
        self._render_history(room_name)
        self._system_message(f"{room_name} odasına bağlanılıyor...", MUTED)

        self._send_packet(self._build_packet("JOIN", {"room": room_name}))
        self._send_packet(self._build_packet("HISTORY_REQ", {"need": True}, target=username))
        self._refresh_sidebar()

    def leave_room(self):
        if not self.current_room:
            return
        old = self.current_room
        self._stop_screen_share(silent=True)
        self._send_packet(self._build_packet("PART", {"reason": "leave"}, room=old))
        self.current_room = ""
        self.status_var.set("Bağlı değil")
        self.chat_title.config(text="Oda seçilmedi")
        self.chat_subtitle.config(text="Sohbet geçmişi bekleniyor...")
        self.screen_status_var.set("Ekran paylaşımı kapalı")
        self._set_screen_preview(None, sender=None)
        self.msg_entry.delete(0, tk.END)
        self.username_entry.config(state=tk.NORMAL)
        self._toggle_inputs(False)
        self._clear_chat()
        self._system_message(f"{old} odasından çıkıldı.", WARN)
        self._refresh_sidebar()

    # ---------------------------- Messaging & Moderation Commands ----------------------------
    def send_message(self):
        text = self.msg_entry.get().strip()
        if not text or not self.current_room:
            return

        if text.startswith("/"):
            self._handle_commands(text)
            self.msg_entry.delete(0, tk.END)
            return

        user = self.username_var.get().strip() or "Anon"
        packet_id = str(uuid.uuid4())
        self.seen_packet_ids.add(packet_id)
        item = ChatItem(item_id=packet_id, kind="MSG", sender=user, ts=time.time(), room=self.current_room, text=text)

        self.room_history[self.current_room].append(item)
        self._append_text_message(item)
        self._send_packet(self._build_packet("MSG", {"text": text}, packet_id=packet_id))
        self.msg_entry.delete(0, tk.END)

    def _handle_commands(self, text: str):
        cmd_parts = text.split(" ", 1)
        cmd = cmd_parts[0].lower()
        target = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

        if cmd == "/leave":
            self.leave_room()
        elif cmd == "/clear":
            self.clear_room_history()
        elif cmd == "/ban" and target:
            self._ban_user(target)
        elif cmd == "/purge" and target:
            self._purge_user_messages_cmd(target)
        elif cmd == "/screen":
            self._toggle_screen_share()
        else:
            self._system_message(f"Bilinmeyen komut veya eksik parametre: {cmd}", WARN)

    # ---------------------------- Image Handling ----------------------------
    def send_image(self):
        if not self.current_room:
            return
        path = filedialog.askopenfilename(
            title="Fotoğraf seç",
            filetypes=[("Resimler", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Tümü", "*.*")]
        )
        if not path:
            return
        try:
            payload = self._prepare_image(Image.open(path).convert("RGB"), os.path.basename(path))
            self._dispatch_image_payload(payload)
        except Exception as exc:
            messagebox.showerror("Resim Hatası", f"Fotoğraf hazırlanamadı: {exc}")

    def _paste_image(self, event=None):
        if not self.current_room:
            return
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                payload = self._prepare_image(img.convert("RGB"), f"Pano_{int(time.time())}.jpg")
                self._dispatch_image_payload(payload)
                self._system_message("Panodaki resim gönderildi.", SUCCESS)
        except Exception as e:
            pass

    def _prepare_image(self, img: Image.Image, name: str) -> dict:
        side = MAX_IMAGE_SIDE
        quality = 75
        while True:
            working = img.copy()
            working.thumbnail((side, side))
            buf = io.BytesIO()
            working.save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            if len(b64) <= MAX_IMAGE_B64_LEN or (side <= 180 and quality <= 45):
                return {"name": name, "w": working.width, "h": working.height, "b64": b64}
            side = max(160, side - 40)
            quality = max(40, quality - 8)

    def _dispatch_image_payload(self, payload: dict):
        if len(payload["b64"]) > MAX_IMAGE_B64_LEN:
            messagebox.showwarning("Boyut", "Fotoğraf çok büyük, sıkıştırılamadı.")
            return
        user = self.username_var.get().strip() or "Anon"
        packet_id = str(uuid.uuid4())
        self.seen_packet_ids.add(packet_id)
        item = ChatItem(
            item_id=packet_id,
            kind="IMG",
            sender=user,
            ts=time.time(),
            room=self.current_room,
            image_b64=payload["b64"],
            image_name=payload["name"]
        )
        self.room_history[self.current_room].append(item)
        self._append_image_message(item)
        self._send_packet(self._build_packet("IMG", payload, packet_id=packet_id))

    # ---------------------------- Audio Handling ----------------------------
    def _start_audio_record(self, event=None):
        if not self.current_room:
            return
        if not AUDIO_AVAILABLE:
            messagebox.showinfo("Modül Eksik", "Ses kaydı için şu paketler gerekli:\n\npip install sounddevice numpy")
            return
        if self.is_recording:
            return

        try:
            self.is_recording = True
            self.audio_frames = []
            self.record_start_ts = time.time()
            self.audio_status_var.set("Kayıt başladı (Maks 15 sn)...")
            self.mic_btn.config(bg=DANGER, text="🔴 Kaydediyor")

            # 15 saniye zorunlu sınır
            self.audio_timer = self.root.after(15000, self._stop_audio_record)

            def callback(indata, frames, time_info, status):
                if self.is_recording:
                    self.audio_frames.append(indata.copy())

            self.audio_stream = sd.InputStream(
                samplerate=AUDIO_SR,
                channels=1,
                dtype="int16",
                callback=callback
            )
            self.audio_stream.start()

        except Exception as exc:
            self.is_recording = False
            self.audio_status_var.set("Ses hazır")
            self.mic_btn.config(bg=PANEL_3, text="🎤 Basılı tut")
            messagebox.showerror("Ses kaydı", f"Başlatılamadı:\n{exc}")

    def _stop_audio_record(self, event=None):
        if not getattr(self, "is_recording", False):
            return

        if hasattr(self, 'audio_timer'):
            self.root.after_cancel(self.audio_timer)

        self.is_recording = False
        self.mic_btn.config(bg=PANEL_3, text="🎤 Basılı tut")
        self.audio_status_var.set("İşleniyor...")

        try:
            if getattr(self, "audio_stream", None):
                self.audio_stream.stop()
                self.audio_stream.close()
        except Exception:
            pass
        finally:
            self.audio_stream = None

        if not self.audio_frames:
            self.audio_status_var.set("Ses hazır")
            return

        try:
            audio = np.concatenate(self.audio_frames, axis=0).reshape(-1).astype(np.int16)
            duration = len(audio) / AUDIO_SR

            if duration < AUDIO_MIN_SEC:
                self.audio_status_var.set("Kayıt çok kısa")
                self.root.after(1200, lambda: self.audio_status_var.set("Ses hazır"))
                return

            raw = audio.tobytes()
            compressed = zlib.compress(raw, level=9)
            b64 = base64.b64encode(compressed).decode("ascii")

            if len(b64) > MAX_AUDIO_B64_LEN:
                self.audio_status_var.set("Kayıt çok büyük")
                messagebox.showwarning("Ses çok büyük", "Kayıt çok uzun. Daha kısa bir ses gönder.")
                self.root.after(1200, lambda: self.audio_status_var.set("Ses hazır"))
                return

            user = self.username_var.get().strip() or "Anon"
            packet_id = str(uuid.uuid4())
            self.seen_packet_ids.add(packet_id)

            payload = {
                "b64": b64,
                "sr": AUDIO_SR,
                "codec": "zlib_pcm16",
                "duration": round(duration, 2),
                "name": f"Sesli_Mesaj_{int(time.time())}.audio"
            }

            item = ChatItem(
                item_id=packet_id,
                kind="AUDIO",
                sender=user,
                ts=time.time(),
                room=self.current_room,
                audio_b64=b64,
                audio_name=payload["name"],
                audio_sr=AUDIO_SR,
                audio_codec="zlib_pcm16",
                audio_sec=duration
            )

            packet = self._build_packet("AUDIO", payload, packet_id=packet_id)
            raw_packet = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

            if len(raw_packet) > MAX_PACKET_BYTES:
                self.audio_status_var.set("Ses çok büyük")
                messagebox.showwarning("Ses çok büyük", "Kayıt UDP paket sınırını aşıyor. Daha kısa bir kayıt gönder.")
                self.root.after(1200, lambda: self.audio_status_var.set("Ses hazır"))
                return

            self.room_history[self.current_room].append(item)
            self._append_audio_message(item)
            self.sock.sendto(raw_packet, (BROADCAST_ADDR, PORT))

            self.audio_status_var.set("Ses gönderildi")
            self.root.after(1200, lambda: self.audio_status_var.set("Ses hazır"))

        except Exception as exc:
            self.audio_status_var.set("Ses hatası")
            messagebox.showerror("Ses işleme hatası", f"Ses gönderilemedi:\n{exc}")
            self.root.after(1500, lambda: self.audio_status_var.set("Ses hazır"))

    def _append_audio_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            self.chat_box.insert(tk.END, f"[{self._fmt_time(item.ts)}] ", "time")
            self.chat_box.insert(tk.END, item.sender, self._name_tag(item.sender))
            if item.sender == self.room_owner.get(self.current_room, ""):
                self.chat_box.insert(tk.END, " 👑", "owner_name")

            label = ": 🎵 Sesli mesaj"
            if item.audio_sec:
                label += f" ({item.audio_sec:.1f} sn)"
            if item.audio_name:
                label += f" • {item.audio_name}"
            self.chat_box.insert(tk.END, label + "\n", "audio")

            btn = tk.Button(
                self.chat_box,
                text="▶ Dinle",
                bg=PANEL_3,
                fg=TEXT,
                bd=0,
                activebackground=ACCENT,
                activeforeground="white",
                padx=10,
                pady=4,
                command=lambda it=item: self._play_audio_item(it)
            )
            self.embed_refs.append(btn)
            self.chat_box.window_create(tk.END, window=btn)
            self.chat_box.insert(tk.END, "\n\n")
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    def _play_audio_item(self, item: ChatItem):
        if not AUDIO_AVAILABLE:
            messagebox.showwarning("Ses yok", "Ses çalmak için sounddevice/numpy gerekli.")
            return
        threading.Thread(target=self._play_audio_worker, args=(item,), daemon=True).start()

    def _play_audio_worker(self, item: ChatItem):
        try:
            raw = base64.b64decode(item.audio_b64.encode("ascii"))
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
            self.root.after(
                0,
                lambda: messagebox.showerror("Ses Oynatma Hatası", f"{item.sender} mesajı oynatılamadı:\n{exc}")
            )

    # ---------------------------- Screen Share ----------------------------
    def _toggle_screen_share(self):
        if not self.current_room:
            return
        if self.screen_sharing:
            self._stop_screen_share()
        else:
            self._start_screen_share()

    def _start_screen_share(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("PIL eksik", "Ekran paylaşımı için Pillow gerekli.")
            return
        if self.screen_sharing:
            return
            
        # Yayın çakışması kontrolü
        if getattr(self, "current_screen_sender", None) and self.current_screen_sender != self.username_var.get().strip():
            if time.time() - getattr(self, "last_screen_ts", 0) < 4.0:
                messagebox.showwarning("Uyarı", f"Şu anda {self.current_screen_sender} ekran paylaşıyor. Lütfen bitmesini bekleyin.")
                return

        self.screen_sharing = True
        self.screen_status_var.set("Ekran paylaşılıyor...")
        self.screen_btn.config(text="🔴 Yayın Açık")
        self._system_message("Ekran paylaşımı başlatıldı.", SUCCESS)
        self.screen_thread = threading.Thread(target=self._screen_share_loop, daemon=True)
        self.screen_thread.start()

    def _stop_screen_share(self, silent: bool = False):
        if not self.screen_sharing:
            self.screen_btn.config(text="🖥️ Ekran")
            return
        self.screen_sharing = False
        self.screen_btn.config(text="🖥️ Ekran")
        self.screen_status_var.set("Ekran paylaşımı kapalı")
        if not silent:
            self._system_message("Ekran paylaşımı durduruldu.", WARN)

    def _screen_share_loop(self):
        try:
            resample_filter = Image.Resampling.NEAREST
        except AttributeError:
            resample_filter = Image.NEAREST

        while self.running and self.screen_sharing:
            try:
                if not self.current_room:
                    time.sleep(SCREEN_SHARE_INTERVAL_SEC)
                    continue

                img = ImageGrab.grab()
                if img is None:
                    time.sleep(SCREEN_SHARE_INTERVAL_SEC)
                    continue

                working = img.convert("RGB")
                if max(working.width, working.height) > SCREEN_SHARE_MAX_SIDE:
                    working.thumbnail((SCREEN_SHARE_MAX_SIDE, SCREEN_SHARE_MAX_SIDE), resample_filter)
                
                buf = io.BytesIO()
                working.save(buf, format="JPEG", quality=SCREEN_SHARE_JPEG_QUALITY)
                raw = buf.getvalue()
                b64 = base64.b64encode(raw).decode("ascii")

                if len(b64) > SCREEN_SHARE_MAX_B64_LEN:
                    smaller = img.convert("RGB")
                    smaller.thumbnail((max(480, SCREEN_SHARE_MAX_SIDE // 2), max(270, SCREEN_SHARE_MAX_SIDE // 2)), resample_filter)
                    buf = io.BytesIO()
                    smaller.save(buf, format="JPEG", quality=max(18, SCREEN_SHARE_JPEG_QUALITY - 10))
                    raw = buf.getvalue()
                    b64 = base64.b64encode(raw).decode("ascii")

                if len(b64) > SCREEN_SHARE_MAX_B64_LEN:
                    self.root.after(0, lambda: self.screen_status_var.set("Ekran çok büyük, küçültüldü"))
                    time.sleep(SCREEN_SHARE_INTERVAL_SEC)
                    continue

                frame_id = str(uuid.uuid4())
                total = (len(b64) + SCREEN_SHARE_CHUNK_SIZE - 1) // SCREEN_SHARE_CHUNK_SIZE
                payload_base = {
                    "frame_id": frame_id,
                    "total": total,
                    "name": f"screen_{int(time.time())}.jpg",
                    "w": working.width,
                    "h": working.height,
                }

                for idx in range(total):
                    if not self.screen_sharing or not self.current_room or not self.running:
                        break
                    chunk = b64[idx * SCREEN_SHARE_CHUNK_SIZE:(idx + 1) * SCREEN_SHARE_CHUNK_SIZE]
                    packet = self._build_packet(
                        "SCREEN",
                        {
                            **payload_base,
                            "index": idx,
                            "chunk": chunk,
                        },
                    )
                    if len(json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) <= 65507:
                        self._send_packet(packet)

                self.root.after(0, lambda: self.screen_status_var.set(f"Ekran paylaşılıyor • {working.width}x{working.height}"))
                time.sleep(SCREEN_SHARE_INTERVAL_SEC)
            except Exception as exc:
                self.root.after(0, lambda: self.screen_status_var.set(f"Ekran paylaşım hatası: {exc}"))
                time.sleep(SCREEN_SHARE_INTERVAL_SEC)

    def _handle_screen_packet(self, pkt: dict, room: str, sender: str, data: dict):
        frame_id = str(data.get("frame_id") or "").strip()
        if not frame_id:
            return

        total = int(data.get("total") or 0)
        index = int(data.get("index") or 0)
        chunk = str(data.get("chunk") or "")
        width = int(data.get("w") or 0)
        height = int(data.get("h") or 0)

        entry = self.screen_buffers.get(frame_id)
        now = time.time()
        if not entry:
            entry = {
                "sender": sender or "Anon",
                "room": room,
                "ts": now,
                "total": max(total, 1),
                "width": width,
                "height": height,
                "chunks": {},
            }
            self.screen_buffers[frame_id] = entry
        entry["ts"] = now
        entry["sender"] = sender or entry.get("sender", "Anon")
        if total:
            entry["total"] = total
        if width:
            entry["width"] = width
        if height:
            entry["height"] = height
        entry["chunks"][index] = chunk

        if len(entry["chunks"]) >= entry["total"]:
            try:
                ordered = [entry["chunks"][i] for i in range(entry["total"])]
                sender_name = entry["sender"]
                threading.Thread(target=self._decode_screen_frame, args=(ordered, sender_name), daemon=True).start()
            except KeyError:
                pass
            finally:
                self.screen_buffers.pop(frame_id, None)

    def _decode_screen_frame(self, ordered_chunks: list, sender: str):
        try:
            b64 = "".join(ordered_chunks)
            raw = base64.b64decode(b64.encode("ascii"))
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            
            self.root.after(0, self._set_screen_preview, img, sender)
        except Exception:
            pass

    def _set_screen_preview(self, img: Image.Image | None, sender: str | None):
        if img is None:
            self.screen_status_var.set("Ekran paylaşımı yok")
            self.screen_preview_photo = None
            if self.viewer_window and self.viewer_window.winfo_exists():
                self.viewer_window.destroy()
            self.viewer_window = None
            self.viewer_label = None
            return

        self.last_screen_ts = time.time()

        if not self.viewer_window or not self.viewer_window.winfo_exists():
            self.viewer_window = tk.Toplevel(self.root)
            self.viewer_window.title(f"{sender} - Ekran Yayını")
            self.viewer_window.geometry("1024x768")
            self.viewer_window.configure(bg=BG)
            self.viewer_label = tk.Label(self.viewer_window, bg=BG)
            self.viewer_label.pack(fill=tk.BOTH, expand=True)

            def on_close():
                self.viewer_window.destroy()
                self.viewer_window = None
            self.viewer_window.protocol("WM_DELETE_WINDOW", on_close)

        win_w = self.viewer_window.winfo_width()
        win_h = self.viewer_window.winfo_height()
        
        if win_w > 10 and win_h > 10:
            try:
                res_filter = Image.Resampling.LANCZOS
            except AttributeError:
                res_filter = Image.LANCZOS
            
            display_img = img.copy()
            display_img.thumbnail((win_w, win_h), res_filter)
        else:
            display_img = img

        photo = ImageTk.PhotoImage(display_img)
        self.screen_preview_photo = photo
        self.viewer_label.configure(image=photo)
        self.viewer_label.image = photo
        
        self.screen_status_var.set(f"{sender} ekran paylaşıyor")
        self.current_screen_sender = sender
        self.current_screen_ts = time.time()

    def _prune_screen_buffers(self):
        if not self.screen_buffers:
            return
        now = time.time()
        for frame_id in list(self.screen_buffers.keys()):
            if now - self.screen_buffers[frame_id].get("ts", now) > SCREEN_BUFFER_TTL:
                self.screen_buffers.pop(frame_id, None)

    # ---------------------------- Packet Handling ----------------------------
    def _process_packet(self, pkt: dict):
        if not isinstance(pkt, dict) or pkt.get("v") not in {3, 4}:
            return

        kind = str(pkt.get("type") or "").upper()
        packet_id = str(pkt.get("id") or "")
        room = str(pkt.get("room") or "").strip()
        sender = str(pkt.get("user") or "").strip()
        target = str(pkt.get("target") or "").strip()
        data = pkt.get("data") or {}

        if packet_id and packet_id in self.seen_packet_ids:
            return
        if sender and sender == self.username_var.get().strip() and kind in {"MSG", "IMG", "JOIN", "PART", "PING", "AUDIO", "SCREEN"}:
            return
        if target and target != self.username_var.get().strip():
            return
        if room:
            self.known_rooms[room] = time.time()

        if sender and room:
            self.room_users[room][sender] = time.time()
            if sender not in self.room_join_times[room]:
                self.room_join_times[room][sender] = time.time()

        if kind == "OWNER" and room:
            announced = str(data.get("owner") or sender or "").strip()
            if announced and announced in self.room_users.get(room, {}):
                self.room_owner[room] = announced
            self._refresh_sidebar()
            return

        if kind in {"JOIN", "PART", "PING"} and room:
            if kind == "PART" and sender:
                self.room_users[room].pop(sender, None)
                self.room_join_times[room].pop(sender, None)
                if room == self.current_room and sender != self.username_var.get().strip():
                    self._system_message(f"{sender} odadan ayrıldı.", WARN)
            if kind == "JOIN" and sender:
                if room == self.current_room and sender != self.username_var.get().strip():
                    self._system_message(f"{sender} odaya girdi.", SUCCESS)
            
            self._recalculate_room_owner(room)
            self._refresh_sidebar()
            return

        if room != self.current_room:
            return

        if sender in self.banned_users.get(room, set()) and kind in {"MSG", "IMG", "AUDIO", "HISTORY", "SCREEN"}:
            return

        if kind == "HISTORY_REQ":
            if room and self._is_owner(room):
                self._send_history_to(target)
            return

        if kind == "HISTORY":
            items = data if isinstance(data, list) else []
            for raw in items:
                if not isinstance(raw, dict):
                    continue
                item_id = str(raw.get("item_id") or raw.get("id") or "")
                if not item_id or item_id in self.seen_packet_ids:
                    continue
                if str(raw.get("sender") or "") == self.username_var.get().strip():
                    continue
                self.seen_packet_ids.add(item_id)
                item_kind = str(raw.get("kind") or "MSG").upper()
                ts = float(raw.get("ts") or time.time())

                if item_kind == "IMG":
                    item = ChatItem(
                        item_id=item_id,
                        kind="IMG",
                        sender=str(raw.get("sender") or "Anon"),
                        ts=ts,
                        room=room,
                        image_b64=str(raw.get("image_b64") or ""),
                        image_name=str(raw.get("image_name") or "image.jpg")
                    )
                    self.room_history[room].append(item)
                    self._append_image_message(item)

                elif item_kind == "AUDIO":
                    item = ChatItem(
                        item_id=item_id,
                        kind="AUDIO",
                        sender=str(raw.get("sender") or "Anon"),
                        ts=ts,
                        room=room,
                        audio_b64=str(raw.get("audio_b64") or ""),
                        audio_name=str(raw.get("audio_name") or "voice.audio"),
                        audio_sr=int(raw.get("audio_sr") or AUDIO_SR),
                        audio_codec=str(raw.get("audio_codec") or "zlib_pcm16"),
                        audio_sec=float(raw.get("audio_sec") or 0.0)
                    )
                    self.room_history[room].append(item)
                    self._append_audio_message(item)

                else:
                    item = ChatItem(
                        item_id=item_id,
                        kind="MSG",
                        sender=str(raw.get("sender") or "Anon"),
                        ts=ts,
                        room=room,
                        text=str(raw.get("text") or "")
                    )
                    self.room_history[room].append(item)
                    self._append_text_message(item)

            self.chat_subtitle.config(text=f"Kurucu: {self.room_owner.get(room, 'bilinmiyor')}")
            return

        if kind == "MSG":
            text = str(data.get("text") or "")
            item = ChatItem(
                item_id=packet_id or str(uuid.uuid4()),
                kind="MSG",
                sender=sender or "Anon",
                ts=float(pkt.get("ts") or time.time()),
                room=room,
                text=text
            )
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_text_message(item)
            self._show_notification("Yeni Mesaj", f"{sender}: {text[:20]}{'...' if len(text)>20 else ''}")
            return

        if kind == "IMG":
            item = ChatItem(
                item_id=packet_id or str(uuid.uuid4()),
                kind="IMG",
                sender=sender or "Anon",
                ts=float(pkt.get("ts") or time.time()),
                room=room,
                image_b64=str(data.get("b64") or ""),
                image_name=str(data.get("name") or "image.jpg")
            )
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_image_message(item)
            self._show_notification("Yeni Fotoğraf", f"{sender} bir fotoğraf paylaştı.")
            return

        if kind == "AUDIO":
            item = ChatItem(
                item_id=packet_id or str(uuid.uuid4()),
                kind="AUDIO",
                sender=sender or "Anon",
                ts=float(pkt.get("ts") or time.time()),
                room=room,
                audio_b64=str(data.get("b64") or ""),
                audio_name=str(data.get("name") or "voice.audio"),
                audio_sr=int(data.get("sr") or AUDIO_SR),
                audio_codec=str(data.get("codec") or "zlib_pcm16"),
                audio_sec=float(data.get("duration") or 0.0)
            )
            self.seen_packet_ids.add(item.item_id)
            self.room_history[room].append(item)
            self._append_audio_message(item)
            self._show_notification("Sesli Mesaj", f"{sender} bir sesli mesaj gönderdi.")
            return

        if kind == "SCREEN":
            self._handle_screen_packet(pkt, room, sender or "Anon", data if isinstance(data, dict) else {})
            return

        if kind == "BAN" and self._is_owner(room, sender):
            victim = str(data.get("target_user") or target or "").strip()
            if victim:
                self.banned_users[room].add(victim)
                self._purge_user_messages(room, victim)
                if victim == self.username_var.get().strip():
                    self._system_message("Bu odadan banlandın.", DANGER)
                    self.leave_room()
                else:
                    self._system_message(f"🔨 {victim} banlandı.", DANGER)
            return

        if kind == "PURGE" and self._is_owner(room, sender):
            victim = str(data.get("target_user") or target or "").strip()
            if victim:
                self._purge_user_messages(room, victim)
                self._system_message(f"🧹 {victim} kullanıcısının mesajları temizlendi.", WARN)
            return

        if kind == "CLEAR" and self._is_owner(room, sender):
            self.room_history[room].clear()
            self._clear_chat()
            self._system_message("Tüm mesaj geçmişi temizlendi.", DANGER)
            return

    def _send_history_to(self, target: str):
        if not self.current_room or not target:
            return
        payload = []
        for item in list(self.room_history[self.current_room])[-MAX_HISTORY:]:
            payload.append({
                "item_id": item.item_id,
                "kind": item.kind,
                "sender": item.sender,
                "ts": item.ts,
                "text": item.text,
                "image_b64": item.image_b64,
                "image_name": item.image_name,
                "audio_b64": item.audio_b64,
                "audio_name": item.audio_name,
                "audio_sr": item.audio_sr,
                "audio_codec": item.audio_codec,
                "audio_sec": item.audio_sec,
            })
        if payload:
            self._send_packet(self._build_packet("HISTORY", payload, target=target))

    # ---------------------------- Moderation ----------------------------
    def _selected_user_from_list(self):
        try:
            idx = self.users_list.curselection()
            if not idx:
                return None
            text = self.users_list.get(idx[0]).strip()
            if text.startswith("👑 "):
                text = text[2:].strip()
            elif text.startswith("👤 "):
                text = text[2:].strip()
            if text.endswith(" (Sen)"):
                text = text[:-6].strip()
            return text
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

        room = self.current_room
        is_owner = self._is_owner(room)

        try:
            self.user_menu.entryconfig(1, state=tk.NORMAL if is_owner and self.selected_user and self.selected_user != self.username_var.get().strip() else tk.DISABLED)
            self.user_menu.entryconfig(2, state=tk.NORMAL if is_owner and self.selected_user and self.selected_user != self.username_var.get().strip() else tk.DISABLED)
        except tk.TclError:
            pass

        self.user_menu.tk_popup(event.x_root, event.y_root)

    def _show_selected_user_info(self):
        user = self.selected_user or self._selected_user_from_list()
        if not user or not self.current_room:
            return
        room = self.current_room
        msgs = [x for x in list(self.room_history[room]) if x.sender == user]
        last_seen = self.room_users[room].get(user)
        info = (
            f"Kullanıcı: {user}\n"
            f"Oda: {room}\n"
            f"Mesaj sayısı: {len(msgs)}\n"
            f"Aktif: {'Evet' if last_seen and time.time() - last_seen < STALE_USER_SEC else 'Hayır'}"
        )
        messagebox.showinfo("Kullanıcı Bilgisi", info)

    def _ban_user(self, user: str):
        if not user or not self.current_room or user == self.username_var.get().strip():
            return
        if not self._is_owner(self.current_room):
            messagebox.showwarning("Yetki yok", "Bu işlem için oda kurucusu olmalısın.")
            return
        self.banned_users[self.current_room].add(user)
        self._purge_user_messages(self.current_room, user)
        self._send_packet(self._build_packet("BAN", {"target_user": user}, target=user))
        self._send_packet(self._build_packet("BAN", {"target_user": user}))
        self._system_message(f"🔨 {user} banlandı.", DANGER)

    def _ban_selected_user_cmd(self):
        user = self.selected_user or self._selected_user_from_list()
        if user and messagebox.askyesno("Banla", f"{user} odadan banlansın mı?"):
            self._ban_user(user)

    def _purge_user_messages_cmd(self, user: str):
        if not user or not self.current_room or user == self.username_var.get().strip():
            return
        if not self._is_owner(self.current_room):
            messagebox.showwarning("Yetki yok", "Bu işlem için oda kurucusu olmalısın.")
            return
        self._purge_user_messages(self.current_room, user)
        self._send_packet(self._build_packet("PURGE", {"target_user": user}))
        self._system_message(f"🧹 {user} mesajları silindi.", WARN)

    def _purge_selected_user_messages(self):
        user = self.selected_user or self._selected_user_from_list()
        if user and messagebox.askyesno("Temizle", f"{user} mesajları silinsin mi?"):
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
            messagebox.showwarning("Yetki yok", "Bu işlem için oda kurucusu olmalısın.")
            return
        self.room_history[self.current_room].clear()
        self._clear_chat()
        self._system_message("Tüm geçmiş temizlendi.", DANGER)
        self._send_packet(self._build_packet("CLEAR", {"all": True}))

    def _purge_user_messages(self, room: str, user: str):
        if not room or not user:
            return
        kept = deque([x for x in self.room_history[room] if x.sender != user], maxlen=MAX_HISTORY)
        self.room_history[room] = kept
        self._render_history(room)

    # ---------------------------- Rendering ----------------------------
    def _clear_chat(self):
        self.chat_box.config(state=tk.NORMAL)
        try:
            self.chat_box.delete("1.0", tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)
        self.image_refs.clear()
        self.embed_refs.clear()

    def _render_history(self, room: str):
        if not room:
            return
        self._clear_chat()
        for item in self.room_history[room]:
            if item.kind == "IMG":
                self._append_image_message(item)
            elif item.kind == "AUDIO":
                self._append_audio_message(item)
            else:
                self._append_text_message(item)
        self.chat_subtitle.config(text=f"Kurucu: {self.room_owner.get(room, 'bilinmiyor')}")

    def _fmt_time(self, ts: float | None):
        return time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "Bilinmiyor"

    def _name_tag(self, sender: str):
        me = self.username_var.get().strip()
        if sender == me:
            return "self_name"
        if sender == self.room_owner.get(self.current_room, ""):
            return "owner_name"
        return "user_name"

    def _append_text_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            self.chat_box.insert(tk.END, f"[{self._fmt_time(item.ts)}] ", "time")
            self.chat_box.insert(tk.END, item.sender, self._name_tag(item.sender))
            if item.sender == self.room_owner.get(self.current_room, ""):
                self.chat_box.insert(tk.END, " 👑", "owner_name")
            self.chat_box.insert(tk.END, f": {item.text}\n\n", "msg")
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    def _append_image_message(self, item: ChatItem):
        self.chat_box.config(state=tk.NORMAL)
        try:
            self.chat_box.insert(tk.END, f"[{self._fmt_time(item.ts)}] ", "time")
            self.chat_box.insert(tk.END, item.sender, self._name_tag(item.sender))
            if item.sender == self.room_owner.get(self.current_room, ""):
                self.chat_box.insert(tk.END, " 👑", "owner_name")
            self.chat_box.insert(tk.END, f": {item.image_name}\n", "msg")
            try:
                raw = base64.b64decode(item.image_b64.encode("ascii"))
                img = Image.open(io.BytesIO(raw))
                photo = ImageTk.PhotoImage(img)
                self.image_refs.append(photo)
                self.chat_box.image_create(tk.END, image=photo)
                self.chat_box.insert(tk.END, "\n\n")
            except Exception:
                self.chat_box.insert(tk.END, "[Fotoğraf gösterilemedi]\n\n", "warn")
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    def _system_message(self, text: str, color: str = MUTED):
        self.chat_box.config(state=tk.NORMAL)
        try:
            tag = {MUTED: "sys", WARN: "warn", DANGER: "danger", SUCCESS: "sys", GOLD: "sys"}.get(color, "sys")
            self.chat_box.insert(tk.END, f"• {text}\n", tag)
            self.chat_box.tag_configure(tag, foreground=color)
            self.chat_box.see(tk.END)
        finally:
            self.chat_box.config(state=tk.DISABLED)

    # ---------------------------- Sidebar ----------------------------
    def _refresh_sidebar(self):
        self.rooms_list.delete(0, tk.END)
        self.users_list.delete(0, tk.END)

        now = time.time()
        rooms = [r for r, seen in self.known_rooms.items() if now - seen <= STALE_ROOM_SEC]
        rooms = sorted(set(rooms), key=str.lower)
        for room in rooms:
            self.rooms_list.insert(tk.END, room)

        if self.current_room:
            users = self.room_users.get(self.current_room, {})
            owner = self.room_owner.get(self.current_room, "")
            self.chat_subtitle.config(text=f"Kurucu: {owner if owner else 'bilinmiyor'}")

            me = self.username_var.get().strip()
            display = [me] if me else []
            for user in sorted(users.keys(), key=str.lower):
                if user not in display:
                    display.append(user)

            for user in display:
                prefix = "👑 " if user == owner else "👤 "
                suffix = " (Sen)" if user == me else ""
                self.users_list.insert(tk.END, f"{prefix}{user}{suffix}")
        else:
            self.users_list.insert(tk.END, "Oda seçilmedi")

        self._animate_status()

    def _on_room_click(self, event):
        idx = self.rooms_list.nearest(event.y)
        if idx < 0 or idx >= self.rooms_list.size():
            return
        room = self.rooms_list.get(idx).strip()
        if room and room != self.current_room:
            self.join_room(room)

    # ---------------------------- Helpers ----------------------------
    def _is_owner(self, room: str, sender: str | None = None):
        if not room:
            return False
        owner = self.room_owner.get(room)
        sender = sender or self.username_var.get().strip()
        return bool(owner and owner == sender)

    def _tick_ui(self):
        if not self.running:
            return
        self._refresh_sidebar()
        self.root.after(UI_REFRESH_MS, self._tick_ui)


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernGhostChat(root)
    root.mainloop()
