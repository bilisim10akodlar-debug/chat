import os
import base64
import io
import json
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
    from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont
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

# Kayıt dosyası
KAYIT_DOSYASI = "test_cozuldu.txt"

sorular = [
    {
        "soru": "1. Turk musunuz?",
        "siklar": {"a": "Evet", "b": "Hayir", "c": "K_rdum ", "d": "K_urdum"},
        "dogru_cevap": "a",
        "sayi": "1"
    },
]

dogru_skor = 0
turkmu_durumu = True

def testi_baslat():
    global dogru_skor, turkmu_durumu
    print("*" * 50)
    print("SİSTEME GİRİŞ YAPMADAN ÖNCE TESTİ ÇÖZMENİZ GEREKMEKTEDİR")
    print("*" * 50, "\n")
    dogru_sayisi = 0
    toplam_soru = len(sorular)
    for index, soru_verisi in enumerate(sorular, start=1):
        print(f"\n--- SORU {index} / {toplam_soru} ---")
        print(soru_verisi["soru"])
        for harf, metin in soru_verisi["siklar"].items():
            print(f"{harf.upper()}) {metin}")
        while True:
            cevap = input("Cevabınız (A/B/C/D): ").strip().lower()
            if cevap in ["a", "b", "c", "d"]:
                break
            print("Lütfen geçerli bir şık giriniz!")
        if cevap == soru_verisi["dogru_cevap"]:
            print("Doğru!")
            dogru_sayisi += 1
        else:
            if index == 1:
                print("Bilgilendirme: İlk soruya verilen cevap sistem analizini etkileyecektir.")
                turkmu_durumu = False
            else:
                print(f"Yanlış! Doğru cevap: {soru_verisi['dogru_cevap'].upper()}")
    dogru_skor = dogru_sayisi
    print("-" * 50)
    print(f"Test tamamlandı! Skorunuz: {dogru_skor} / {toplam_soru}")
    print("-" * 50)
    ana_sistemi_calistir()

def analiz():
    if turkmu_durumu:
        print("Analiz sonucu: Geçti (Kriter 2)")
        return True
    else:
        print("Analiz sonucu: Başarısız")
        return False

def ana_sistemi_calistir():
    print(f"\nSistem Başlatılıyor... Durum: {turkmu_durumu}, Skor: {dogru_skor}")

    if analiz():
        print("Sistem başarıyla açıldı.")

        if os.name == 'nt':
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        subprocess.run(["taskkill", "/F", "/IM", "student.exe"])

        APP_TITLE = "OPSI v9.0"
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

        AUDIO_SR = 8000
        AUDIO_MIN_SEC = 0.2
        MAX_AUDIO_B64_LEN = 180000
        MAX_PACKET_BYTES = 60000

        SCREEN_SHARE_INTERVAL_SEC = 0.04
        SCREEN_SHARE_MAX_SIDE = 1920
        SCREEN_SHARE_JPEG_QUALITY = 80
        SCREEN_SHARE_MAX_B64_LEN = 400000
        SCREEN_SHARE_CHUNK_SIZE = 45000
        SCREEN_BUFFER_TTL = 6.0

        # ===== Discord Renk Paleti =====
        BG       = "#313338"   # Ana chat arka planı
        PANEL    = "#2B2D31"   # Sol/sağ sidebar
        PANEL_2  = "#313338"   # Chat alanı (BG ile aynı)
        PANEL_3  = "#1E1F22"   # En koyu (border, alt bar)
        INPUT    = "#383A40"   # Input arka planı
        HOVER    = "#35373C"   # Hover durumu
        BORDER   = "#1E1F22"   # Ayraçlar
        TEXT     = "#DCDDDE"   # Normal metin
        MUTED    = "#949BA4"   # Soluk metin
        ACCENT   = "#5865F2"   # Discord moru (blurple)
        ACCENT_2 = "#3BA55C"   # Yeşil
        SUCCESS  = "#3BA55C"
        WARN     = "#FAA61A"
        DANGER   = "#ED4245"
        GOLD     = "#FAA61A"
        USER_BG  = "#232428"   # Kullanıcı paneli arka planı

        AVATAR_PALETTE = [
            "#5865F2", "#57F287", "#FEE75C", "#EB459E",
            "#ED4245", "#3BA55C", "#FAA61A", "#5DA0D0",
            "#9B59B6", "#E67E22"
        ]

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
                self.root.geometry("1150x720")
                self.root.minsize(820, 520)
                self.root.configure(bg=BORDER)

                self.root.protocol("WM_DELETE_WINDOW", self._ignore_close)
                self.root.bind("<Alt-F4>", self._ignore_close)

                self.username_var    = tk.StringVar(value=f"kullanici_{uuid.uuid4().hex[:4]}")
                self.room_entry_var  = tk.StringVar(value="genel-sohbet")
                self.status_var      = tk.StringVar(value="Bağlı değil")
                self.audio_status_var  = tk.StringVar(value="")
                self.screen_status_var = tk.StringVar(value="")

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

                self.is_recording     = False
                self.audio_frames     = []
                self.audio_stream     = None
                self.record_start_ts  = 0.0

                self.screen_sharing       = False
                self.screen_thread        = None
                self.screen_buffers       = {}
                self.screen_preview_photo = None
                self.current_screen_sender = ""
                self.current_screen_ts    = 0.0
                self.viewer_window        = None
                self.viewer_label         = None
                self.last_screen_ts       = 0.0

                # ---- Avatar sistemi ----
                self.avatar_cache    = {}   # "username_size" -> ImageTk.PhotoImage
                self.avatar_b64_map  = {}   # username -> b64 string (ham resim)
                self.avatar_refs     = []   # GC koruması

                # Mesaj gruplama (Discord gibi)
                self._last_chat_sender = ""
                self._last_chat_ts     = 0.0

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
                if self.root.focus_displayof() is not None:
                    return
                if hasattr(self, "active_toast") and self.active_toast.winfo_exists():
                    self.active_toast.destroy()
                self.active_toast = tk.Toplevel(self.root)
                self.active_toast.overrideredirect(True)
                self.active_toast.attributes("-topmost", True)
                w, h = 300, 72
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                self.active_toast.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-70}")
                self.active_toast.configure(bg=PANEL_3)

                tk.Frame(self.active_toast, bg=ACCENT, width=4).pack(side=tk.LEFT, fill=tk.Y)
                c = tk.Frame(self.active_toast, bg=PANEL_3)
                c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=8)
                tk.Label(c, text=title, bg=PANEL_3, fg=TEXT,
                         font=("Segoe UI", 10, "bold")).pack(anchor="w")
                tk.Label(c, text=message, bg=PANEL_3, fg=MUTED,
                         font=("Segoe UI", 9)).pack(anchor="w")
                self.root.after(3500, lambda: (
                    self.active_toast.destroy()
                    if hasattr(self, "active_toast") and self.active_toast.winfo_exists()
                    else None
                ))

            # ==================== AVATAR SİSTEMİ ====================

            def _avatar_color(self, username: str) -> tuple:
                """Kullanıcı adına göre sabit renk (RGB tuple)."""
                hex_c = AVATAR_PALETTE[hash(username) % len(AVATAR_PALETTE)]
                return (int(hex_c[1:3],16), int(hex_c[3:5],16), int(hex_c[5:7],16))

            def _make_circle_from_pil(self, img: Image.Image, size: int) -> ImageTk.PhotoImage:
                """PIL resmini yuvarlak avatar'a çevirir."""
                img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse([0, 0, size-1, size-1], fill=255)
                result = Image.new("RGBA", (size, size), (0,0,0,0))
                result.paste(img, mask=mask)
                return ImageTk.PhotoImage(result)

            def _make_default_avatar(self, username: str, size: int) -> ImageTk.PhotoImage:
                """Baş harf + renkli daire varsayılan avatar."""
                r, g, b = self._avatar_color(username)
                img = Image.new("RGBA", (size, size), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                draw.ellipse([0, 0, size-1, size-1], fill=(r, g, b, 255))

                initial = (username[0].upper() if username else "?")
                font_size = max(10, size // 2)
                font = None
                for font_path in ["arial.ttf", "Arial.ttf",
                                  "/System/Library/Fonts/Helvetica.ttc",
                                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except Exception:
                        pass
                if font is None:
                    font = ImageFont.load_default()

                try:
                    bbox = draw.textbbox((0, 0), initial, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    x = (size - tw) // 2 - bbox[0]
                    y = (size - th) // 2 - bbox[1]
                except Exception:
                    x, y = size // 4, size // 4

                draw.text((x, y), initial, fill=(255,255,255,230), font=font)
                return ImageTk.PhotoImage(img)

            def _get_avatar_image(self, username: str, size: int = 40) -> ImageTk.PhotoImage:
                """Avatar PhotoImage döndürür (önbellekli)."""
                key = f"{username}_{size}"
                if key in self.avatar_cache:
                    return self.avatar_cache[key]

                if username in self.avatar_b64_map:
                    try:
                        raw = base64.b64decode(self.avatar_b64_map[username])
                        pil_img = Image.open(io.BytesIO(raw))
                        photo = self._make_circle_from_pil(pil_img, size)
                        self.avatar_cache[key] = photo
                        return photo
                    except Exception:
                        pass

                photo = self._make_default_avatar(username, size)
                self.avatar_cache[key] = photo
                return photo

            def _pick_profile_photo(self):
                """Kullanıcı kendi profil fotoğrafını seçer."""
                path = filedialog.askopenfilename(
                    title="Profil fotoğrafı seç",
                    filetypes=[("Resimler", "*.png *.jpg *.jpeg *.webp *.bmp"), ("Tümü", "*.*")]
                )
                if not path:
                    return
                try:
                    pil_img = Image.open(path).convert("RGB")
                    pil_img.thumbnail((128, 128))
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=85)
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

                    me = self.username_var.get().strip()
                    self.avatar_b64_map[me] = b64

                    # Önbelleği temizle (kendi avatarı için)
                    for k in list(self.avatar_cache.keys()):
                        if k.startswith(f"{me}_"):
                            del self.avatar_cache[k]

                    self._update_own_avatar_display()

                    # Ağa yayınla
                    if self.current_room and len(b64) <= 28000:
                        self._send_packet(self._build_packet("AVATAR", {"b64": b64}))

                    messagebox.showinfo("Profil", "Profil fotoğrafı güncellendi!")
                except Exception as exc:
                    messagebox.showerror("Hata", f"Fotoğraf yüklenemedi:\n{exc}")

            def _update_own_avatar_display(self):
                """Alt kullanıcı panelindeki avatarı günceller."""
                me = self.username_var.get().strip()
                if not me:
                    return
                photo = self._get_avatar_image(me, 32)
                self.avatar_refs.append(photo)
                if hasattr(self, "user_avatar_lbl"):
                    self.user_avatar_lbl.config(image=photo)
                    self.user_avatar_lbl.image = photo

            # ==================== ARAYÜZ ====================

            def _build_ui(self):
                """Ana üç sütunlu Discord layout."""
                container = tk.Frame(self.root, bg=BORDER)
                container.pack(fill=tk.BOTH, expand=True)

                # SOL SIDEBAR (240px)
                self.sidebar = tk.Frame(container, bg=PANEL, width=240)
                self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
                self.sidebar.pack_propagate(False)

                tk.Frame(container, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

                # SAĞ ÜYELER PANELİ (210px)
                self.members_panel = tk.Frame(container, bg=PANEL, width=210)
                self.members_panel.pack(side=tk.RIGHT, fill=tk.Y)

                tk.Frame(container, bg=BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y)

                # ORTA ANA ALAN
                self.main = tk.Frame(container, bg=BG)
                self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                self._build_sidebar()
                self._build_members_panel()
                self._build_main_area()

            # ---- Sol Sidebar ----
            def _build_sidebar(self):
                sb = self.sidebar

                # Sunucu başlığı
                srv_header = tk.Frame(sb, bg=PANEL, height=48)
                srv_header.pack(fill=tk.X)
                srv_header.pack_propagate(False)
                tk.Label(srv_header, text="  ⚡ OPSI Sunucusu", bg=PANEL, fg=TEXT,
                         font=("Segoe UI", 13, "bold"), anchor="w").pack(
                    fill=tk.X, padx=4, pady=12)
                tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X)

                # Kanallar bölümü başlığı
                ch_hdr = tk.Frame(sb, bg=PANEL)
                ch_hdr.pack(fill=tk.X, padx=8, pady=(10, 2))
                tk.Label(ch_hdr, text="METİN KANALLARI", bg=PANEL, fg=MUTED,
                         font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
                add_lbl = tk.Label(ch_hdr, text=" ＋ ", bg=PANEL, fg=MUTED,
                                   font=("Segoe UI", 14), cursor="hand2")
                add_lbl.pack(side=tk.RIGHT)
                add_lbl.bind("<Enter>", lambda e: add_lbl.config(fg=TEXT))
                add_lbl.bind("<Leave>", lambda e: add_lbl.config(fg=MUTED))
                add_lbl.bind("<Button-1>", lambda e: self.room_entry.focus_set())

                # Oda listesi
                self.rooms_list = tk.Listbox(
                    sb, bg=PANEL, fg=MUTED, bd=0,
                    highlightthickness=0,
                    selectbackground=HOVER,
                    selectforeground=TEXT,
                    activestyle="none",
                    font=("Segoe UI", 11),
                    relief=tk.FLAT,
                    height=14
                )
                self.rooms_list.pack(fill=tk.BOTH, expand=True, padx=4)
                self.rooms_list.bind("<ButtonRelease-1>", self._on_room_click)

                # Oda ekle / katıl alanı
                tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X)
                join_area = tk.Frame(sb, bg="#1E1F22")
                join_area.pack(fill=tk.X)

                inner = tk.Frame(join_area, bg="#1E1F22")
                inner.pack(fill=tk.X, padx=10, pady=(8, 4))
                tk.Label(inner, text="# oda adı", bg="#1E1F22", fg=MUTED,
                         font=("Segoe UI", 9)).pack(anchor="w")
                self.room_entry = tk.Entry(
                    inner, textvariable=self.room_entry_var,
                    bg=INPUT, fg=TEXT, insertbackground=TEXT,
                    bd=0, font=("Segoe UI", 11), relief=tk.FLAT
                )
                self.room_entry.pack(fill=tk.X, ipady=7, pady=(2, 0))
                self.room_entry.bind("<Return>", lambda e: self._join_from_entry())

                btn_row = tk.Frame(join_area, bg="#1E1F22")
                btn_row.pack(fill=tk.X, padx=10, pady=(4, 8))
                self.join_btn = tk.Button(
                    btn_row, text="Katıl", bg=ACCENT, fg="white",
                    bd=0, font=("Segoe UI", 10, "bold"),
                    padx=0, pady=6, cursor="hand2",
                    activebackground="#4752C4",
                    command=self._join_from_entry
                )
                self.join_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
                self.leave_btn = tk.Button(
                    btn_row, text="Ayrıl", bg=DANGER, fg="white",
                    bd=0, font=("Segoe UI", 10),
                    padx=0, pady=6, cursor="hand2",
                    state=tk.DISABLED,
                    activebackground="#A03032",
                    command=self.leave_room
                )
                self.leave_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

                # Alt kullanıcı paneli
                tk.Frame(sb, bg=BORDER, height=1).pack(fill=tk.X)
                self.user_panel = tk.Frame(sb, bg=USER_BG, height=52)
                self.user_panel.pack(fill=tk.X, side=tk.BOTTOM)
                self.user_panel.pack_propagate(False)
                self._build_user_panel()

            def _build_user_panel(self):
                """Alt kullanıcı alanı (Discord'daki gibi)."""
                p = self.user_panel
                me = self.username_var.get().strip()

                # Avatar (tıklanınca fotoğraf seç)
                av = self._get_avatar_image(me, 32)
                self.avatar_refs.append(av)
                self.user_avatar_lbl = tk.Label(p, image=av, bg=USER_BG, cursor="hand2")
                self.user_avatar_lbl.image = av
                self.user_avatar_lbl.pack(side=tk.LEFT, padx=(10, 6), pady=10)
                self.user_avatar_lbl.bind("<Button-1>", lambda e: self._pick_profile_photo())
                self.user_avatar_lbl.bind("<Enter>", lambda e: self.user_avatar_lbl.config(
                    relief=tk.SOLID, bd=2))
                self.user_avatar_lbl.bind("<Leave>", lambda e: self.user_avatar_lbl.config(
                    relief=tk.FLAT, bd=0))

                # İsim + durum
                name_f = tk.Frame(p, bg=USER_BG)
                name_f.pack(side=tk.LEFT, fill=tk.Y, pady=10)
                self.user_name_lbl = tk.Label(
                    name_f, text=me, bg=USER_BG, fg=TEXT,
                    font=("Segoe UI", 10, "bold"), anchor="w"
                )
                self.user_name_lbl.pack(anchor="w")
                self.user_status_lbl = tk.Label(
                    name_f, textvariable=self.status_var,
                    bg=USER_BG, fg=MUTED, font=("Segoe UI", 8), anchor="w"
                )
                self.user_status_lbl.pack(anchor="w")

                # Sağ butonlar
                btn_f = tk.Frame(p, bg=USER_BG)
                btn_f.pack(side=tk.RIGHT, padx=8)

                for sym, tip, cmd in [
                    ("🎤", "Mikrofon", lambda: None),
                    ("⚙️", "Ayarlar",  self._show_settings),
                    ("✕",  "Çıkış",   self._app_exit),
                ]:
                    lbl = tk.Label(btn_f, text=sym, bg=USER_BG, fg=MUTED,
                                   font=("Segoe UI", 13), cursor="hand2")
                    lbl.pack(side=tk.LEFT, padx=3)
                    lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=TEXT))
                    lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=MUTED))
                    lbl.bind("<Button-1>", lambda e, c=cmd: c())

            # ---- Sağ Üyeler Paneli ----
            def _build_members_panel(self):
                mp = self.members_panel

                hdr = tk.Frame(mp, bg=PANEL, height=48)
                hdr.pack(fill=tk.X)
                hdr.pack_propagate(False)
                tk.Label(hdr, text="  ÜYELER", bg=PANEL, fg=MUTED,
                         font=("Segoe UI", 11, "bold"), anchor="w").pack(
                    fill=tk.X, padx=8, pady=14)
                tk.Frame(mp, bg=BORDER, height=1).pack(fill=tk.X)

                self.users_list = tk.Listbox(
                    mp, bg=PANEL, fg=TEXT, bd=0,
                    highlightthickness=0,
                    selectbackground=HOVER,
                    selectforeground=TEXT,
                    activestyle="none",
                    font=("Segoe UI", 10),
                    relief=tk.FLAT
                )
                self.users_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
                self.users_list.bind("<Button-3>", self._show_user_menu)
                self.users_list.bind("<ButtonRelease-1>", self._select_user)

                self.user_menu = tk.Menu(
                    self.root, tearoff=0, bg="#2C2F33", fg=TEXT,
                    activebackground=ACCENT, bd=0, relief=tk.FLAT
                )
                self.user_menu.add_command(label="  Bilgileri gör",      command=self._show_selected_user_info)
                self.user_menu.add_command(label="  Mesajlarını sil",     command=self._purge_selected_user_messages)
                self.user_menu.add_command(label="  Banla",               command=self._ban_selected_user_cmd)
                self.user_menu.add_separator()
                self.user_menu.add_command(label="  Adı kopyala",         command=self._copy_selected_user_name)

            # ---- Ana Chat Alanı ----
            def _build_main_area(self):
                main = self.main

                # Kanal başlığı
                ch_hdr = tk.Frame(main, bg=BG, height=48)
                ch_hdr.pack(fill=tk.X)
                ch_hdr.pack_propagate(False)
                tk.Frame(main, bg=BORDER, height=1).pack(fill=tk.X)

                hdr_left = tk.Frame(ch_hdr, bg=BG)
                hdr_left.pack(side=tk.LEFT, padx=16, pady=8)

                tk.Label(hdr_left, text="#", bg=BG, fg=MUTED,
                         font=("Segoe UI", 19, "bold")).pack(side=tk.LEFT)
                self.chat_title = tk.Label(hdr_left, text="oda seçilmedi", bg=BG, fg=TEXT,
                                           font=("Segoe UI", 15, "bold"))
                self.chat_title.pack(side=tk.LEFT, padx=(4, 0))

                # Dikey ayraç
                sep = tk.Frame(hdr_left, bg=MUTED, width=1, height=22)
                sep.pack(side=tk.LEFT, padx=14)

                self.chat_subtitle = tk.Label(hdr_left, text="Bir kanala katılın",
                                              bg=BG, fg=MUTED, font=("Segoe UI", 10))
                self.chat_subtitle.pack(side=tk.LEFT)

                # Sağ taraf (ekran paylaşım durumu)
                hdr_right = tk.Frame(ch_hdr, bg=BG)
                hdr_right.pack(side=tk.RIGHT, padx=16)
                tk.Label(hdr_right, textvariable=self.screen_status_var,
                         bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side=tk.RIGHT)

                # Chat kutusu
                self.chat_box = scrolledtext.ScrolledText(
                    main, bg=BG, fg=TEXT, insertbackground=TEXT,
                    bd=0, highlightthickness=0,
                    padx=16, pady=12,
                    font=("Segoe UI", 11),
                    wrap=tk.WORD, relief=tk.FLAT
                )
                self.chat_box.pack(fill=tk.BOTH, expand=True)
                self.chat_box.configure(state=tk.DISABLED)

                # Metin etiketleri (Discord tarzı)
                AVATAR_INDENT = 56
                self.chat_box.tag_configure("time",
                    foreground=MUTED, font=("Segoe UI", 9))
                self.chat_box.tag_configure("msg",
                    foreground=TEXT, font=("Segoe UI", 11),
                    lmargin1=AVATAR_INDENT, lmargin2=AVATAR_INDENT)
                self.chat_box.tag_configure("msg_cont",
                    foreground=TEXT, font=("Segoe UI", 11),
                    lmargin1=AVATAR_INDENT, lmargin2=AVATAR_INDENT)
                self.chat_box.tag_configure("sys",
                    foreground=MUTED, font=("Segoe UI", 9, "italic"),
                    lmargin1=16, lmargin2=16)
                self.chat_box.tag_configure("warn",
                    foreground=WARN, font=("Segoe UI", 9, "italic"),
                    lmargin1=16, lmargin2=16)
                self.chat_box.tag_configure("danger",
                    foreground=DANGER, font=("Segoe UI", 9, "italic"),
                    lmargin1=16, lmargin2=16)
                self.chat_box.tag_configure("self_name",
                    foreground="#FFFFFF", font=("Segoe UI", 11, "bold"))
                self.chat_box.tag_configure("user_name",
                    foreground=TEXT, font=("Segoe UI", 11, "bold"))
                self.chat_box.tag_configure("owner_name",
                    foreground=GOLD, font=("Segoe UI", 11, "bold"))
                self.chat_box.tag_configure("audio",
                    foreground=ACCENT_2, font=("Segoe UI", 11),
                    lmargin1=AVATAR_INDENT, lmargin2=AVATAR_INDENT)
                self.chat_box.tag_configure("owner_badge",
                    foreground=GOLD, font=("Segoe UI", 10))

                # Input alanı (Discord tarzı tek kutu)
                input_wrap = tk.Frame(main, bg=BG)
                input_wrap.pack(fill=tk.X, padx=16, pady=(4, 16))

                input_box = tk.Frame(input_wrap, bg=INPUT)
                input_box.pack(fill=tk.X)

                # Sol eylem butonları
                def _icon_btn(parent, text, cmd=None, hover_fg=TEXT):
                    lbl = tk.Label(parent, text=text, bg=INPUT, fg=MUTED,
                                   font=("Segoe UI", 15), cursor="hand2", padx=4)
                    lbl.pack(side=tk.LEFT, padx=(4, 0), pady=6)
                    lbl.bind("<Enter>", lambda e: lbl.config(fg=hover_fg))
                    lbl.bind("<Leave>", lambda e: lbl.config(fg=MUTED))
                    if cmd:
                        lbl.bind("<Button-1>", lambda e: cmd())
                    return lbl

                _icon_btn(input_box, "🖼️", self.send_image)
                self.screen_icon = _icon_btn(input_box, "🖥️", self._toggle_screen_share)

                # Mesaj giriş alanı
                self.msg_entry = tk.Entry(
                    input_box, bg=INPUT, fg=TEXT,
                    insertbackground=TEXT, bd=0,
                    font=("Segoe UI", 12), relief=tk.FLAT
                )
                self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=14, padx=8)
                self.msg_entry.bind("<Return>", lambda e: self.send_message())

                # Sağ butonlar
                self.mic_btn = tk.Label(
                    input_box, text="🎤", bg=INPUT, fg=MUTED,
                    font=("Segoe UI", 15), cursor="hand2", padx=4
                )
                self.mic_btn.pack(side=tk.LEFT, padx=(0, 4))
                self.mic_btn.bind("<Enter>", lambda e: self.mic_btn.config(fg=DANGER))
                self.mic_btn.bind("<Leave>", lambda e: self.mic_btn.config(
                    fg=DANGER if self.is_recording else MUTED))
                self.mic_btn.bind("<ButtonPress-1>",   self._start_audio_record)
                self.mic_btn.bind("<ButtonRelease-1>", self._stop_audio_record)

                self.send_btn = tk.Label(
                    input_box, text="➤", bg=INPUT, fg=ACCENT,
                    font=("Segoe UI", 15, "bold"), cursor="hand2", padx=8
                )
                self.send_btn.pack(side=tk.LEFT, padx=(0, 4))
                self.send_btn.bind("<Enter>",    lambda e: self.send_btn.config(fg="#7B89FF"))
                self.send_btn.bind("<Leave>",    lambda e: self.send_btn.config(fg=ACCENT))
                self.send_btn.bind("<Button-1>", lambda e: self.send_message())

                # Ses durum etiketi
                tk.Label(input_wrap, textvariable=self.audio_status_var,
                         bg=BG, fg=MUTED, font=("Segoe UI", 8, "italic")).pack(anchor="e")

                # Sahte buton referansları (eski kod uyumluluğu)
                self.photo_btn  = tk.Frame()
                self.send_btn_ttk = tk.Frame()

                self._toggle_inputs(False)
                self._system_message("OPSI'ye hoş geldiniz. Sol panelden bir kanala katılın.", MUTED)

            # ---- Ayarlar ----
            def _show_settings(self):
                if hasattr(self, "_swin") and self._swin.winfo_exists():
                    self._swin.lift()
                    return
                win = tk.Toplevel(self.root)
                win.title("Kullanıcı Ayarları")
                win.geometry("400x300")
                win.configure(bg=PANEL)
                win.resizable(False, False)
                self._swin = win

                def section(text):
                    tk.Label(win, text=text, bg=PANEL, fg=MUTED,
                             font=("Segoe UI", 10, "bold")).pack(
                        anchor="w", padx=24, pady=(16, 4))

                section("KULLANICI ADI")
                name_e = tk.Entry(win, textvariable=self.username_var,
                                  bg=INPUT, fg=TEXT, insertbackground=TEXT,
                                  bd=0, font=("Segoe UI", 12))
                name_e.pack(fill=tk.X, padx=24, ipady=8)

                section("PROFİL FOTOĞRAFI")
                tk.Button(win, text="  📷  Fotoğraf Seç...", bg=ACCENT, fg="white",
                          bd=0, font=("Segoe UI", 10), padx=16, pady=8,
                          cursor="hand2", activebackground="#4752C4",
                          command=lambda: (self._pick_profile_photo(), win.lift())
                          ).pack(anchor="w", padx=24)

                tk.Button(win, text="Kaydet & Kapat", bg=PANEL_3, fg=TEXT,
                          bd=0, font=("Segoe UI", 10), padx=16, pady=8,
                          cursor="hand2", command=win.destroy
                          ).pack(anchor="e", padx=24, pady=20)

            # ==================== TOGGLE INPUTS ====================

            def _toggle_inputs(self, state: bool):
                s = tk.NORMAL if state else tk.DISABLED
                self.msg_entry.config(state=s)
                lv_s = tk.NORMAL if state else tk.DISABLED
                self.leave_btn.config(state=lv_s)

                # Label-butonlar için renk değişimi
                active_fg = MUTED if not state else MUTED
                for w_name in ("screen_icon", "mic_btn", "send_btn"):
                    if hasattr(self, w_name):
                        w = getattr(self, w_name)
                        try:
                            w.config(state=s if isinstance(w, tk.Button) else tk.NORMAL)
                        except Exception:
                            pass

            def _animate_status(self):
                pass

            # ==================== MESAJ GÖRÜNTÜLEME ====================

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
                self.chat_subtitle.config(
                    text=f"Kurucu: {self.room_owner.get(room, 'bilinmiyor')}")

            def _fmt_time(self, ts):
                return time.strftime("%H:%M", time.localtime(ts)) if ts else ""

            def _name_tag(self, sender: str):
                me = self.username_var.get().strip()
                if sender == me:
                    return "self_name"
                if sender == self.room_owner.get(self.current_room, ""):
                    return "owner_name"
                return "user_name"

            def _should_group(self, sender: str, ts: float) -> bool:
                """Aynı kişinin mesajı 7 dakika içinde ise grupla (avatar/isim gösterme)."""
                if sender != self._last_chat_sender:
                    return False
                if not self._last_chat_ts or not ts:
                    return False
                return (ts - self._last_chat_ts) < 420

            def _insert_avatar_header(self, sender: str, ts: float):
                """Avatar + isim + zaman damgası satırı ekler."""
                self.chat_box.insert(tk.END, "\n")
                av = self._get_avatar_image(sender, 40)
                self.avatar_refs.append(av)
                self.chat_box.image_create(tk.END, image=av, padx=8, pady=6)
                self.chat_box.insert(tk.END, " ")
                self.chat_box.insert(tk.END, sender, self._name_tag(sender))
                if sender == self.room_owner.get(self.current_room, ""):
                    self.chat_box.insert(tk.END, " 👑", "owner_badge")
                self.chat_box.insert(tk.END, f"  {self._fmt_time(ts)}\n", "time")

            def _append_text_message(self, item: ChatItem):
                self.chat_box.config(state=tk.NORMAL)
                try:
                    grouped = self._should_group(item.sender, item.ts)
                    if not grouped:
                        self._insert_avatar_header(item.sender, item.ts)
                        self.chat_box.insert(tk.END, f"{item.text}\n", "msg")
                    else:
                        self.chat_box.insert(tk.END, f"{item.text}\n", "msg_cont")
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
                    self.chat_box.insert(tk.END, f"{item.image_name}\n", "msg")
                    try:
                        raw = base64.b64decode(item.image_b64.encode("ascii"))
                        img = Image.open(io.BytesIO(raw))
                        img.thumbnail((420, 320))
                        photo = ImageTk.PhotoImage(img)
                        self.image_refs.append(photo)
                        self.chat_box.image_create(tk.END, image=photo, padx=56, pady=4)
                        self.chat_box.insert(tk.END, "\n")
                    except Exception:
                        self.chat_box.insert(tk.END, "[Fotoğraf gösterilemedi]\n", "warn")
                    self._last_chat_sender = item.sender
                    self._last_chat_ts     = item.ts
                    self.chat_box.see(tk.END)
                finally:
                    self.chat_box.config(state=tk.DISABLED)

            def _append_audio_message(self, item: ChatItem):
                self.chat_box.config(state=tk.NORMAL)
                try:
                    grouped = self._should_group(item.sender, item.ts)
                    if not grouped:
                        self._insert_avatar_header(item.sender, item.ts)

                    label = "🎵  Sesli mesaj"
                    if item.audio_sec:
                        label += f"  ({item.audio_sec:.1f} sn)"
                    self.chat_box.insert(tk.END, f"{label}\n", "audio")

                    btn = tk.Button(
                        self.chat_box,
                        text="  ▶  Dinle  ",
                        bg=ACCENT, fg="white", bd=0,
                        activebackground="#4752C4",
                        activeforeground="white",
                        font=("Segoe UI", 10),
                        padx=10, pady=5,
                        cursor="hand2",
                        command=lambda it=item: self._play_audio_item(it)
                    )
                    self.embed_refs.append(btn)
                    self.chat_box.window_create(tk.END, window=btn, padx=56, pady=2)
                    self.chat_box.insert(tk.END, "\n")
                    self._last_chat_sender = item.sender
                    self._last_chat_ts     = item.ts
                    self.chat_box.see(tk.END)
                finally:
                    self.chat_box.config(state=tk.DISABLED)

            def _system_message(self, text: str, color: str = MUTED):
                self.chat_box.config(state=tk.NORMAL)
                try:
                    tag_map = {MUTED: "sys", WARN: "warn", DANGER: "danger",
                               SUCCESS: "sys", GOLD: "sys"}
                    tag = tag_map.get(color, "sys")
                    self.chat_box.insert(tk.END, f"  —  {text}\n", tag)
                    self.chat_box.tag_configure(tag, foreground=color)
                    self.chat_box.see(tk.END)
                    self._last_chat_sender = ""
                    self._last_chat_ts     = 0.0
                finally:
                    self.chat_box.config(state=tk.DISABLED)

            # ==================== SIDEBAR GÜNCELLEME ====================

            def _refresh_sidebar(self):
                self.rooms_list.delete(0, tk.END)
                self.users_list.delete(0, tk.END)

                now = time.time()
                rooms = sorted(
                    [r for r, seen in self.known_rooms.items() if now - seen <= STALE_ROOM_SEC],
                    key=str.lower
                )

                for room in rooms:
                    self.rooms_list.insert(tk.END, f"  # {room}")
                    if room == self.current_room:
                        last = self.rooms_list.size() - 1
                        self.rooms_list.itemconfig(last, fg=TEXT, bg=HOVER)
                    else:
                        last = self.rooms_list.size() - 1
                        self.rooms_list.itemconfig(last, fg=MUTED, bg=PANEL)

                if self.current_room:
                    users  = self.room_users.get(self.current_room, {})
                    owner  = self.room_owner.get(self.current_room, "")
                    me     = self.username_var.get().strip()

                    self.chat_subtitle.config(
                        text=f"Kurucu: {owner if owner else 'bilinmiyor'}")

                    # Kurucu grubu
                    if owner:
                        self.users_list.insert(tk.END, "KURUCU")
                        self.users_list.itemconfig(
                            self.users_list.size()-1,
                            fg=MUTED, selectbackground=PANEL, selectforeground=MUTED
                        )
                        suffix = "  (Sen)" if owner == me else ""
                        self.users_list.insert(tk.END, f"  👑 {owner}{suffix}")
                        self.users_list.itemconfig(
                            self.users_list.size()-1, fg=GOLD, bg=PANEL)

                    # Diğer üyeler
                    others = sorted([u for u in users if u != owner], key=str.lower)
                    if others:
                        self.users_list.insert(tk.END, "ÜYELER")
                        self.users_list.itemconfig(
                            self.users_list.size()-1,
                            fg=MUTED, selectbackground=PANEL, selectforeground=MUTED
                        )
                        for user in others:
                            online = (now - users[user]) < STALE_USER_SEC
                            dot    = "🟢" if online else "⚫"
                            suffix = "  (Sen)" if user == me else ""
                            self.users_list.insert(tk.END, f"  {dot} {user}{suffix}")
                            self.users_list.itemconfig(
                                self.users_list.size()-1,
                                fg=TEXT if online else MUTED, bg=PANEL
                            )

                # Kullanıcı adı panelini güncelle
                if hasattr(self, "user_name_lbl"):
                    self.user_name_lbl.config(text=self.username_var.get().strip())

                self._animate_status()

            def _on_room_click(self, event):
                idx = self.rooms_list.nearest(event.y)
                if idx < 0 or idx >= self.rooms_list.size():
                    return
                raw = self.rooms_list.get(idx).strip()
                # "# oda-adi" formatından oda adını çıkar
                room = raw.lstrip("#").strip()
                if room and room != self.current_room:
                    self.join_room(room)

            # ==================== AĞ ====================

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
                threading.Thread(target=self._receiver_loop,  daemon=True).start()
                threading.Thread(target=self._heartbeat_loop, daemon=True).start()

            def _build_packet(self, kind: str, data=None, *, target=None, room=None, packet_id=None):
                return {
                    "v":      4,
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
                    raw = json.dumps(packet, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")
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
                        data, _ = self.sock.recvfrom(65507)
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
                        me = self.username_var.get().strip()
                        ping_data = {"online": True}
                        # Avatar varsa PING'e ekle (küçük tutarak)
                        if me in self.avatar_b64_map:
                            av = self.avatar_b64_map[me]
                            if len(av) <= 6000:
                                ping_data["avatar_b64"] = av
                        self._send_packet(self._build_packet("PING", ping_data))
                        if self.room_owner.get(self.current_room) == me:
                            self._send_packet(self._build_packet("OWNER", {"owner": me}))

                    now = time.time()
                    for room in list(self.room_users.keys()):
                        users = self.room_users[room]
                        for user in list(users.keys()):
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
                        if time.time() - getattr(self, "last_screen_ts", 0) > 3.0:
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

            # ==================== ODA AKIŞI ====================

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

                users_in_room = self.room_users.get(room_name, {})
                if username in users_in_room and (time.time() - users_in_room[username] < STALE_USER_SEC):
                    username = f"{username}_{random.randint(10, 99)}"
                    self.username_var.set(username)

                if self.current_room and self.current_room != room_name:
                    self._send_packet(
                        self._build_packet("PART", {"reason": "switch"}, room=self.current_room))

                self.current_room = room_name
                self.status_var.set(f"#{room_name}")
                self.chat_title.config(text=room_name)
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
                self._system_message(f"#{room_name} kanalına katıldınız.", SUCCESS)

                self._send_packet(self._build_packet("JOIN",        {"room": room_name}))
                self._send_packet(self._build_packet("HISTORY_REQ", {"need": True}, target=username))
                self._refresh_sidebar()

                # Kendi avatarını yayınla
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
                self._send_packet(self._build_packet("PART", {"reason": "leave"}, room=old))
                self.current_room = ""
                self.status_var.set("Bağlı değil")
                self.chat_title.config(text="oda seçilmedi")
                self.chat_subtitle.config(text="Bir kanala katılın")
                self.screen_status_var.set("")
                self._set_screen_preview(None, sender=None)
                self.msg_entry.delete(0, tk.END)
                self._toggle_inputs(False)
                self._clear_chat()
                self._system_message(f"#{old} kanalından ayrıldınız.", WARN)
                self._refresh_sidebar()

            # ==================== MESAJLAŞMA ====================

            def send_message(self):
                text = self.msg_entry.get().strip()
                if not text or not self.current_room:
                    return
                if text.startswith("/"):
                    self._handle_commands(text)
                    self.msg_entry.delete(0, tk.END)
                    return
                user      = self.username_var.get().strip() or "Anon"
                packet_id = str(uuid.uuid4())
                self.seen_packet_ids.add(packet_id)
                item = ChatItem(
                    item_id=packet_id, kind="MSG", sender=user,
                    ts=time.time(), room=self.current_room, text=text
                )
                self.room_history[self.current_room].append(item)
                self._append_text_message(item)
                self._send_packet(self._build_packet("MSG", {"text": text}, packet_id=packet_id))
                self.msg_entry.delete(0, tk.END)

            def _handle_commands(self, text: str):
                cmd_parts = text.split(" ", 1)
                cmd    = cmd_parts[0].lower()
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
                    self._system_message(f"Bilinmeyen komut: {cmd}", WARN)

            # ==================== RESIM ====================

            def send_image(self):
                if not self.current_room:
                    return
                path = filedialog.askopenfilename(
                    title="Fotoğraf seç",
                    filetypes=[("Resimler", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                               ("Tümü", "*.*")]
                )
                if not path:
                    return
                try:
                    payload = self._prepare_image(
                        Image.open(path).convert("RGB"), os.path.basename(path))
                    self._dispatch_image_payload(payload)
                except Exception as exc:
                    messagebox.showerror("Resim Hatası", f"Fotoğraf hazırlanamadı: {exc}")

            def _paste_image(self, event=None):
                if not self.current_room:
                    return
                try:
                    img = ImageGrab.grabclipboard()
                    if isinstance(img, Image.Image):
                        payload = self._prepare_image(
                            img.convert("RGB"), f"Pano_{int(time.time())}.jpg")
                        self._dispatch_image_payload(payload)
                        self._system_message("Panodaki resim gönderildi.", SUCCESS)
                except Exception:
                    pass

            def _prepare_image(self, img: Image.Image, name: str) -> dict:
                side, quality = MAX_IMAGE_SIDE, 75
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

            def _dispatch_image_payload(self, payload: dict):
                if len(payload["b64"]) > MAX_IMAGE_B64_LEN:
                    messagebox.showwarning("Boyut", "Fotoğraf çok büyük, sıkıştırılamadı.")
                    return
                user      = self.username_var.get().strip() or "Anon"
                packet_id = str(uuid.uuid4())
                self.seen_packet_ids.add(packet_id)
                item = ChatItem(
                    item_id=packet_id, kind="IMG", sender=user,
                    ts=time.time(), room=self.current_room,
                    image_b64=payload["b64"], image_name=payload["name"]
                )
                self.room_history[self.current_room].append(item)
                self._append_image_message(item)
                self._send_packet(self._build_packet("IMG", payload, packet_id=packet_id))

            # ==================== SES ====================

            def _start_audio_record(self, event=None):
                if not self.current_room:
                    return
                if not AUDIO_AVAILABLE:
                    messagebox.showinfo("Modül Eksik",
                        "Ses kaydı için:\npip install sounddevice numpy")
                    return
                if self.is_recording:
                    return
                try:
                    self.is_recording   = True
                    self.audio_frames   = []
                    self.record_start_ts = time.time()
                    self.audio_status_var.set("🔴  Kayıt devam ediyor… (maks 15 sn)")
                    self.mic_btn.config(fg=DANGER)
                    self.audio_timer = self.root.after(15000, self._stop_audio_record)

                    def callback(indata, frames, time_info, status):
                        if self.is_recording:
                            self.audio_frames.append(indata.copy())

                    self.audio_stream = sd.InputStream(
                        samplerate=AUDIO_SR, channels=1, dtype="int16",
                        callback=callback)
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
                        self.root.after(1200, lambda: self.audio_status_var.set(""))
                        return
                    raw        = audio.tobytes()
                    compressed = zlib.compress(raw, level=9)
                    b64        = base64.b64encode(compressed).decode("ascii")
                    if len(b64) > MAX_AUDIO_B64_LEN:
                        messagebox.showwarning("Ses çok büyük",
                            "Kayıt çok uzun. Daha kısa bir ses gönder.")
                        self.audio_status_var.set("")
                        return
                    user      = self.username_var.get().strip() or "Anon"
                    packet_id = str(uuid.uuid4())
                    self.seen_packet_ids.add(packet_id)
                    payload = {
                        "b64":      b64,
                        "sr":       AUDIO_SR,
                        "codec":    "zlib_pcm16",
                        "duration": round(duration, 2),
                        "name":     f"Sesli_Mesaj_{int(time.time())}.audio"
                    }
                    item = ChatItem(
                        item_id=packet_id, kind="AUDIO", sender=user,
                        ts=time.time(), room=self.current_room,
                        audio_b64=b64, audio_name=payload["name"],
                        audio_sr=AUDIO_SR, audio_codec="zlib_pcm16",
                        audio_sec=duration
                    )
                    raw_packet = json.dumps(
                        self._build_packet("AUDIO", payload, packet_id=packet_id),
                        ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    if len(raw_packet) > MAX_PACKET_BYTES:
                        messagebox.showwarning("Ses çok büyük",
                            "UDP paket sınırı aşıldı. Daha kısa kayıt yap.")
                        self.audio_status_var.set("")
                        return
                    self.room_history[self.current_room].append(item)
                    self._append_audio_message(item)
                    self.sock.sendto(raw_packet, (BROADCAST_ADDR, PORT))
                    self.audio_status_var.set("✓  Ses gönderildi")
                    self.root.after(1500, lambda: self.audio_status_var.set(""))
                except Exception as exc:
                    messagebox.showerror("Ses işleme hatası", f"Gönderilemedi:\n{exc}")
                    self.audio_status_var.set("")

            def _play_audio_item(self, item: ChatItem):
                if not AUDIO_AVAILABLE:
                    messagebox.showwarning("Ses yok", "sounddevice/numpy gerekli.")
                    return
                threading.Thread(
                    target=self._play_audio_worker, args=(item,), daemon=True).start()

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
                        "Oynatma Hatası", f"{item.sender} mesajı oynatılamadı:\n{exc}"))

            # ==================== EKRAN PAYLAŞIMI ====================

            def _toggle_screen_share(self):
                if not self.current_room:
                    return
                if self.screen_sharing:
                    self._stop_screen_share()
                else:
                    self._start_screen_share()

            def _start_screen_share(self):
                if not PIL_AVAILABLE:
                    messagebox.showerror("PIL eksik", "Pillow gerekli.")
                    return
                if self.screen_sharing:
                    return
                if (getattr(self, "current_screen_sender", None) and
                        self.current_screen_sender != self.username_var.get().strip() and
                        time.time() - getattr(self, "last_screen_ts", 0) < 4.0):
                    messagebox.showwarning("Uyarı",
                        f"{self.current_screen_sender} ekran paylaşıyor. Lütfen bekleyin.")
                    return
                self.screen_sharing = True
                self.screen_status_var.set("🔴  Ekran paylaşılıyor")
                if hasattr(self, "screen_icon"):
                    self.screen_icon.config(text="🔴", fg=DANGER)
                self._system_message("Ekran paylaşımı başlatıldı.", SUCCESS)
                self.screen_thread = threading.Thread(
                    target=self._screen_share_loop, daemon=True)
                self.screen_thread.start()

            def _stop_screen_share(self, silent: bool = False):
                if not self.screen_sharing:
                    if hasattr(self, "screen_icon"):
                        self.screen_icon.config(text="🖥️", fg=MUTED)
                    return
                self.screen_sharing = False
                self.screen_status_var.set("")
                if hasattr(self, "screen_icon"):
                    self.screen_icon.config(text="🖥️", fg=MUTED)
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
                            working.thumbnail(
                                (SCREEN_SHARE_MAX_SIDE, SCREEN_SHARE_MAX_SIDE), resample_filter)
                        buf = io.BytesIO()
                        working.save(buf, format="JPEG", quality=SCREEN_SHARE_JPEG_QUALITY)
                        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                        if len(b64) > SCREEN_SHARE_MAX_B64_LEN:
                            smaller = img.convert("RGB")
                            smaller.thumbnail(
                                (max(480, SCREEN_SHARE_MAX_SIDE//2),
                                 max(270, SCREEN_SHARE_MAX_SIDE//2)), resample_filter)
                            buf = io.BytesIO()
                            smaller.save(buf, format="JPEG",
                                         quality=max(18, SCREEN_SHARE_JPEG_QUALITY-10))
                            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                        if len(b64) > SCREEN_SHARE_MAX_B64_LEN:
                            time.sleep(SCREEN_SHARE_INTERVAL_SEC)
                            continue
                        frame_id = str(uuid.uuid4())
                        total    = (len(b64) + SCREEN_SHARE_CHUNK_SIZE - 1) // SCREEN_SHARE_CHUNK_SIZE
                        payload_base = {
                            "frame_id": frame_id, "total": total,
                            "name": f"screen_{int(time.time())}.jpg",
                            "w": working.width, "h": working.height,
                        }
                        for idx in range(total):
                            if not self.screen_sharing or not self.current_room or not self.running:
                                break
                            chunk  = b64[idx*SCREEN_SHARE_CHUNK_SIZE:(idx+1)*SCREEN_SHARE_CHUNK_SIZE]
                            packet = self._build_packet(
                                "SCREEN", {**payload_base, "index": idx, "chunk": chunk})
                            raw_p  = json.dumps(packet, ensure_ascii=False,
                                                separators=(",",":")).encode("utf-8")
                            if len(raw_p) <= 65507:
                                self._send_packet(packet)
                        time.sleep(SCREEN_SHARE_INTERVAL_SEC)
                    except Exception as exc:
                        self.root.after(0, lambda: self.screen_status_var.set(
                            f"Hata: {exc}"))
                        time.sleep(SCREEN_SHARE_INTERVAL_SEC)

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
                    entry = {
                        "sender": sender or "Anon", "room": room, "ts": now,
                        "total": max(total, 1), "width": width, "height": height, "chunks": {}
                    }
                    self.screen_buffers[frame_id] = entry
                entry["ts"] = now
                entry["sender"] = sender or entry.get("sender", "Anon")
                if total:  entry["total"]  = total
                if width:  entry["width"]  = width
                if height: entry["height"] = height
                entry["chunks"][index] = chunk
                if len(entry["chunks"]) >= entry["total"]:
                    try:
                        ordered     = [entry["chunks"][i] for i in range(entry["total"])]
                        sender_name = entry["sender"]
                        threading.Thread(
                            target=self._decode_screen_frame,
                            args=(ordered, sender_name), daemon=True).start()
                    except KeyError:
                        pass
                    finally:
                        self.screen_buffers.pop(frame_id, None)

            def _decode_screen_frame(self, ordered_chunks, sender):
                try:
                    b64 = "".join(ordered_chunks)
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
                    self.viewer_window.title(f"{sender}  —  Ekran Yayını")
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
                    try:    res_filter = Image.Resampling.LANCZOS
                    except: res_filter = Image.LANCZOS
                    display_img = img.copy()
                    display_img.thumbnail((win_w, win_h), res_filter)
                else:
                    display_img = img
                photo = ImageTk.PhotoImage(display_img)
                self.screen_preview_photo = photo
                self.viewer_label.configure(image=photo)
                self.viewer_label.image = photo
                self.screen_status_var.set(f"📡  {sender} ekran paylaşıyor")
                self.current_screen_sender = sender
                self.current_screen_ts     = time.time()

            def _prune_screen_buffers(self):
                if not self.screen_buffers:
                    return
                now = time.time()
                for fid in list(self.screen_buffers.keys()):
                    if now - self.screen_buffers[fid].get("ts", now) > SCREEN_BUFFER_TTL:
                        self.screen_buffers.pop(fid, None)

            # ==================== PAKET İŞLEME ====================

            def _process_packet(self, pkt: dict):
                if not isinstance(pkt, dict) or pkt.get("v") not in {3, 4}:
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
                        kind in {"MSG","IMG","JOIN","PART","PING","AUDIO","SCREEN","AVATAR"}:
                    return
                if target and target != self.username_var.get().strip():
                    return
                if room:
                    self.known_rooms[room] = time.time()
                if sender and room:
                    self.room_users[room][sender] = time.time()
                    if sender not in self.room_join_times[room]:
                        self.room_join_times[room][sender] = time.time()

                # Avatar paketi — avatar önbelleğine kaydet
                if kind == "AVATAR":
                    b64 = str(data.get("b64") or "").strip()
                    if b64 and sender:
                        self.avatar_b64_map[sender] = b64
                        # Önbellekten temizle, sonraki görüntülemede yeniden oluştur
                        for k in list(self.avatar_cache.keys()):
                            if k.startswith(f"{sender}_"):
                                del self.avatar_cache[k]
                    return

                if kind == "OWNER" and room:
                    announced = str(data.get("owner") or sender or "").strip()
                    if announced and announced in self.room_users.get(room, {}):
                        self.room_owner[room] = announced
                    self._refresh_sidebar()
                    return

                if kind == "PING" and sender and room:
                    # Avatar PING içinde geldiyse işle
                    av_b64 = str(data.get("avatar_b64") or "").strip()
                    if av_b64 and sender not in self.avatar_b64_map:
                        self.avatar_b64_map[sender] = av_b64
                        for k in list(self.avatar_cache.keys()):
                            if k.startswith(f"{sender}_"):
                                del self.avatar_cache[k]

                if kind in {"JOIN", "PART", "PING"} and room:
                    if kind == "PART" and sender:
                        self.room_users[room].pop(sender, None)
                        self.room_join_times[room].pop(sender, None)
                        if room == self.current_room and sender != self.username_var.get().strip():
                            self._system_message(f"{sender} kanaldan ayrıldı.", WARN)
                    if kind == "JOIN" and sender:
                        if room == self.current_room and sender != self.username_var.get().strip():
                            self._system_message(f"{sender} kanala katıldı.", SUCCESS)
                    self._recalculate_room_owner(room)
                    self._refresh_sidebar()
                    return

                if room != self.current_room:
                    return
                if sender in self.banned_users.get(room, set()) and \
                        kind in {"MSG","IMG","AUDIO","HISTORY","SCREEN"}:
                    return

                if kind == "HISTORY_REQ":
                    if room and self._is_owner(room):
                        self._send_history_to(target)
                    return

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
                        if item_kind == "IMG":
                            item = ChatItem(
                                item_id=item_id, kind="IMG",
                                sender=str(raw_item.get("sender") or "Anon"),
                                ts=ts, room=room,
                                image_b64=str(raw_item.get("image_b64") or ""),
                                image_name=str(raw_item.get("image_name") or "image.jpg")
                            )
                            self.room_history[room].append(item)
                            self._append_image_message(item)
                        elif item_kind == "AUDIO":
                            item = ChatItem(
                                item_id=item_id, kind="AUDIO",
                                sender=str(raw_item.get("sender") or "Anon"),
                                ts=ts, room=room,
                                audio_b64=str(raw_item.get("audio_b64") or ""),
                                audio_name=str(raw_item.get("audio_name") or "voice.audio"),
                                audio_sr=int(raw_item.get("audio_sr") or AUDIO_SR),
                                audio_codec=str(raw_item.get("audio_codec") or "zlib_pcm16"),
                                audio_sec=float(raw_item.get("audio_sec") or 0.0)
                            )
                            self.room_history[room].append(item)
                            self._append_audio_message(item)
                        else:
                            item = ChatItem(
                                item_id=item_id, kind="MSG",
                                sender=str(raw_item.get("sender") or "Anon"),
                                ts=ts, room=room,
                                text=str(raw_item.get("text") or "")
                            )
                            self.room_history[room].append(item)
                            self._append_text_message(item)
                    self.chat_subtitle.config(
                        text=f"Kurucu: {self.room_owner.get(room,'bilinmiyor')}")
                    return

                if kind == "MSG":
                    text = str(data.get("text") or "")
                    item = ChatItem(
                        item_id=packet_id or str(uuid.uuid4()), kind="MSG",
                        sender=sender or "Anon",
                        ts=float(pkt.get("ts") or time.time()),
                        room=room, text=text
                    )
                    self.seen_packet_ids.add(item.item_id)
                    self.room_history[room].append(item)
                    self._append_text_message(item)
                    self._show_notification("Yeni Mesaj",
                        f"{sender}: {text[:24]}{'…' if len(text)>24 else ''}")
                    return

                if kind == "IMG":
                    item = ChatItem(
                        item_id=packet_id or str(uuid.uuid4()), kind="IMG",
                        sender=sender or "Anon",
                        ts=float(pkt.get("ts") or time.time()), room=room,
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
                        item_id=packet_id or str(uuid.uuid4()), kind="AUDIO",
                        sender=sender or "Anon",
                        ts=float(pkt.get("ts") or time.time()), room=room,
                        audio_b64=str(data.get("b64") or ""),
                        audio_name=str(data.get("name") or "voice.audio"),
                        audio_sr=int(data.get("sr") or AUDIO_SR),
                        audio_codec=str(data.get("codec") or "zlib_pcm16"),
                        audio_sec=float(data.get("duration") or 0.0)
                    )
                    self.seen_packet_ids.add(item.item_id)
                    self.room_history[room].append(item)
                    self._append_audio_message(item)
                    self._show_notification("Sesli Mesaj", f"{sender} sesli mesaj gönderdi.")
                    return

                if kind == "SCREEN":
                    self._handle_screen_packet(
                        pkt, room, sender or "Anon",
                        data if isinstance(data, dict) else {})
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
                        self._system_message(
                            f"🧹 {victim} kullanıcısının mesajları silindi.", WARN)
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
                        "item_id":    item.item_id,
                        "kind":       item.kind,
                        "sender":     item.sender,
                        "ts":         item.ts,
                        "text":       item.text,
                        "image_b64":  item.image_b64,
                        "image_name": item.image_name,
                        "audio_b64":  item.audio_b64,
                        "audio_name": item.audio_name,
                        "audio_sr":   item.audio_sr,
                        "audio_codec":item.audio_codec,
                        "audio_sec":  item.audio_sec,
                    })
                if payload:
                    self._send_packet(self._build_packet("HISTORY", payload, target=target))

            # ==================== MODERASİON ====================

            def _selected_user_from_list(self):
                try:
                    idx = self.users_list.curselection()
                    if not idx:
                        return None
                    text = self.users_list.get(idx[0]).strip()
                    if text.startswith("👑 "): text = text[2:].strip()
                    elif text.startswith("👤 "): text = text[2:].strip()
                    elif text.startswith("🟢 "): text = text[2:].strip()
                    elif text.startswith("⚫ "): text = text[2:].strip()
                    if text.endswith("  (Sen)"): text = text[:-7].strip()
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
                room     = self.current_room
                is_owner = self._is_owner(room)
                me       = self.username_var.get().strip()
                can_mod  = is_owner and self.selected_user != me
                try:
                    self.user_menu.entryconfig(
                        1, state=tk.NORMAL if can_mod else tk.DISABLED)
                    self.user_menu.entryconfig(
                        2, state=tk.NORMAL if can_mod else tk.DISABLED)
                except tk.TclError:
                    pass
                self.user_menu.tk_popup(event.x_root, event.y_root)

            def _show_selected_user_info(self):
                user = self.selected_user or self._selected_user_from_list()
                if not user or not self.current_room:
                    return
                room      = self.current_room
                msgs      = [x for x in list(self.room_history[room]) if x.sender == user]
                last_seen = self.room_users[room].get(user)
                info = (
                    f"Kullanıcı: {user}\n"
                    f"Oda: {room}\n"
                    f"Mesaj sayısı: {len(msgs)}\n"
                    f"Aktif: {'Evet' if last_seen and time.time()-last_seen < STALE_USER_SEC else 'Hayır'}"
                )
                messagebox.showinfo("Kullanıcı Bilgisi", info)

            def _ban_user(self, user: str):
                if not user or not self.current_room or user == self.username_var.get().strip():
                    return
                if not self._is_owner(self.current_room):
                    messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
                    return
                self.banned_users[self.current_room].add(user)
                self._purge_user_messages(self.current_room, user)
                self._send_packet(
                    self._build_packet("BAN", {"target_user": user}, target=user))
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
                    messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
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
                    messagebox.showwarning("Yetki yok", "Oda kurucusu olmalısın.")
                    return
                self.room_history[self.current_room].clear()
                self._clear_chat()
                self._system_message("Tüm geçmiş temizlendi.", DANGER)
                self._send_packet(self._build_packet("CLEAR", {"all": True}))

            def _purge_user_messages(self, room: str, user: str):
                if not room or not user:
                    return
                kept = deque(
                    [x for x in self.room_history[room] if x.sender != user],
                    maxlen=MAX_HISTORY
                )
                self.room_history[room] = kept
                self._render_history(room)

            def _is_owner(self, room: str, sender=None):
                if not room:
                    return False
                owner  = self.room_owner.get(room)
                sender = sender or self.username_var.get().strip()
                return bool(owner and owner == sender)

            def _tick_ui(self):
                if not self.running:
                    return
                self._refresh_sidebar()
                self.root.after(UI_REFRESH_MS, self._tick_ui)

        # ==================== BAŞLAT ====================
        if __name__ == "__main__":
            root = tk.Tk()
            app  = ModernGhostChat(root)
            root.mainloop()
    else:
        print("Erişim reddedildi.")
        input("Tamam.")


if __name__ == "__main__":
    testi_baslat()
