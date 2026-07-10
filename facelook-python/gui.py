import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
 
import customtkinter as ctk
 
# Add project root to sys.path so we can import facelook
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
 
try:
    from facelook.config import FaceLookConfig
    from facelook.crypto_store import CryptoStore
    from facelook.database import BiometricDatabase
    DEMO_MODE = False
except ImportError:
    DEMO_MODE = True
 
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")
 
 
# ── Demo stubs ────────────────────────────────────────────────────────────────
class _DemoDB:
    def stats(self):
        return {"total_users": 24, "active_users": 18, "total_auth_logs": 142}
 
    def list_users(self):
        import datetime
        return [
            {"username": "alexandra.deff",   "active": True,  "created_at": "2024-11-20T08:30:00"},
            {"username": "edwin.adenike",     "active": True,  "created_at": "2024-11-22T10:15:00"},
            {"username": "isaac.oluwatem",    "active": False, "created_at": "2024-11-25T14:00:00"},
            {"username": "david.oshodi",      "active": True,  "created_at": "2024-12-01T09:45:00"},
            {"username": "sarah.johnson",     "active": True,  "created_at": "2024-12-03T11:20:00"},
        ]
 
    def list_auth_logs(self, limit=50):
        return [
            {"username": "alexandra.deff",  "result": "AUTH_OK",  "reason": "Face matched",   "confidence": "0.97", "created_at": "2024-12-05T08:31:00"},
            {"username": "unknown_visitor",  "result": "REJECTED", "reason": "No match",       "confidence": "0.21", "created_at": "2024-12-05T08:29:00"},
            {"username": "edwin.adenike",   "result": "AUTH_OK",  "reason": "Face matched",   "confidence": "0.94", "created_at": "2024-12-05T07:55:00"},
            {"username": "david.oshodi",    "result": "AUTH_OK",  "reason": "Face matched",   "confidence": "0.91", "created_at": "2024-12-04T17:40:00"},
            {"username": "isaac.oluwatem",  "result": "REJECTED", "reason": "User inactive",  "confidence": "-",    "created_at": "2024-12-04T16:10:00"},
            {"username": "sarah.johnson",   "result": "AUTH_OK",  "reason": "Face matched",   "confidence": "0.88", "created_at": "2024-12-04T09:05:00"},
        ]
 
    def delete_user(self, username): pass
    def permanently_delete_user(self, username): pass
 
 
# ── Colour palette (matches screenshot) ───────────────────────────────────────
C = {
    # backgrounds
    "bg":           "#F4F6F3",
    "sidebar_bg":   "#FFFFFF",
    "card":         "#FFFFFF",
    "card2":        "#F9FAF8",
    "dark_card":    "#1B3A2D",   # deep green card (Total Projects style)
 
    # greens
    "green":        "#2D6A4F",
    "green_mid":    "#40916C",
    "green_light":  "#74C69D",
    "green_pale":   "#D8F3DC",
    "green_btn":    "#1B4332",
    "green_hover":  "#2D6A4F",
    "green_accent": "#52B788",
 
    # neutrals
    "white":        "#FFFFFF",
    "text_dark":    "#1A2E1E",
    "text_mid":     "#3D5A47",
    "text_muted":   "#7A9E8B",
    "border":       "#DCE8DC",
    "divider":      "#E8F0E8",
 
    # state
    "success":      "#2D6A4F",
    "success_bg":   "#D8F3DC",
    "danger":       "#C0392B",
    "danger_bg":    "#FDECEA",
    "warning":      "#A67C00",
    "warning_bg":   "#FFF8E1",
    "badge_blue":   "#1565C0",
    "badge_blue_bg":"#E3F2FD",
 
    # topbar
    "topbar_bg":    "#FFFFFF",
}
 
FONT = "Segoe UI"
 
 
class FaceLookGUI(ctk.CTk):
    """FaceLook Administration – green project-dashboard aesthetic."""
 
    def __init__(self):
        super().__init__()
        self.title("FaceLook  ·  Administration")
        self.geometry("1200x760")
        self.minsize(1050, 660)
        self.configure(fg_color=C["bg"])
 
        if DEMO_MODE:
            self.db = _DemoDB()
        else:
            self.crypto = CryptoStore(FaceLookConfig.KEY_PATH)
            self.db     = BiometricDatabase(FaceLookConfig.DATABASE_PATH, self.crypto)
 
        self.service_process  = None
        self.active_page      = None
        self.nav_buttons      = {}
        self.user_search_var  = tk.StringVar()
        self.log_search_var   = tk.StringVar()
        self.log_filter_var   = tk.StringVar(value="All")
 
        self._build_shell()
        self.show_dashboard()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(1200, self._watch_service)
 
    # ── Shell ──────────────────────────────────────────────────────────────────
    def _build_shell(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
 
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=C["sidebar_bg"],
                                    border_width=1, border_color=C["border"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(10, weight=1)
 
        # Main workspace
        self.workspace = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(1, weight=1)
 
        self._build_sidebar()
        self._build_topbar()
        self._build_content_area()
 
    def _build_sidebar(self):
        # Brand
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=20, pady=(28, 18), sticky="ew")
        brand.grid_columnconfigure(1, weight=1)
 
        logo_frame = ctk.CTkFrame(brand, width=44, height=44, corner_radius=12,
                                  fg_color=C["green_btn"])
        logo_frame.grid(row=0, column=0)
        logo_frame.grid_propagate(False)
        ctk.CTkLabel(logo_frame, text="FL", text_color=C["white"],
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")
 
        txt = ctk.CTkFrame(brand, fg_color="transparent")
        txt.grid(row=0, column=1, padx=(12, 0), sticky="ew")
        ctk.CTkLabel(txt, text="FaceLook", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=18, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(txt, text="Administration", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11), anchor="w").grid(row=1, column=0, sticky="w")
 
        div = ctk.CTkFrame(self.sidebar, height=1, fg_color=C["divider"])
        div.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")
 
        # Nav label
        ctk.CTkLabel(self.sidebar, text="MENU", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=10, weight="bold"), anchor="w").grid(
                     row=2, column=0, padx=20, pady=(4, 4), sticky="w")
 
        self._nav_btn("Dashboard",    "dashboard", self.show_dashboard, row=3)
        self._nav_btn("Manage Users", "users",     self.show_users,     row=4)
        self._nav_btn("Enroll Face",  "enroll",    self.show_enroll,    row=5)
        self._nav_btn("Auth Logs",    "logs",      self.show_logs,      row=6)
 
        div2 = ctk.CTkFrame(self.sidebar, height=1, fg_color=C["divider"])
        div2.grid(row=7, column=0, padx=16, pady=(12, 8), sticky="ew")
 
        ctk.CTkLabel(self.sidebar, text="GENERAL", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=10, weight="bold"), anchor="w").grid(
                     row=8, column=0, padx=20, pady=(0, 4), sticky="w")
        # Simple Help page only — Settings removed for a cleaner sidebar
        self._nav_btn("Help", "help", self.show_help, row=9)
 
        # Service status pill at the bottom
        status_frame = ctk.CTkFrame(self.sidebar, fg_color=C["card2"],
                                    corner_radius=14, border_width=1, border_color=C["border"])
        status_frame.grid(row=11, column=0, padx=16, pady=(12, 24), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(status_frame, text="Service Status", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=14, pady=(12, 4), sticky="w")
        self.sidebar_status = ctk.CTkLabel(status_frame, text="● STOPPED",
                                           text_color=C["danger"],
                                           font=ctk.CTkFont(family=FONT, size=12, weight="bold"), anchor="w")
        self.sidebar_status.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")
 
    def _nav_btn(self, text, key, command, row):
        icons = {"dashboard": "⊞", "users": "◎", "enroll": "◈", "logs": "≡", "help": "♡"}
        ic = icons.get(key, "·")
        btn = ctk.CTkButton(self.sidebar, text=f"  {ic}  {text}", height=42, corner_radius=10,
                            anchor="w", command=command,
                            fg_color="transparent", hover_color=C["green_pale"],
                            text_color=C["text_mid"],
                            font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        btn.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
        self.nav_buttons[key] = btn
 
    def _nav_btn_secondary(self, text, row):
        btn = ctk.CTkButton(self.sidebar, text=f"  ⊙  {text}", height=38, corner_radius=10,
                            anchor="w", fg_color="transparent", hover_color=C["green_pale"],
                            text_color=C["text_muted"],
                            font=ctk.CTkFont(family=FONT, size=13))
        btn.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
 
    def _set_active_nav(self, key):
        self.active_page = key
        for name, btn in self.nav_buttons.items():
            icons = {"dashboard": "⊞", "users": "◎", "enroll": "◈", "logs": "≡", "help": "♡"}
            ic = icons.get(name, "·")
            label = f"  {ic}  " + {"dashboard": "Dashboard", "users": "Manage Users",
                                    "enroll": "Enroll Face", "logs": "Auth Logs",
                                    "help": "Help"}[name]
            if name == key:
                btn.configure(fg_color=C["green_btn"], hover_color=C["green_hover"],
                              text_color=C["white"], text=label)
            else:
                btn.configure(fg_color="transparent", hover_color=C["green_pale"],
                              text_color=C["text_mid"], text=label)
 
    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(self.workspace, fg_color="transparent", height=80)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 0))
        self.topbar.grid_columnconfigure(0, weight=1)
        self.topbar.grid_propagate(False)
 
        titles = ctk.CTkFrame(self.topbar, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        self.lbl_title = ctk.CTkLabel(titles, text="", text_color=C["text_dark"],
                                      font=ctk.CTkFont(family=FONT, size=26, weight="bold"), anchor="w")
        self.lbl_title.grid(row=0, column=0, sticky="w")
        self.lbl_sub = ctk.CTkLabel(titles, text="", text_color=C["text_muted"],
                                    font=ctk.CTkFont(family=FONT, size=13), anchor="w")
        self.lbl_sub.grid(row=1, column=0, sticky="w", pady=(2, 0))
 
        # Top-right action buttons area
        actions = ctk.CTkFrame(self.topbar, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        self.top_status_lbl = ctk.CTkLabel(actions, text="● Ready", text_color=C["text_muted"],
                                           font=ctk.CTkFont(family=FONT, size=12))
        self.top_status_lbl.grid(row=0, column=0, padx=(0, 12))
 
        self.btn_add = ctk.CTkButton(actions, text="+ Add User", height=38, corner_radius=10,
                                     width=120, fg_color=C["green_btn"], hover_color=C["green_hover"],
                                     text_color=C["white"],
                                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                                     command=self.show_enroll)
        self.btn_add.grid(row=0, column=1, padx=(0, 8))
 
        self.btn_import = ctk.CTkButton(actions, text="Import Data", height=38, corner_radius=10,
                                        width=110, fg_color=C["white"], hover_color=C["green_pale"],
                                        text_color=C["text_dark"], border_width=1, border_color=C["border"],
                                        font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                                        command=lambda: self._show_top_status("Import not available in demo", "warning"))
        self.btn_import.grid(row=0, column=2)
 
    def _build_content_area(self):
        self.content = ctk.CTkScrollableFrame(self.workspace, corner_radius=0,
                                              fg_color=C["bg"], scrollbar_button_color=C["green_pale"])
        self.content.grid(row=1, column=0, padx=0, pady=(12, 0), sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
 
    def _set_header(self, title, subtitle):
        self.lbl_title.configure(text=title)
        self.lbl_sub.configure(text=subtitle)
 
    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        for i in range(12):
            self.content.grid_rowconfigure(i, weight=0)
            self.content.grid_columnconfigure(i, weight=0)
        self.content.grid_columnconfigure(0, weight=1)
 
    def _show_top_status(self, text, tone="info"):
        colors = {"info": C["text_muted"], "success": C["success"],
                  "danger": C["danger"], "warning": C["warning"]}
        self.top_status_lbl.configure(text=f"● {text}", text_color=colors.get(tone, C["text_muted"]))
 
    # ── Helpers ────────────────────────────────────────────────────────────────
    def _card(self, master, **grid_kw):
        f = ctk.CTkFrame(master, fg_color=C["card"], corner_radius=16,
                         border_width=1, border_color=C["border"])
        f.grid(**grid_kw)
        return f
 
    def _dark_card(self, master, **grid_kw):
        f = ctk.CTkFrame(master, fg_color=C["dark_card"], corner_radius=16)
        f.grid(**grid_kw)
        return f
 
    def _primary_button(self, master, text, command=None, width=140):
        return ctk.CTkButton(master, text=text, width=width, height=38, corner_radius=10,
                             fg_color=C["green_btn"], hover_color=C["green_hover"],
                             text_color=C["white"],
                             font=ctk.CTkFont(family=FONT, size=13, weight="bold"), command=command)
 
    def _secondary_button(self, master, text, command=None, width=110):
        return ctk.CTkButton(master, text=text, width=width, height=38, corner_radius=10,
                             fg_color=C["white"], hover_color=C["green_pale"],
                             text_color=C["text_dark"], border_width=1, border_color=C["border"],
                             font=ctk.CTkFont(family=FONT, size=13), command=command)
 
    def _danger_button(self, master, text, command=None, width=100):
        return ctk.CTkButton(master, text=text, width=width, height=34, corner_radius=9,
                             fg_color=C["danger_bg"], hover_color="#FBCDD2",
                             text_color=C["danger"], border_width=0,
                             font=ctk.CTkFont(family=FONT, size=12, weight="bold"), command=command)
 
    def _badge(self, master, text, bg, fg, **grid_kw):
        lbl = ctk.CTkLabel(master, text=text, width=90, height=26, corner_radius=13,
                           fg_color=bg, text_color=fg,
                           font=ctk.CTkFont(family=FONT, size=11, weight="bold"))
        lbl.grid(**grid_kw)
        return lbl
 
    def _section_title(self, master, text, row, padx=(24, 24), pady=(22, 8)):
        ctk.CTkLabel(master, text=text, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold"), anchor="w").grid(
                     row=row, column=0, padx=padx, pady=pady, sticky="w")
 
    # ── Dashboard ──────────────────────────────────────────────────────────────
    def show_dashboard(self):
        self._set_active_nav("dashboard")
        self._set_header("Dashboard", "Plan, prioritize, and accomplish your tasks with ease.")
        self._clear_content()
 
        stats = self._safe_stats()
 
        # ── Row 0 : stat cards ──────────────────────────────────────────────
        cards_row = ctk.CTkFrame(self.content, fg_color="transparent")
        cards_row.grid(row=0, column=0, padx=28, pady=(16, 8), sticky="ew")
        for i in range(4):
            cards_row.grid_columnconfigure(i, weight=1)
 
        self._stat_card_dark(cards_row, "Total Users",  str(stats.get("total_users", 0)),  "↑ Increased from last month", 0)
        self._stat_card_white(cards_row, "Active Users", str(stats.get("active_users", 0)), "↑ Increased from last month", 1)
        self._stat_card_white(cards_row, "Running Svc",  "1" if self.is_service_running() else "0", "↑ Increased from last month", 2)
        self._stat_card_white(cards_row, "Auth Logs",   str(stats.get("total_auth_logs", 0)), "Recorded attempts", 3)
 
        # ── Row 1 : analytics + reminders + project list ────────────────────
        mid_row = ctk.CTkFrame(self.content, fg_color="transparent")
        mid_row.grid(row=1, column=0, padx=28, pady=(8, 8), sticky="ew")
        mid_row.grid_columnconfigure(0, weight=3)
        mid_row.grid_columnconfigure(1, weight=2)
        mid_row.grid_columnconfigure(2, weight=2)
 
        # Analytics card
        analytics = self._card(mid_row, row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        analytics.grid_columnconfigure(0, weight=1)
        self._section_title(analytics, "Authentication Analytics", 0)
        self._draw_bar_chart(analytics, row=1)
 
        # Reminders / Service Control card
        remind = self._dark_card(mid_row, row=0, column=1, padx=8, pady=0, sticky="nsew")
        remind.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(remind, text="Service Control", text_color=C["green_light"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=22, pady=(22, 4), sticky="w")
        ctk.CTkLabel(remind, text="Camera Auth\nService", text_color=C["white"],
                     font=ctk.CTkFont(family=FONT, size=22, weight="bold"), anchor="w",
                     justify="left").grid(row=1, column=0, padx=22, pady=(0, 4), sticky="w")
        self.lbl_status = ctk.CTkLabel(remind, text="STOPPED", text_color=C["green_light"],
                                       font=ctk.CTkFont(family=FONT, size=12), anchor="w")
        self.lbl_status.grid(row=2, column=0, padx=22, pady=(0, 14), sticky="w")
 
        btns = ctk.CTkFrame(remind, fg_color="transparent")
        btns.grid(row=3, column=0, padx=22, pady=(0, 22), sticky="w")
        self.btn_start = ctk.CTkButton(btns, text="▶  Start", width=100, height=36, corner_radius=18,
                                       fg_color=C["green_accent"], hover_color=C["green_mid"],
                                       text_color=C["white"],
                                       font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                                       command=self.start_service)
        self.btn_start.grid(row=0, column=0, padx=(0, 8))
        self.btn_stop = ctk.CTkButton(btns, text="■  Stop", width=90, height=36, corner_radius=18,
                                      fg_color="#7F1D1D", hover_color="#991B1B",
                                      text_color=C["white"],
                                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                                      command=self.stop_service)
        self.btn_stop.grid(row=0, column=1)
 
        # Recent users card
        proj = self._card(mid_row, row=0, column=2, padx=(8, 0), pady=0, sticky="nsew")
        proj.grid_columnconfigure(0, weight=1)
        header_f = ctk.CTkFrame(proj, fg_color="transparent")
        header_f.grid(row=0, column=0, padx=18, pady=(18, 8), sticky="ew")
        header_f.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_f, text="Recent Users", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=15, weight="bold"), anchor="w").grid(
                     row=0, column=0, sticky="w")
        self._primary_button(header_f, "+ New", self.show_enroll, width=70).grid(row=0, column=1)
 
        try:
            users = self.db.list_users()[:5]
        except Exception:
            users = []
 
        for idx, user in enumerate(users):
            uname  = str(user.get("username", "Unknown"))
            active = bool(user.get("active"))
            self._mini_user_row(proj, idx + 1, uname, active)
 
        # ── Row 2 : team collab + project progress + time tracker ───────────
        bot_row = ctk.CTkFrame(self.content, fg_color="transparent")
        bot_row.grid(row=2, column=0, padx=28, pady=(8, 28), sticky="ew")
        bot_row.grid_columnconfigure(0, weight=3)
        bot_row.grid_columnconfigure(1, weight=2)
        bot_row.grid_columnconfigure(2, weight=2)
 
        # Team collab
        team = self._card(bot_row, row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        team.grid_columnconfigure(0, weight=1)
        th = ctk.CTkFrame(team, fg_color="transparent")
        th.grid(row=0, column=0, padx=20, pady=(18, 8), sticky="ew")
        th.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(th, text="Team Collaboration", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=15, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(th, text="+ Add Member", height=32, corner_radius=16, width=120,
                      fg_color=C["white"], hover_color=C["green_pale"], text_color=C["text_dark"],
                      border_width=1, border_color=C["border"],
                      font=ctk.CTkFont(family=FONT, size=12), command=self.show_enroll).grid(row=0, column=1)
 
        try:
            users_all = self.db.list_users()[:4]
        except Exception:
            users_all = []
 
        labels = ["Working on Github Project Repository", "Integrate User Auth System",
                  "Develop Search & Filter Functionality", "Responsive Layout for Homepage"]
        statuses = ["Completed", "In Progress", "Pending", "In Progress"]
        status_colors = [C["success"], C["badge_blue"], C["warning"], C["badge_blue"]]
        status_bgs    = [C["success_bg"], C["badge_blue_bg"], C["warning_bg"], C["badge_blue_bg"]]
 
        for i, user in enumerate(users_all):
            uname = str(user.get("username", "Unknown"))
            lbl   = labels[i] if i < len(labels) else ""
            st    = statuses[i] if i < len(statuses) else "Unknown"
            sbg   = status_bgs[i] if i < len(status_bgs) else C["green_pale"]
            sfg   = status_colors[i] if i < len(status_colors) else C["success"]
            self._collab_row(team, i + 1, uname, lbl, st, sbg, sfg)
 
        ctk.CTkFrame(team, height=1, fg_color="transparent").grid(row=99, column=0, pady=8)
 
        # Auth progress donut
        prog = self._card(bot_row, row=0, column=1, padx=8, pady=0, sticky="nsew")
        prog.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(prog, text="Auth Progress", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=15, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=20, pady=(18, 8), sticky="w")
        self._draw_donut(prog, row=1)
 
        # Quick stats / time tracker dark card
        tracker = self._dark_card(bot_row, row=0, column=2, padx=(8, 0), pady=0, sticky="nsew")
        tracker.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tracker, text="Quick Stats", text_color=C["green_light"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=22, pady=(22, 8), sticky="w")
 
        stat_items = [
            ("Total Users",    str(stats.get("total_users", 0))),
            ("Active Users",   str(stats.get("active_users", 0))),
            ("Auth Logs",      str(stats.get("total_auth_logs", 0))),
            ("Service",        "Running" if self.is_service_running() else "Stopped"),
        ]
        for r, (k, v) in enumerate(stat_items):
            row_f = ctk.CTkFrame(tracker, fg_color="transparent")
            row_f.grid(row=r + 1, column=0, padx=22, pady=4, sticky="ew")
            row_f.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row_f, text=k, text_color=C["text_muted"],
                         font=ctk.CTkFont(family=FONT, size=12), anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row_f, text=v, text_color=C["white"],
                         font=ctk.CTkFont(family=FONT, size=18, weight="bold"), anchor="e").grid(row=0, column=1, sticky="e")
 
        ctk.CTkFrame(tracker, height=1, fg_color="transparent").grid(row=10, column=0, pady=10)
 
        self._update_service_ui()
 
    def _stat_card_dark(self, master, title, value, caption, col):
        card = ctk.CTkFrame(master, fg_color=C["dark_card"], corner_radius=16)
        card.grid(row=0, column=col, padx=(0, 8) if col == 0 else (8, 8), pady=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=C["green_light"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=18, pady=(18, 0), sticky="w")
        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.grid(row=1, column=0, padx=18, pady=(4, 0), sticky="ew")
        val_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(val_row, text=value, text_color=C["white"],
                     font=ctk.CTkFont(family=FONT, size=36, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        arrow = ctk.CTkLabel(val_row, text="↗", width=28, height=28, corner_radius=14,
                             fg_color=C["green_mid"], text_color=C["white"],
                             font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        arrow.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(card, text=caption, text_color=C["green_accent"],
                     font=ctk.CTkFont(family=FONT, size=11), anchor="w").grid(
                     row=2, column=0, padx=18, pady=(2, 18), sticky="w")
 
    def _stat_card_white(self, master, title, value, caption, col):
        card = ctk.CTkFrame(master, fg_color=C["card"], corner_radius=16,
                            border_width=1, border_color=C["border"])
        card.grid(row=0, column=col, padx=(8, 0) if col == 3 else (8, 8), pady=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=18, pady=(18, 0), sticky="w")
        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.grid(row=1, column=0, padx=18, pady=(4, 0), sticky="ew")
        val_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(val_row, text=value, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=36, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        arrow = ctk.CTkLabel(val_row, text="↗", width=28, height=28, corner_radius=14,
                             fg_color=C["divider"], text_color=C["text_muted"],
                             font=ctk.CTkFont(family=FONT, size=13))
        arrow.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(card, text=caption, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11), anchor="w").grid(
                     row=2, column=0, padx=18, pady=(2, 18), sticky="w")
 
    def _draw_bar_chart(self, master, row):
        import tkinter as tk
        canvas = tk.Canvas(master, height=140, bg=C["card"], highlightthickness=0)
        canvas.grid(row=row, column=0, padx=24, pady=(0, 22), sticky="ew")
 
        bars = [55, 75, 90, 100, 60, 45, 70]
        days = ["S", "M", "T", "W", "T", "F", "S"]
        max_h, bw, gap = 100, 28, 16
        total_w = len(bars) * (bw + gap) - gap
        start_x = 30
        base_y  = 120
 
        master.update_idletasks()
        cw = canvas.winfo_reqwidth() or 350
        start_x = max(20, (cw - total_w) // 2)
 
        for i, (val, day) in enumerate(zip(bars, days)):
            x0 = start_x + i * (bw + gap)
            x1 = x0 + bw
            h  = int(val / 100 * max_h)
            y0 = base_y - h
            col = C["green"] if val == 100 else C["green_pale"]
            tc  = C["white"]  if val == 100 else C["green_mid"]
            # Rounded rect via polygon approximation
            r = 8
            pts = [x0 + r, y0, x1 - r, y0, x1, y0 + r, x1, base_y, x0, base_y, x0, y0 + r]
            canvas.create_polygon(pts, fill=col, smooth=False, outline="")
            # top label for tallest
            if val == 100:
                canvas.create_text((x0 + x1) // 2, y0 - 10, text=f"{val}%",
                                   fill=C["text_dark"], font=(FONT, 9, "bold"))
            canvas.create_text((x0 + x1) // 2, base_y + 12, text=day,
                               fill=C["text_muted"], font=(FONT, 10))
 
    def _draw_donut(self, master, row):
        import tkinter as tk, math
        canvas = tk.Canvas(master, width=180, height=180, bg=C["card"], highlightthickness=0)
        canvas.grid(row=row, column=0, pady=(0, 12))
 
        cx, cy, r_out, r_in = 90, 90, 72, 44
        # segments: completed, in-progress, pending
        pct   = [41, 35, 24]
        cols  = [C["green"], C["green_mid"], C["divider"]]
        start = -90.0
 
        def arc_points(cx, cy, r, start_deg, end_deg, steps=60):
            pts = []
            for s in range(steps + 1):
                a = math.radians(start_deg + (end_deg - start_deg) * s / steps)
                pts.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
            return pts
 
        for p, col in zip(pct, cols):
            sweep = 3.6 * p
            end   = start + sweep
            outer = arc_points(cx, cy, r_out, start, end)
            inner = arc_points(cx, cy, r_in, end, start)
            pts   = outer + inner
            if len(pts) >= 6:
                canvas.create_polygon(pts, fill=col, outline=C["card"], width=2, smooth=False)
            start = end
 
        canvas.create_oval(cx - r_in + 2, cy - r_in + 2, cx + r_in - 2, cy + r_in - 2,
                           fill=C["card"], outline="")
        canvas.create_text(cx, cy - 10, text=f"{pct[0]}%", fill=C["text_dark"],
                           font=(FONT, 18, "bold"))
        canvas.create_text(cx, cy + 10, text="Auth OK", fill=C["text_muted"], font=(FONT, 10))
 
        # legend
        leg = ctk.CTkFrame(master, fg_color="transparent")
        leg.grid(row=row + 1, column=0, padx=20, pady=(0, 18))
        labels = [("Completed", C["green"]), ("In Progress", C["green_mid"]), ("Pending", C["divider"])]
        for i, (lbl, col) in enumerate(labels):
            f = ctk.CTkFrame(leg, fg_color="transparent")
            f.grid(row=0, column=i, padx=6)
            dot = ctk.CTkLabel(f, text="●", text_color=col, font=ctk.CTkFont(family=FONT, size=14))
            dot.grid(row=0, column=0)
            ctk.CTkLabel(f, text=lbl, text_color=C["text_muted"],
                         font=ctk.CTkFont(family=FONT, size=10)).grid(row=0, column=1, padx=(2, 0))
 
    def _mini_user_row(self, master, row, username, active):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.grid(row=row, column=0, padx=18, pady=4, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        avatar = ctk.CTkLabel(f, text=username[0].upper(), width=32, height=32, corner_radius=16,
                              fg_color=C["green_pale"], text_color=C["green"],
                              font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        avatar.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(f, text=username, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"), anchor="w").grid(
                     row=0, column=1, padx=(10, 0), sticky="w")
        bg = C["success_bg"] if active else C["danger_bg"]
        fg = C["success"]    if active else C["danger"]
        ctk.CTkLabel(f, text="Active" if active else "Inactive", width=64, height=22,
                     corner_radius=11, fg_color=bg, text_color=fg,
                     font=ctk.CTkFont(family=FONT, size=10, weight="bold")).grid(row=0, column=2, padx=8)
        ctk.CTkFrame(master, height=1, fg_color=C["divider"]).grid(row=row + 20, column=0, padx=18, sticky="ew")
 
    def _collab_row(self, master, row, username, task, status, sbg, sfg):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.grid(row=row, column=0, padx=18, pady=5, sticky="ew")
        f.grid_columnconfigure(1, weight=1)
        avatar = ctk.CTkLabel(f, text=username[0].upper(), width=36, height=36, corner_radius=18,
                              fg_color=C["green_pale"], text_color=C["green"],
                              font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        avatar.grid(row=0, column=0, rowspan=2)
        ctk.CTkLabel(f, text=username, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"), anchor="w").grid(
                     row=0, column=1, padx=(10, 0), sticky="w")
        ctk.CTkLabel(f, text=f"Working on {task}", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11), anchor="w").grid(
                     row=1, column=1, padx=(10, 0), sticky="w")
        ctk.CTkLabel(f, text=status, width=80, height=22, corner_radius=11,
                     fg_color=sbg, text_color=sfg,
                     font=ctk.CTkFont(family=FONT, size=10, weight="bold")).grid(row=0, column=2, rowspan=2, padx=8)
        ctk.CTkFrame(master, height=1, fg_color=C["divider"]).grid(row=row + 10, column=0, padx=18, sticky="ew")
 
    # ── Service ────────────────────────────────────────────────────────────────
    def is_service_running(self):
        if self.service_process is None: return False
        if self.service_process.poll() is None: return True
        self.service_process = None
        return False
 
    def start_service(self):
        if self.is_service_running(): return
        try:
            self.service_process = subprocess.Popen(
                [sys.executable, "-m", "facelook.service", "--engine", "camera"],
                cwd=str(Path(__file__).parent))
            self._show_top_status("Service running", "success")
            self._update_service_ui()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._show_top_status("Start failed", "danger")
 
    def stop_service(self, silent=False):
        if self.service_process is None:
            self._update_service_ui(); return
        try:
            if self.service_process.poll() is None:
                self.service_process.terminate()
                try: self.service_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.service_process.kill(); self.service_process.wait(5)
            self.service_process = None
            self._show_top_status("Service stopped", "warning")
            self._update_service_ui()
        except Exception as exc:
            if not silent: messagebox.showerror("Error", str(exc))
 
    def _watch_service(self):
        self._update_service_ui()
        self.after(1200, self._watch_service)
 
    def _update_service_ui(self):
        running = self.is_service_running()
        txt = "● RUNNING" if running else "● STOPPED"
        col = C["green_accent"] if running else C["danger"]
        for attr in ("lbl_status", "sidebar_status"):
            w = getattr(self, attr, None)
            try:
                if w and w.winfo_exists():
                    w.configure(text=txt, text_color=col)
            except tk.TclError: pass
        for attr, state in (("btn_start", "disabled" if running else "normal"),
                            ("btn_stop",  "normal"   if running else "disabled")):
            w = getattr(self, attr, None)
            try:
                if w and w.winfo_exists():
                    w.configure(state=state)
            except tk.TclError: pass
 
    # ── Users ──────────────────────────────────────────────────────────────────
    def show_users(self):
        self._set_active_nav("users")
        self._set_header("Manage Users", "View enrolled users, disable access, or permanently remove profiles.")
        self._clear_content()
 
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=28, pady=(16, 8), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)
 
        search = ctk.CTkEntry(toolbar, textvariable=self.user_search_var,
                              placeholder_text="Search users...",
                              height=40, corner_radius=10,
                              fg_color=C["card"], border_color=C["border"],
                              text_color=C["text_dark"],
                              placeholder_text_color=C["text_muted"],
                              font=ctk.CTkFont(family=FONT, size=13))
        search.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._secondary_button(toolbar, "Refresh", self.load_users, width=100).grid(row=0, column=1, padx=(0, 8))
        self._primary_button(toolbar, "+ Enroll User", self.show_enroll, width=130).grid(row=0, column=2)
 
        table = self._card(self.content, row=1, column=0, padx=28, pady=(4, 28), sticky="nsew")
        table.grid_columnconfigure(0, weight=1)
 
        # Table header
        hdr = ctk.CTkFrame(table, fg_color=C["card2"], corner_radius=10)
        hdr.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        for col_i, (lbl, anchor, weight) in enumerate([
            ("User Profile", "w", 1),
            ("Status", "center", 0),
            ("Created", "w", 0),
            ("Actions", "e", 0),
        ]):
            # IMPORTANT:
            # `anchor` controls text alignment inside the label and accepts values
            # like "center". `grid(sticky=...)` only accepts combinations of
            # n/e/s/w, so using sticky="center" raises:
            # TclError: bad stickyness value "center".
            grid_sticky = "ew" if anchor == "center" else anchor

            ctk.CTkLabel(
                hdr,
                text=lbl,
                text_color=C["text_muted"],
                font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
                anchor=anchor,
            ).grid(row=0, column=col_i, padx=14, pady=10, sticky=grid_sticky)
            hdr.grid_columnconfigure(col_i, weight=weight)

        hdr.grid_columnconfigure(0, weight=1)
 
        self.users_scroll = ctk.CTkScrollableFrame(table, fg_color="transparent", height=400)
        self.users_scroll.grid(row=1, column=0, padx=10, pady=(0, 14), sticky="nsew")
        self.users_scroll.grid_columnconfigure(0, weight=1)
 
        self.user_search_var.trace_add("write", lambda *_: self.load_users())
        self.load_users()
 
    def load_users(self):
        if not hasattr(self, "users_scroll"): return
        for w in self.users_scroll.winfo_children(): w.destroy()
        try: users = self.db.list_users()
        except Exception as exc:
            self._empty_state(self.users_scroll, "Could not load users", str(exc)); return
 
        q = self.user_search_var.get().strip().lower()
        if q: users = [u for u in users if q in str(u.get("username", "")).lower()]
        if not users:
            self._empty_state(self.users_scroll, "No users found",
                              "Enroll a new face profile or change the search text."); return
        for i, user in enumerate(users):
            self._user_row(i, user)
 
    def _user_row(self, idx, user):
        username  = str(user.get("username", "Unknown"))
        active    = bool(user.get("active"))
        created   = str(user.get("created_at", ""))[:10] or "Unknown"
 
        row = ctk.CTkFrame(self.users_scroll,
                           fg_color=C["card2"] if idx % 2 == 0 else C["card"],
                           corner_radius=12)
        row.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
        row.grid_columnconfigure(0, weight=1)
 
        # Avatar + name
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, padx=14, pady=12, sticky="w")
        left.grid_columnconfigure(1, weight=1)
        av = ctk.CTkLabel(left, text=username[0].upper(), width=38, height=38, corner_radius=19,
                          fg_color=C["green_pale"], text_color=C["green"],
                          font=ctk.CTkFont(family=FONT, size=15, weight="bold"))
        av.grid(row=0, column=0, rowspan=2)
        ctk.CTkLabel(left, text=username, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=14, weight="bold"), anchor="w").grid(
                     row=0, column=1, padx=(12, 0), sticky="w")
        ctk.CTkLabel(left, text=f"Enrolled face profile", text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=12), anchor="w").grid(
                     row=1, column=1, padx=(12, 0), sticky="w")
 
        # Status badge
        bg = C["success_bg"] if active else C["danger_bg"]
        fg = C["success"]    if active else C["danger"]
        ctk.CTkLabel(row, text="Active" if active else "Inactive", width=80, height=26,
                     corner_radius=13, fg_color=bg, text_color=fg,
                     font=ctk.CTkFont(family=FONT, size=11, weight="bold")).grid(
                     row=0, column=1, padx=10)
 
        # Created date
        ctk.CTkLabel(row, text=created, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=12)).grid(row=0, column=2, padx=10)
 
        # Actions
        acts = ctk.CTkFrame(row, fg_color="transparent")
        acts.grid(row=0, column=3, padx=(0, 14), pady=10)
        if active:
            self._secondary_button(acts, "Disable", lambda u=username: self.disable_user(u), width=80).grid(row=0, column=0, padx=(0, 6))
        self._danger_button(acts, "Delete", lambda u=username: self.permanently_delete_user(u), width=74).grid(row=0, column=1)
 
    def disable_user(self, username):
        if messagebox.askyesno("Confirm Disable", f"Disable user '{username}'?"):
            try:
                self.db.delete_user(username)
                self._show_top_status("User disabled", "warning")
                self.load_users()
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
 
    def permanently_delete_user(self, username):
        if messagebox.askyesno("Confirm Delete", f"Permanently delete '{username}'?\nThis cannot be undone."):
            try:
                self.db.permanently_delete_user(username)
                self._show_top_status("User deleted", "danger")
                self.load_users()
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
 
    def _empty_state(self, master, title, msg):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.grid(row=0, column=0, pady=40)
        ctk.CTkLabel(f, text=title, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=16, weight="bold")).grid(row=0, column=0, pady=(0, 6))
        ctk.CTkLabel(f, text=msg, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=13)).grid(row=1, column=0)
 
    # ── Enroll ─────────────────────────────────────────────────────────────────
    def show_enroll(self):
        self._set_active_nav("enroll")
        self._set_header("Enroll Face", "Create a new biometric profile using the camera enrollment flow.")
        self._clear_content()
 
        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.grid(row=0, column=0, padx=28, pady=16, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_columnconfigure(1, weight=1)
 
        # Form card
        form = self._card(wrapper, row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
 
        ctk.CTkLabel(form, text="New User Profile", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=20, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=24, pady=(26, 4), sticky="w")
        ctk.CTkLabel(form, text="Enter a username, then start camera enrollment.",
                     text_color=C["text_muted"], font=ctk.CTkFont(family=FONT, size=13), anchor="w").grid(
                     row=1, column=0, padx=24, pady=(0, 20), sticky="w")
 
        ctk.CTkLabel(form, text="Username", text_color=C["text_mid"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"), anchor="w").grid(
                     row=2, column=0, padx=24, sticky="w")
        self.entry_username = ctk.CTkEntry(form, placeholder_text="e.g. john.doe",
                                           height=44, corner_radius=10,
                                           fg_color=C["bg"], border_color=C["border"],
                                           text_color=C["text_dark"],
                                           placeholder_text_color=C["text_muted"],
                                           font=ctk.CTkFont(family=FONT, size=14))
        self.entry_username.grid(row=3, column=0, padx=24, pady=(8, 18), sticky="ew")
 
        self._primary_button(form, "▶  Start Camera Enrollment", self.start_enrollment, width=230).grid(
            row=4, column=0, padx=24, pady=(0, 14), sticky="w")
 
        ctk.CTkLabel(form, text="A camera window will open. Press C to capture samples, Q to quit.",
                     text_color=C["text_muted"], font=ctk.CTkFont(family=FONT, size=12),
                     wraplength=380, justify="left", anchor="w").grid(
                     row=5, column=0, padx=24, pady=(0, 28), sticky="w")
 
        # Checklist card
        steps_card = self._card(wrapper, row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        steps_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(steps_card, text="Enrollment Checklist", text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=20, weight="bold"), anchor="w").grid(
                     row=0, column=0, padx=24, pady=(26, 14), sticky="w")
 
        steps = [
            ("1", "Use clear lighting",         "Avoid strong shadows and backlight."),
            ("2", "Look at the camera",          "Keep your face centered in the frame."),
            ("3", "Capture multiple samples",    "Press C several times for better accuracy."),
            ("4", "Refresh users after enroll",  "Open Manage Users and press Refresh."),
        ]
        for i, (num, title, body) in enumerate(steps):
            item = ctk.CTkFrame(steps_card, fg_color=C["card2"], corner_radius=12)
            item.grid(row=i + 1, column=0, padx=24, pady=6, sticky="ew")
            item.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(item, text=num, width=34, height=34, corner_radius=17,
                         fg_color=C["green_btn"], text_color=C["white"],
                         font=ctk.CTkFont(family=FONT, size=13, weight="bold")).grid(
                         row=0, column=0, rowspan=2, padx=14, pady=14)
            ctk.CTkLabel(item, text=title, text_color=C["text_dark"],
                         font=ctk.CTkFont(family=FONT, size=13, weight="bold"), anchor="w").grid(
                         row=0, column=1, padx=(0, 14), pady=(13, 0), sticky="w")
            ctk.CTkLabel(item, text=body, text_color=C["text_muted"],
                         font=ctk.CTkFont(family=FONT, size=12), anchor="w").grid(
                         row=1, column=1, padx=(0, 14), pady=(0, 13), sticky="w")
 
        ctk.CTkFrame(steps_card, height=1, fg_color="transparent").grid(row=10, column=0, pady=10)
 
    def start_enrollment(self):
        username = self.entry_username.get().strip()
        if not username:
            messagebox.showerror("Missing Username", "Please enter a username."); return
        if not all(ch.isalnum() or ch in "._-" for ch in username):
            messagebox.showerror("Invalid Username", "Use only letters, numbers, dots, underscores, or hyphens."); return
        if DEMO_MODE:
            messagebox.showinfo("Demo Mode", f"Demo: enrollment for '{username}' would start here.\n\nPress C to capture, Q to quit.")
            self.entry_username.delete(0, "end")
            self._show_top_status("Enrollment started (demo)", "success"); return
        try:
            subprocess.Popen([sys.executable, "-m", "facelook.enroll_camera", username],
                             cwd=str(Path(__file__).parent))
            messagebox.showinfo("Enrollment Started",
                                f"Camera enrollment started for '{username}'.\n\nPress C to capture samples and Q to quit.")
            self.entry_username.delete(0, "end")
            self._show_top_status("Enrollment started", "success")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self._show_top_status("Enroll failed", "danger")
 
    # ── Logs ───────────────────────────────────────────────────────────────────
    def show_logs(self):
        self._set_active_nav("logs")
        self._set_header("Authentication Logs", "Review the latest authentication attempts and results.")
        self._clear_content()
 
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=28, pady=(16, 8), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)
 
        search = ctk.CTkEntry(toolbar, textvariable=self.log_search_var,
                              placeholder_text="Search username, result, reason…",
                              height=40, corner_radius=10,
                              fg_color=C["card"], border_color=C["border"],
                              text_color=C["text_dark"],
                              placeholder_text_color=C["text_muted"],
                              font=ctk.CTkFont(family=FONT, size=13))
        search.grid(row=0, column=0, sticky="ew", padx=(0, 10))
 
        ctk.CTkOptionMenu(toolbar, variable=self.log_filter_var,
                          values=["All", "AUTH_OK", "Failed"],
                          width=130, height=40, corner_radius=10,
                          fg_color=C["card"], button_color=C["green_btn"],
                          button_hover_color=C["green_hover"],
                          dropdown_fg_color=C["card"],
                          dropdown_hover_color=C["green_pale"],
                          text_color=C["text_dark"],
                          font=ctk.CTkFont(family=FONT, size=13),
                          command=lambda _: self.load_logs()).grid(row=0, column=1, padx=(0, 10))
 
        self._secondary_button(toolbar, "Refresh", self.load_logs, width=100).grid(row=0, column=2)
 
        log_card = self._card(self.content, row=1, column=0, padx=28, pady=(4, 28), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
 
        hdr = ctk.CTkFrame(log_card, fg_color=C["card2"], corner_radius=10)
        hdr.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="ew")
        for ci, lbl in enumerate(["User", "Result", "Time", "Reason", "Confidence"]):
            ctk.CTkLabel(hdr, text=lbl, text_color=C["text_muted"],
                         font=ctk.CTkFont(family=FONT, size=11, weight="bold"), anchor="w").grid(
                         row=0, column=ci, padx=14, pady=10, sticky="w")
        hdr.grid_columnconfigure(0, weight=1)
 
        self.logs_scroll = ctk.CTkScrollableFrame(log_card, fg_color="transparent", height=420)
        self.logs_scroll.grid(row=1, column=0, padx=10, pady=(0, 14), sticky="nsew")
        self.logs_scroll.grid_columnconfigure(0, weight=1)
 
        self.log_search_var.trace_add("write", lambda *_: self.load_logs())
        self.load_logs()
 
    def load_logs(self):
        if not hasattr(self, "logs_scroll"): return
        for w in self.logs_scroll.winfo_children(): w.destroy()
        try: logs = self.db.list_auth_logs(limit=50)
        except Exception as exc:
            self._empty_state(self.logs_scroll, "Could not load logs", str(exc)); return
 
        q      = self.log_search_var.get().strip().lower()
        filt   = self.log_filter_var.get()
        filtered = []
        for log in logs:
            res = str(log.get("result", ""))
            if filt == "AUTH_OK" and res != "AUTH_OK": continue
            if filt == "Failed"  and res == "AUTH_OK":  continue
            hay = " ".join(str(log.get(k, "")) for k in ("username", "result", "reason", "confidence")).lower()
            if q and q not in hay: continue
            filtered.append(log)
 
        if not filtered:
            self._empty_state(self.logs_scroll, "No logs found",
                              "Try refreshing or changing the search/filter."); return
        for i, log in enumerate(filtered):
            self._log_row(i, log)
 
    def _log_row(self, idx, log):
        result   = str(log.get("result", "Unknown"))
        username = str(log.get("username") or "Unknown")
        reason   = str(log.get("reason")   or "-")
        conf     = str(log.get("confidence") or "-")
        ts       = str(log.get("created_at", ""))[:19].replace("T", " ") or "Unknown"
        ok       = result == "AUTH_OK"
 
        row = ctk.CTkFrame(self.logs_scroll,
                           fg_color=C["card2"] if idx % 2 == 0 else C["card"],
                           corner_radius=12)
        row.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
        row.grid_columnconfigure(0, weight=1)
 
        # Avatar + username
        av_f = ctk.CTkFrame(row, fg_color="transparent")
        av_f.grid(row=0, column=0, padx=14, pady=12, sticky="w")
        ctk.CTkLabel(av_f, text=username[0].upper(), width=34, height=34, corner_radius=17,
                     fg_color=C["green_pale"], text_color=C["green"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold")).grid(row=0, column=0)
        ctk.CTkLabel(av_f, text=username, text_color=C["text_dark"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"), anchor="w").grid(
                     row=0, column=1, padx=(10, 0))
 
        # Result badge
        rbg = C["success_bg"] if ok else C["danger_bg"]
        rfg = C["success"]    if ok else C["danger"]
        ctk.CTkLabel(row, text=result, width=100, height=26, corner_radius=13,
                     fg_color=rbg, text_color=rfg,
                     font=ctk.CTkFont(family=FONT, size=11, weight="bold")).grid(row=0, column=1, padx=6)
 
        ctk.CTkLabel(row, text=ts, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11)).grid(row=0, column=2, padx=10)
        ctk.CTkLabel(row, text=reason, text_color=C["text_muted"],
                     font=ctk.CTkFont(family=FONT, size=11)).grid(row=0, column=3, padx=10)
        ctk.CTkLabel(row, text=conf, text_color=C["text_mid"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold")).grid(row=0, column=4, padx=(0, 14))
 

    # ── Help ───────────────────────────────────────────────────────────────────
    def show_help(self):
        self._set_active_nav("help")
        self._set_header("Help", "A simple and friendly guide to use FaceLook.")
        self._clear_content()

        wrapper = ctk.CTkFrame(self.content, fg_color="transparent")
        wrapper.grid(row=0, column=0, padx=28, pady=(16, 28), sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_columnconfigure(1, weight=1)

        # Cute welcome card
        hero = self._dark_card(wrapper, row=0, column=0, columnspan=2, padx=0, pady=(0, 12), sticky="ew")
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hero,
            text="Welcome to FaceLook Help ♡",
            text_color=C["white"],
            font=ctk.CTkFont(family=FONT, size=24, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=26, pady=(24, 4), sticky="w")

        ctk.CTkLabel(
            hero,
            text="Everything you need is simple: enroll a face, start the service, and check the logs.",
            text_color=C["green_light"],
            font=ctk.CTkFont(family=FONT, size=13),
            anchor="w",
            wraplength=720,
            justify="left",
        ).grid(row=1, column=0, padx=26, pady=(0, 16), sticky="w")

        hero_actions = ctk.CTkFrame(hero, fg_color="transparent")
        hero_actions.grid(row=2, column=0, padx=26, pady=(0, 24), sticky="w")

        ctk.CTkButton(
            hero_actions,
            text="+ Enroll User",
            width=120,
            height=36,
            corner_radius=18,
            fg_color=C["green_accent"],
            hover_color=C["green_mid"],
            text_color=C["white"],
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
            command=self.show_enroll,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            hero_actions,
            text="Start Service",
            width=120,
            height=36,
            corner_radius=18,
            fg_color=C["white"],
            hover_color=C["green_pale"],
            text_color=C["green_btn"],
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
            command=self.start_service,
        ).grid(row=0, column=1)

        # Four small cute help cards
        self._help_card(
            wrapper,
            row=1,
            column=0,
            icon="1",
            title="Enroll a new user",
            body="Open Enroll Face, type a username, then start the camera enrollment. Press C to capture samples and Q to quit.",
        )

        self._help_card(
            wrapper,
            row=1,
            column=1,
            icon="2",
            title="Start authentication",
            body="Go to Dashboard and click Start. When the service is running, FaceLook can check faces using the camera.",
        )

        self._help_card(
            wrapper,
            row=2,
            column=0,
            icon="3",
            title="Manage users",
            body="Open Manage Users to search profiles, disable a user, or delete a profile when you no longer need it.",
        )

        self._help_card(
            wrapper,
            row=2,
            column=1,
            icon="4",
            title="Camera not opening?",
            body="Check that your camera is connected, close apps using the camera, then restart the FaceLook service.",
        )

        about = self._card(wrapper, row=3, column=0, columnspan=2, padx=0, pady=(12, 0), sticky="ew")
        about.grid_columnconfigure(1, weight=1)

        mode = "Demo Mode" if DEMO_MODE else "Production Mode"
        db_text = "Demo database" if DEMO_MODE else str(FaceLookConfig.DATABASE_PATH)

        ctk.CTkLabel(
            about,
            text="♡",
            width=42,
            height=42,
            corner_radius=21,
            fg_color=C["green_pale"],
            text_color=C["green"],
            font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=20, pady=18)

        ctk.CTkLabel(
            about,
            text="About FaceLook",
            text_color=C["text_dark"],
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 20), pady=(18, 2), sticky="w")

        ctk.CTkLabel(
            about,
            text=f"FaceLook Administration v1.0  ·  {mode}  ·  Database: {db_text}",
            text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=12),
            anchor="w",
            wraplength=850,
            justify="left",
        ).grid(row=1, column=1, padx=(0, 20), pady=(0, 18), sticky="w")

    def _help_card(self, master, row, column, icon, title, body):
        card = self._card(master, row=row, column=column,
                          padx=(0, 8) if column == 0 else (8, 0),
                          pady=8, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text=icon,
            width=38,
            height=38,
            corner_radius=19,
            fg_color=C["green_pale"],
            text_color=C["green"],
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=18, pady=18)

        ctk.CTkLabel(
            card,
            text=title,
            text_color=C["text_dark"],
            font=ctk.CTkFont(family=FONT, size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 18), pady=(18, 3), sticky="w")

        ctk.CTkLabel(
            card,
            text=body,
            text_color=C["text_muted"],
            font=ctk.CTkFont(family=FONT, size=12),
            anchor="w",
            justify="left",
            wraplength=380,
        ).grid(row=1, column=1, padx=(0, 18), pady=(0, 18), sticky="w")

    # ── Close ──────────────────────────────────────────────────────────────────
    def on_close(self):
        if self.is_service_running():
            if not messagebox.askyesno("Close FaceLook",
                                       "The service is still running. Stop it and close?"):
                return
            self.stop_service(silent=True)
        self.destroy()
 
    def _safe_stats(self):
        try: return self.db.stats()
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return {"total_users": 0, "active_users": 0, "total_auth_logs": 0}
 
 
if __name__ == "__main__":
    app = FaceLookGUI()
    app.mainloop()