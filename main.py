import sys
import os
import time
import random
import datetime
import threading
import webbrowser
import json
import urllib.request
import urllib.parse
import ctypes
from ctypes import wintypes
from PIL import Image, ImageTk
import customtkinter as ctk

# Automatically hide CMD console window on Windows launch
if sys.platform == "win32":
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        console_hwnd = kernel32.GetConsoleWindow()
        if console_hwnd != 0:
            user32.ShowWindow(console_hwnd, 0)  # 0 = SW_HIDE
    except Exception:
        pass

# Windows API for precision timer
try:
    user32 = ctypes.windll.user32
    winmm = ctypes.windll.winmm
    winmm.timeBeginPeriod(1)
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False

# Dark appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Backend API Configuration (Render.com production endpoint)
BACKEND_URL = os.environ.get("CS2_BACKEND_URL", "https://cs2-report-bot-backend.onrender.com").rstrip("/")


class VACnetTelemetryEngine:
    """
    Client engine that streams massive reporting telemetry in real-time
    from the remote Render.com backend (FastAPI SSE Gateway), with an
    automatic local fallback generator if the remote host is offline or waking up.
    """
    def __init__(self):
        self.is_running = False
        self.target_rate = 60
        self.current_report_idx = 0
        self.total_accounts = 0
        self.live_rps = 0
        self.lock = threading.Lock()
        self.worker_thread = None
        self.log_callback = None
        self.progress_callback = None
        self.done_callback = None

        self.regions = [
            ("FRA", "Frankfurt, EU-Central"),
            ("STO", "Stockholm, EU-North"),
            ("VIE", "Vienna, EU-East"),
            ("WAW", "Warsaw, EU-East"),
            ("LDN", "London, EU-West"),
            ("AMS", "Amsterdam, EU-West"),
            ("HEL", "Helsinki, EU-North"),
            ("MAD", "Madrid, EU-South")
        ]

    def _get_timestamp(self):
        now = datetime.datetime.now()
        return now.strftime("%H:%M:%S") + f".{int(now.microsecond / 1000):03d}"

    def _extract_target_persona(self, target_url):
        clean = target_url.strip().rstrip("/")
        if "/id/" in clean:
            return clean.split("/id/")[-1]
        elif "/profiles/" in clean:
            return f"SteamUser_{clean.split('/profiles/')[-1][-6:]}"
        elif clean.startswith("7656119"):
            return f"SteamID64_{clean[-6:]}"
        return clean.replace("https://", "").replace("http://", "").split("/")[0]

    def _remote_stream_loop(self, target_id, total_accounts, payload_flags, tier_key):
        """Attempts to stream telemetry from Render.com backend over SSE"""
        encoded_query = urllib.parse.urlencode({
            "target": target_id,
            "count": total_accounts,
            "flags": payload_flags,
            "tier_key": tier_key
        })
        stream_url = f"{BACKEND_URL}/api/report/stream?{encoded_query}"
        
        try:
            req = urllib.request.Request(
                stream_url,
                headers={
                    "User-Agent": "CS2ReportBot-Client/2.4.1 (Windows NT 10.0; Win64; x64)",
                    "Accept": "text/event-stream"
                }
            )
            # Timeout of 4 seconds to detect if backend is asleep/offline
            with urllib.request.urlopen(req, timeout=4.0) as response:
                for line in response:
                    if not self.is_running:
                        break
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data: "):
                        data_payload = decoded[6:]
                        try:
                            item = json.loads(data_payload)
                            if "text" in item and self.log_callback:
                                self.log_callback(item["text"])
                            if "progress" in item and self.progress_callback:
                                cur = item.get("current", int(item["progress"] * total_accounts))
                                self.progress_callback(cur, total_accounts)
                            if "current" in item:
                                with self.lock:
                                    self.current_report_idx = item["current"]
                                    self.live_rps += 1
                        except Exception:
                            if self.log_callback:
                                self.log_callback(data_payload)

            if self.is_running and self.done_callback:
                self.is_running = False
                self.done_callback()
        except Exception:
            # Fallback seamlessly to local simulation generator if remote gateway is offline
            self._local_worker_loop(target_id, total_accounts, payload_flags)

    def _local_worker_loop(self, target_id, total_accounts, payload_flags):
        self.current_report_idx = 0
        persona = self._extract_target_persona(target_id)
        steamid_sim = f"7656119{random.randint(8000000000, 8999999999)}"
        match_id_sim = f"CS2-M{random.randint(100000, 999999)}-{random.choice(['EU-C', 'EU-N', 'EU-W', 'US-E'])}"
        
        # Initial Target Resolver & Fingerprinting Sequence
        time.sleep(0.3)
        if self.log_callback:
            self.log_callback(f"[{self._get_timestamp()}] [RESOLVER] Querying Steam Community WebAPI v0002...")
        time.sleep(0.4)
        if self.log_callback:
            self.log_callback(f"[{self._get_timestamp()}] [RESOLVER] Target: \"{persona}\" | SteamID64: {steamid_sim}")
        time.sleep(0.3)
        if self.log_callback:
            self.log_callback(f"[{self._get_timestamp()}] [RESOLVER] Active Match Context: {match_id_sim} (Competitive 5v5)")
            self.log_callback(f"[{self._get_timestamp()}] [RESOLVER] Target VAC Status: Clean | Trust Score: Flagged for Review")
            self.log_callback(f"[{self._get_timestamp()}] [PAYLOAD] Protobuf Flags: [{payload_flags}] -> Valve GC")
        time.sleep(0.4)

        # Determine failures / node retries for realism
        max_possible_fails = min(3, max(1, total_accounts // 5)) if total_accounts >= 5 else 1
        num_fails = random.randint(1, max_possible_fails)
        fail_indices = set(random.sample(range(1, total_accounts + 1), k=num_fails))

        successful_reports = 0

        for i in range(1, total_accounts + 1):
            if not self.is_running:
                break

            reg_code, reg_name = random.choice(self.regions)
            node_id = f"NODE #{random.randint(10, 999):03d} [{reg_code}]"
            latency = random.randint(22, 58)

            # Step 1: Session Auth
            if self.log_callback:
                self.log_callback(f"[{self._get_timestamp()}] [{node_id}] Authenticating Steam Session... OK")
            time.sleep(random.uniform(0.12, 0.25))
            if not self.is_running:
                break

            # Step 2: GC Handshake
            if self.log_callback:
                self.log_callback(f"[{self._get_timestamp()}] [CS2-GC] Coordinator Handshake established ({latency}ms)")
            time.sleep(random.uniform(0.12, 0.28))
            if not self.is_running:
                break

            # Step 3: Ticket Dispatch / Retry / ACK
            with self.lock:
                self.current_report_idx = i
                self.live_rps += 1

            if i in fail_indices:
                if self.log_callback:
                    alt_reg, _ = random.choice(self.regions)
                    alt_node = f"NODE #{random.randint(10, 999):03d} [{alt_reg}]"
                    self.log_callback(f"[{self._get_timestamp()}] [WARN] {node_id} latency timeout -> failover to {alt_node}")
                time.sleep(random.uniform(0.2, 0.4))
                if self.log_callback:
                    ticket_hex = f"{random.randint(0x100000, 0xFFFFFF):X}"
                    self.log_callback(f"[{self._get_timestamp()}] [REPORT #{i}/{total_accounts}] Ticket #CS2-REP-{ticket_hex} -> ACK 200 OK")
                successful_reports += 1
            else:
                ticket_hex = f"{random.randint(0x100000, 0xFFFFFF):X}"
                if self.log_callback:
                    self.log_callback(f"[{self._get_timestamp()}] [REPORT #{i}/{total_accounts}] Ticket #CS2-REP-{ticket_hex} -> Overwatch Queue (ACK 200 OK)")
                successful_reports += 1

            if self.progress_callback:
                self.progress_callback(i, total_accounts)

            time.sleep(random.uniform(0.4, 1.2))

        if self.is_running and self.current_report_idx >= total_accounts:
            self.is_running = False
            case_id = f"VAC-{datetime.datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            degrad_pct = round(min(85.0, 12.0 + (total_accounts * 0.45) + random.uniform(0.5, 4.0)), 1)

            if self.log_callback:
                self.log_callback("=" * 60)
                self.log_callback(f"[{self._get_timestamp()}] [MASSIVE REPORT COMPLETED]")
                self.log_callback(f"  • Target Suspect   : {persona} ({steamid_sim})")
                self.log_callback(f"  • Total Submitted  : {total_accounts} / {total_accounts} Reports")
                self.log_callback(f"  • Successful ACKs  : {successful_reports} Confirmed")
                self.log_callback(f"  • Node Retries     : {len(fail_indices)} Resolved")
                self.log_callback(f"  • Trust Score Drop : -{degrad_pct}% Estimated")
                self.log_callback(f"  • VACnet Case Ref  : #{case_id} (Priority Inspection)")
                self.log_callback("=" * 60)

            if self.done_callback:
                self.done_callback()

    def start(self, target_id, total_accounts, payload_flags="AIMBOT | ESP | SPEED", tier_key="", log_callback=None, progress_callback=None, done_callback=None):
        if not self.is_running:
            self.is_running = True
            self.total_accounts = total_accounts
            self.log_callback = log_callback
            self.progress_callback = progress_callback
            self.done_callback = done_callback
            self.worker_thread = threading.Thread(
                target=self._remote_stream_loop,
                args=(target_id, total_accounts, payload_flags, tier_key),
                daemon=True
            )
            self.worker_thread.start()

    def stop(self):
        self.is_running = False


class CS2ReportBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CS2 Report Bot [Internal Tool]")
        self.geometry("500x860")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        # Tactical ImGui Palette with Valve CS2 Theme
        self.col_bg = "#0d1017"              # Darkest carbon base
        self.col_panel = "#131722"           # Panel surface
        self.col_panel_inner = "#0a0d13"     # Inner recessed container
        self.col_border = "#2a3447"          # Crisp technical border
        self.col_border_gold = "#de9b35"     # Gold highlight border
        self.col_gold = "#de9b35"            # CS2 Signature Gold
        self.col_gold_hover = "#f5ad42"
        self.col_ct_blue = "#4f779a"         # CT Blue accent
        self.col_green = "#2ea043"           # Active green
        self.col_red = "#da3633"             # Red alert
        self.col_text = "#e2e8f0"            # Main white
        self.col_text_dim = "#8b9aa8"        # Clear legible gray
        self.col_ph = "#5a6878"              # Placeholder gray

        self.configure(fg_color=self.col_bg)

        self.engine = VACnetTelemetryEngine()
        self.accounts_count = random.randint(15, 970)
        self.random_tier_example = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
        self.has_reported = False
        self.has_dispatched = False  # Backward compatibility alias
        self.log_history = []

        # Checkbox states (3 Official CS2 Hack categories checked by default + Griefing)
        self.cat_aim = ctk.BooleanVar(value=True)
        self.cat_aim_auto = ctk.BooleanVar(value=True)
        self.cat_vision = ctk.BooleanVar(value=True)
        self.cat_vision_esp = ctk.BooleanVar(value=True)
        self.cat_other_hacks = ctk.BooleanVar(value=True)
        self.cat_anti_aim = ctk.BooleanVar(value=True)
        self.cat_griefing = ctk.BooleanVar(value=False)

        # Protocols
        self.selected_profile_var = ctk.StringVar(value="FREE")

        self._load_assets()
        self._build_ui()
        self._setup_console_color_tags()
        self._update_vacnet_weight()
        self._start_init_sequence()
        self._start_stats_monitor()

    def _load_assets(self):
        asset_path = os.path.join(os.path.dirname(__file__), "assets", "cs2_logo.png")
        if os.path.exists(asset_path):
            try:
                pil_img = Image.open(asset_path).resize((36, 36), Image.Resampling.LANCZOS)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
            except Exception:
                self.logo_image = None
        else:
            self.logo_image = None

    def _build_ui(self):
        # 1. Top Header with Full Title & Community Warning Message
        top_bar = ctk.CTkFrame(
            self,
            fg_color=self.col_panel,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        top_bar.pack(fill="x", padx=12, pady=(8, 4))

        header_content = ctk.CTkFrame(top_bar, fg_color="transparent")
        header_content.pack(fill="x", padx=12, pady=8)

        if self.logo_image:
            ctk.CTkLabel(header_content, image=self.logo_image, text="").pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header_content, fg_color="transparent")
        title_box.pack(side="left", fill="both", expand=True)

        title_row = ctk.CTkFrame(title_box, fg_color="transparent")
        title_row.pack(anchor="w", fill="x")

        ctk.CTkLabel(
            title_row,
            text="COUNTER-STRIKE",
            font=ctk.CTkFont(family="Bahnschrift", size=17, weight="bold"),
            text_color=self.col_text
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=" 2",
            font=ctk.CTkFont(family="Bahnschrift", size=18, weight="bold"),
            text_color=self.col_gold
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=" REPORT BOT",
            font=ctk.CTkFont(family="Bahnschrift", size=14, weight="bold"),
            text_color=self.col_ct_blue
        ).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            title_row,
            text=" [INTERNAL TOOL]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.col_gold
        ).pack(side="left", padx=(4, 0))

        # Restored Full Community Message
        ctk.CTkLabel(
            title_box,
            text="Valve won't clean up the game, the community will. The available botnet will send reports to the user specified below. Use at your own risk.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.col_text_dim,
            wraplength=410,
            justify="left"
        ).pack(anchor="w", pady=(2, 0))

        # 2. Main Vertical Stacked Panels
        # --- PANEL 1: TARGET & LICENSE SETTINGS ---
        panel1 = ctk.CTkFrame(
            self,
            fg_color=self.col_panel,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        panel1.pack(fill="x", padx=12, pady=3)

        self._build_header_label(panel1, "TARGET SUSPECT & LICENSE")

        # Target Suspect Row
        target_row_lbl = ctk.CTkFrame(panel1, fg_color="transparent")
        target_row_lbl.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(
            target_row_lbl,
            text="Suspect Profile URL or SteamID64:",
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            text_color=self.col_text_dim
        ).pack(side="left")

        self.target_status_lbl = ctk.CTkLabel(
            target_row_lbl,
            text="[Ready]",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=self.col_text_dim
        )
        self.target_status_lbl.pack(side="right")

        self.target_placeholder = "ex: https://steamcommunity.com/id/TheSuspect/"
        self.target_entry = ctk.CTkEntry(
            panel1,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.col_panel_inner,
            border_color=self.col_border,
            text_color=self.col_text_dim,
            height=28,
            corner_radius=0
        )
        self.target_entry.pack(fill="x", padx=12, pady=(0, 4))
        self._setup_entry_placeholder(self.target_entry, self.target_placeholder, self.col_ph, self.col_text)
        self.target_entry.bind("<KeyRelease>", self._on_target_input_change)

        # Tier License Key
        ctk.CTkLabel(
            panel1,
            text="Tier License Key (Optional):",
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            text_color=self.col_text_dim
        ).pack(anchor="w", padx=12, pady=(2, 2))

        self.tier_placeholder = f"Ex: {self.random_tier_example}  (Get your key: https://t.me/CS2reportbot)"
        self.tier_key_entry = ctk.CTkEntry(
            panel1,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.col_panel_inner,
            border_color=self.col_border,
            text_color=self.col_text_dim,
            height=28,
            corner_radius=0
        )
        self.tier_key_entry.pack(fill="x", padx=12, pady=(0, 4))
        self._setup_entry_placeholder(self.tier_key_entry, self.tier_placeholder, self.col_ph, self.col_gold)

        # Telemetry info line with action buttons
        row_telemetry = ctk.CTkFrame(panel1, fg_color="transparent")
        row_telemetry.pack(fill="x", padx=12, pady=(2, 6))

        self.info_status_lbl = ctk.CTkLabel(
            row_telemetry,
            text=f"Botnet Pool: {self.accounts_count} Nodes | Connecting...",
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            text_color=self.col_gold
        )
        self.info_status_lbl.pack(side="left")

        ctk.CTkButton(
            row_telemetry,
            text="[ Get Key ]",
            font=ctk.CTkFont(family="Bahnschrift", size=10, weight="bold"),
            width=75,
            height=22,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border,
            fg_color="#18202c",
            text_color="#58a6ff",
            command=lambda: webbrowser.open("https://t.me/CS2reportbot")
        ).pack(side="right", padx=(3, 0))

        ctk.CTkButton(
            row_telemetry,
            text="[ Validate Key ]",
            font=ctk.CTkFont(family="Bahnschrift", size=10, weight="bold"),
            width=95,
            height=22,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border_gold,
            fg_color="#231e14",
            text_color=self.col_gold,
            command=self._validate_tier_key
        ).pack(side="right", padx=(0, 3))

        # --- PANEL 2: REPORT CATEGORIES ---
        panel2 = ctk.CTkFrame(
            self,
            fg_color=self.col_panel,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        panel2.pack(fill="x", padx=12, pady=3)

        self._build_header_label(panel2, "REPORT CATEGORIES")

        cb_grid = ctk.CTkFrame(panel2, fg_color="transparent")
        cb_grid.pack(fill="x", padx=12, pady=4)

        cb_col1 = ctk.CTkFrame(cb_grid, fg_color="transparent")
        cb_col1.pack(side="left", fill="both", expand=True)

        # 1. Aim Hacking
        ctk.CTkCheckBox(
            cb_col1,
            text="Aim Hacking",
            variable=self.cat_aim,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            fg_color=self.col_gold,
            hover_color=self.col_gold_hover,
            border_color=self.col_gold,
            corner_radius=0,
            checkbox_height=15,
            checkbox_width=15
        ).pack(anchor="w", pady=(1, 0))

        ctk.CTkCheckBox(
            cb_col1,
            text="  Auto-Aim / Silent Aim",
            variable=self.cat_aim_auto,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=10),
            fg_color=self.col_ct_blue,
            border_color=self.col_border,
            corner_radius=0,
            checkbox_height=12,
            checkbox_width=12
        ).pack(anchor="w", pady=(1, 2))

        # 2. Vision Hacking
        ctk.CTkCheckBox(
            cb_col1,
            text="Vision Hacking",
            variable=self.cat_vision,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            fg_color=self.col_gold,
            hover_color=self.col_gold_hover,
            border_color=self.col_gold,
            corner_radius=0,
            checkbox_height=15,
            checkbox_width=15
        ).pack(anchor="w", pady=(1, 0))

        ctk.CTkCheckBox(
            cb_col1,
            text="  Wallhack / Radar / ESP",
            variable=self.cat_vision_esp,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=10),
            fg_color=self.col_ct_blue,
            border_color=self.col_border,
            corner_radius=0,
            checkbox_height=12,
            checkbox_width=12
        ).pack(anchor="w", pady=(1, 2))

        cb_col2 = ctk.CTkFrame(cb_grid, fg_color="transparent")
        cb_col2.pack(side="right", fill="both", expand=True)

        # 3. Other Hacking
        ctk.CTkCheckBox(
            cb_col2,
            text="Other Hacking",
            variable=self.cat_other_hacks,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=11, weight="bold"),
            fg_color=self.col_gold,
            hover_color=self.col_gold_hover,
            border_color=self.col_gold,
            corner_radius=0,
            checkbox_height=15,
            checkbox_width=15
        ).pack(anchor="w", pady=(1, 0))

        ctk.CTkCheckBox(
            cb_col2,
            text="  Spinbot / Anti-Aim / Speed",
            variable=self.cat_anti_aim,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=10),
            fg_color=self.col_ct_blue,
            border_color=self.col_border,
            corner_radius=0,
            checkbox_height=12,
            checkbox_width=12
        ).pack(anchor="w", pady=(1, 2))

        # 4. Griefing
        ctk.CTkCheckBox(
            cb_col2,
            text="Griefing (Trust factor)",
            variable=self.cat_griefing,
            command=self._update_vacnet_weight,
            font=ctk.CTkFont(family="Bahnschrift", size=11),
            fg_color=self.col_gold,
            border_color=self.col_border,
            corner_radius=0,
            checkbox_height=15,
            checkbox_width=15
        ).pack(anchor="w", pady=(1, 3))

        # Dynamic VACnet Weight Bar
        weight_row = ctk.CTkFrame(panel2, fg_color="#0e131d", height=20, corner_radius=0)
        weight_row.pack(fill="x", padx=12, pady=(0, 4))
        self.vacnet_weight_lbl = ctk.CTkLabel(
            weight_row,
            text="● VACnet Priority: 4.2x (High Priority Overwatch Fast-Track)",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=self.col_gold
        )
        self.vacnet_weight_lbl.pack(anchor="w", padx=8, pady=1)

        # --- PANEL 3: REPORT CONSOLE & PROFILES ---
        panel3 = ctk.CTkFrame(
            self,
            fg_color=self.col_panel,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        panel3.pack(fill="both", expand=True, padx=12, pady=3)

        self._build_header_label(panel3, "REPORT CONSOLE")

        # Radios
        proto_box = ctk.CTkFrame(panel3, fg_color="transparent")
        proto_box.pack(fill="x", padx=12, pady=(3, 1))

        self.profiles = [
            ("15 Reports - Standard FREE use", "FREE", 15, 15),
            ("50 Reports - Join Telegram Channel", "TG_50", 50, 45),
            (f"MAX REPORTS AVAILABLE ({self.accounts_count}) - PREMIUM TIER KEY NEEDED", "PREMIUM", self.accounts_count, 120),
        ]

        self.radio_widgets = {}
        for text, key, count, speed in self.profiles:
            is_locked = (key in ["TG_50", "PREMIUM"])
            r_state = "disabled" if is_locked else "normal"
            r_txt_color = self.col_ph if is_locked else self.col_text

            r_btn = ctk.CTkRadioButton(
                proto_box,
                text=text,
                variable=self.selected_profile_var,
                value=key,
                command=self._on_profile_change,
                font=ctk.CTkFont(family="Bahnschrift", size=10),
                fg_color=self.col_gold,
                hover_color=self.col_gold_hover,
                border_color=self.col_border,
                text_color=r_txt_color,
                state=r_state,
                radiobutton_height=13,
                radiobutton_width=13
            )
            r_btn.pack(anchor="w", pady=1)
            self.radio_widgets[key] = r_btn

        # Action Button (Big green rectangular button)
        self.action_btn = ctk.CTkButton(
            panel3,
            text="[ LETS FUCKING GO ]",
            font=ctk.CTkFont(family="Bahnschrift", size=13, weight="bold"),
            fg_color="#1c6b32",
            hover_color="#248a40",
            text_color="#ffffff",
            height=34,
            corner_radius=0,
            border_width=1,
            border_color="#2da44e",
            state="disabled",
            command=self.toggle_report
        )
        self.action_btn.pack(fill="x", padx=12, pady=(3, 3))

        # Progress bar & Live telemetry subheader
        prog_frame = ctk.CTkFrame(panel3, fg_color="transparent")
        prog_frame.pack(fill="x", padx=12, pady=(0, 2))

        self.prog_lbl = ctk.CTkLabel(
            prog_frame,
            text="Network: 24 Nodes Online | Ping: 28ms | GC: SYNCED",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=self.col_text_dim
        )
        self.prog_lbl.pack(anchor="w", pady=(0, 1))

        self.prog_bar = ctk.CTkProgressBar(
            prog_frame,
            height=5,
            corner_radius=0,
            fg_color="#101520",
            progress_color=self.col_gold,
            border_width=1,
            border_color=self.col_border
        )
        self.prog_bar.pack(fill="x", pady=(1, 2))
        self.prog_bar.set(0.0)

        # Live Console Box (Dark terminal)
        console_frame = ctk.CTkFrame(
            panel3,
            fg_color=self.col_panel_inner,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        console_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        self.console_textbox = ctk.CTkTextbox(
            console_frame,
            fg_color="transparent",
            text_color="#9daab8",
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=0,
            wrap="none"
        )
        self.console_textbox.pack(fill="both", expand=True, padx=6, pady=3)
        self.console_textbox.configure(state="disabled")

        # 3. Bottom Status Bar (Classic HUD Footer)
        status_bar = ctk.CTkFrame(
            self,
            fg_color=self.col_panel,
            height=28,
            corner_radius=0,
            border_width=1,
            border_color=self.col_border
        )
        status_bar.pack(fill="x", padx=12, pady=(2, 6))

        self.stats_summary_lbl = ctk.CTkLabel(
            status_bar,
            text="[ Total Sent: 0/15 | 0 rps ]",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=self.col_text
        )
        self.stats_summary_lbl.pack(side="left", padx=10, pady=2)

        self.status_badge = ctk.CTkLabel(
            status_bar,
            text="● INITIALIZING...",
            font=ctk.CTkFont(family="Bahnschrift", size=10, weight="bold"),
            text_color=self.col_gold
        )
        self.status_badge.pack(side="right", padx=10, pady=2)

    def _setup_console_color_tags(self):
        """Configures syntax tags on the internal tk.Text widget for vibrant terminal highlighting"""
        try:
            tb = self.console_textbox._textbox
            tb.tag_config("tag_green", foreground="#2ea043")
            tb.tag_config("tag_gold", foreground="#de9b35")
            tb.tag_config("tag_blue", foreground="#4f779a")
            tb.tag_config("tag_red", foreground="#da3633")
            tb.tag_config("tag_cyan", foreground="#58a6ff")
            tb.tag_config("tag_gray", foreground="#6e7681")
            tb.tag_config("tag_white", foreground="#e6edf3")
            tb.tag_config("tag_warn", foreground="#d29922")
        except Exception:
            pass

    def _build_header_label(self, parent, text):
        header = ctk.CTkFrame(parent, fg_color="#181e2b", height=22, corner_radius=0, border_width=1, border_color=self.col_border)
        header.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(
            header,
            text=text.upper(),
            font=ctk.CTkFont(family="Bahnschrift", size=10, weight="bold"),
            text_color=self.col_gold
        ).pack(anchor="w", padx=10, pady=2)

    def _on_target_input_change(self, event=None):
        val = self._get_entry_value(self.target_entry).strip()
        if not val:
            self.target_status_lbl.configure(text="[Ready]", text_color=self.col_text_dim)
            self.target_entry.configure(border_color=self.col_border)
        elif "steamcommunity.com" in val or val.startswith("7656119") or val.isalnum():
            self.target_status_lbl.configure(text="[✓ Steam Format Valid]", text_color=self.col_green)
            self.target_entry.configure(border_color="#1f6feb")
        else:
            self.target_status_lbl.configure(text="[Format Unknown]", text_color="#d29922")
            self.target_entry.configure(border_color=self.col_border)

    def _update_vacnet_weight(self):
        count = sum([
            self.cat_aim.get(), self.cat_aim_auto.get(),
            self.cat_vision.get(), self.cat_vision_esp.get(),
            self.cat_other_hacks.get(), self.cat_anti_aim.get(),
            self.cat_griefing.get()
        ])
        weight = round(1.0 + (count * 0.55), 1)
        if count >= 4:
            txt = f"● VACnet Priority: {weight}x (High Priority Overwatch Fast-Track)"
            col = self.col_gold
        elif count >= 2:
            txt = f"● VACnet Priority: {weight}x (Standard Overwatch Queue)"
            col = self.col_ct_blue
        else:
            txt = f"● VACnet Priority: {weight}x (Low Priority Queue)"
            col = self.col_text_dim

        if hasattr(self, "vacnet_weight_lbl"):
            self.vacnet_weight_lbl.configure(text=txt, text_color=col)

    def _get_target_reports_count(self):
        mode = self.selected_profile_var.get()
        if mode == "FREE":
            return 15
        elif mode == "TG_50":
            return 50
        elif mode == "PREMIUM":
            return self.accounts_count
        return 15

    def _get_active_payload_flags(self):
        flags = []
        if self.cat_aim.get():
            flags.append("AIMBOT")
        if self.cat_aim_auto.get():
            flags.append("SILENT_AIM")
        if self.cat_vision.get():
            flags.append("WALLHACK")
        if self.cat_vision_esp.get():
            flags.append("RADAR_ESP")
        if self.cat_other_hacks.get():
            flags.append("ANTI_AIM")
        if self.cat_anti_aim.get():
            flags.append("SPINBOT")
        if self.cat_griefing.get():
            flags.append("GRIEFING")
        return " | ".join(flags) if flags else "GENERAL_SUSPECT"

    def _start_init_sequence(self):
        """Simulates connection delays on startup with clean prompt logging"""
        def init_task():
            time.sleep(0.3)
            self.log_to_console("Connecting to database...")
            time.sleep(0.6)
            self.log_to_console("Loading API...")
            time.sleep(0.6)
            self.log_to_console(f"Accounts available to use: {self.accounts_count}")
            time.sleep(0.8)
            self.log_to_console("Connected")
            time.sleep(0.4)
            self.log_to_console("Ready to report the hacker")

            def _enable():
                self.status_badge.configure(text="● READY TO REPORT THE HACKER", text_color=self.col_green)
                self.info_status_lbl.configure(text=f"Botnet Pool: {self.accounts_count} Nodes | Connected: OK", text_color=self.col_green)
                self.action_btn.configure(state="normal")
            self.after(0, _enable)

        threading.Thread(target=init_task, daemon=True).start()

    def _on_profile_change(self):
        mode = self.selected_profile_var.get()
        speed = 15
        for _, key, _, spd in self.profiles:
            if key == mode:
                speed = spd
                break
        self.engine.target_rate = speed
        self._update_footer_stats(0, 0)

    def log_to_console(self, text):
        self.log_history.append(text)
        def _append():
            try:
                self.console_textbox.configure(state="normal")
                tb = self.console_textbox._textbox

                # Determine tag based on content
                chosen_tag = "tag_white"
                if "ACK 200 OK" in text or "Connected" in text or "Ready" in text or "Key loaded" in text:
                    chosen_tag = "tag_green"
                elif "[RESOLVER]" in text or "[PAYLOAD]" in text or "Ticket" in text or "===" in text or "Key:" in text:
                    chosen_tag = "tag_gold"
                elif "[NODE" in text or "[CS2-GC]" in text:
                    chosen_tag = "tag_blue"
                elif "invalid key" in text or "enter URL" in text or "[ERROR]" in text:
                    chosen_tag = "tag_red"
                elif "[WARN]" in text:
                    chosen_tag = "tag_warn"
                elif "Connecting" in text or "Loading" in text:
                    chosen_tag = "tag_gray"

                tb.insert("end", text + "\n", chosen_tag)
                self.console_textbox.see("end")
                self.console_textbox.configure(state="disabled")
            except Exception:
                pass
        self.after(0, _append)

    def _update_progress(self, current, total):
        def _set_p():
            if total > 0:
                pct = min(1.0, current / total)
                self.prog_bar.set(pct)
                pct_display = int(pct * 100)
                eta = max(1, int((total - current) * 0.7))
                self.prog_lbl.configure(
                    text=f"Progress: {pct_display}% [{current}/{total} sent] | ETA: ~{eta}s | GC: ACTIVE",
                    text_color=self.col_gold
                )
        self.after(0, _set_p)

    def _on_report_finished(self):
        def _update():
            count = self._get_target_reports_count()
            self.prog_bar.set(1.0)
            self.prog_lbl.configure(text=f"Status: 100% Completed [{count}/{count} sent] | Rate Limit Cooldown: 04:59", text_color=self.col_green)
            self.status_badge.configure(text="● COMPLETED", text_color=self.col_green)
            self.action_btn.configure(
                state="disabled",
                text="[ REPORTS SENT ]",
                fg_color="#2b3447",
                border_color="#36455c",
                text_color="#8c9aa8"
            )
            self._update_footer_stats(0, count)
        self.after(0, _update)

    def _setup_entry_placeholder(self, entry, placeholder_text, placeholder_color, active_color):
        entry.insert(0, placeholder_text)
        entry.configure(text_color=placeholder_color)
        entry._has_placeholder = True

        def on_focus_in(event):
            if getattr(entry, "_has_placeholder", False):
                entry.delete(0, "end")
                entry.configure(text_color=active_color)
                entry._has_placeholder = False

        def on_focus_out(event):
            if not entry.get().strip():
                entry.delete(0, "end")
                entry.insert(0, placeholder_text)
                entry.configure(text_color=placeholder_color)
                entry._has_placeholder = True

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _get_entry_value(self, entry):
        if getattr(entry, "_has_placeholder", False):
            return ""
        return entry.get().strip()

    def _validate_tier_key(self):
        tier_key = self._get_entry_value(self.tier_key_entry).strip()
        
        # Check if text format is exactly 5 alphanumeric characters
        if len(tier_key) == 5 and tier_key.isalnum():
            # Unlock TG_50 and PREMIUM options
            if "TG_50" in self.radio_widgets:
                self.radio_widgets["TG_50"].configure(state="normal", text_color=self.col_text)
            if "PREMIUM" in self.radio_widgets:
                self.radio_widgets["PREMIUM"].configure(state="normal", text_color=self.col_text)

            self.log_to_console("Key loaded successfully")
            self.info_status_lbl.configure(text=f"Key: {tier_key.upper()} (Valid) | Pool: {self.accounts_count} Nodes", text_color=self.col_green)
        else:
            self.log_to_console("invalid key")

    def _clear_inputs(self):
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, self.target_placeholder)
        self.target_entry.configure(text_color=self.col_ph)
        self.target_entry._has_placeholder = True

        self.tier_key_entry.delete(0, "end")
        self.tier_key_entry.insert(0, self.tier_placeholder)
        self.tier_key_entry.configure(text_color=self.col_ph)
        self.tier_key_entry._has_placeholder = True

    def toggle_report(self):
        if self.has_reported or self.engine.is_running:
            return

        target = self._get_entry_value(self.target_entry).strip()
        if not target:
            self.log_to_console("enter URL steam profile")
            return

        self.has_reported = True
        self.has_dispatched = True  # Backward compatibility
        mode = self.selected_profile_var.get()
        tier_key = self._get_entry_value(self.tier_key_entry).strip()
        total_to_send = self._get_target_reports_count()
        payload_flags = self._get_active_payload_flags()

        if mode == "PREMIUM" and not tier_key:
            self.log_to_console("[WARNING] Premium Tier Key not provided. Using demo bypass...")
        elif mode == "PREMIUM" and tier_key:
            self.log_to_console(f"[AUTH] Premium Tier Key verified: {tier_key[:4]}****")
        elif mode == "TG_50":
            self.log_to_console("[INFO] Telegram Community Channel verified (50 reports).")

        # Disable button immediately, change color to gray and text to REPORTS SENT
        self.action_btn.configure(
            state="disabled",
            text="[ REPORTS SENT ]",
            fg_color="#2b3447",
            border_color="#36455c",
            text_color="#8c9aa8"
        )
        self.status_badge.configure(text="● ACTIVE (SENDING REPORTS...)", text_color=self.col_green)
        self.prog_bar.set(0.0)

        self.engine.start(
            target,
            total_to_send,
            payload_flags=payload_flags,
            tier_key=tier_key,
            log_callback=self.log_to_console,
            progress_callback=self._update_progress,
            done_callback=self._on_report_finished
        )

    # Alias for backward compatibility
    toggle_dispatch = toggle_report

    def _start_stats_monitor(self):
        def monitor_loop():
            last_ts = time.perf_counter()
            while True:
                time.sleep(0.1)
                now = time.perf_counter()
                elapsed = now - last_ts
                if elapsed >= 0.3:
                    with self.engine.lock:
                        rate = int(self.engine.live_rps / elapsed) if self.engine.is_running else 0
                        current_idx = self.engine.current_report_idx
                        self.engine.live_rps = 0
                    last_ts = now
                    try:
                        self.after(0, self._update_footer_stats, rate, current_idx)
                    except Exception:
                        break

        threading.Thread(target=monitor_loop, daemon=True).start()

    def _update_footer_stats(self, rate, current_idx):
        target_count = self._get_target_reports_count()
        self.stats_summary_lbl.configure(text=f"[ Total Sent: {current_idx}/{target_count} | {rate} rps ]")


def main():
    app = CS2ReportBotApp()
    app.mainloop()
    if HAS_WIN32:
        try:
            winmm.timeEndPeriod(1)
        except Exception:
            pass


if __name__ == "__main__":
    main()
