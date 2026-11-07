"""
Bulk Video Editor & Remixer GUI
Optimized for Facebook, Instagram Reels, YouTube Shorts, and TikTok.
"""

import os
import sys
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from editor_engine import (
    SUPPORTED_EXTENSIONS,
    check_ffmpeg,
    get_video_info,
    process_single_video,
    generate_layout_preview,
    is_video_file,
    format_duration,
    format_size,
    sanitize_filename
)
from PIL import Image, ImageTk

class BulkVideoEditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bulk Video Editor & Remixer | Facebook & Instagram Reels Optimizer")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1160, max(960, int(screen_w * 0.92)))
        win_h = min(820, max(650, int(screen_h * 0.88)))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(900, 550)
        try:
            self.root.state('zoomed')
        except Exception:
            pass

        # Output folder variable
        # Cross-platform default output folder (Google Drive / Windows / Linux)
        gdrive_dir = os.path.expanduser("~/GoogleDrive/Edited_Videos")
        if os.path.exists(os.path.expanduser("~/GoogleDrive")):
            default_out = gdrive_dir
        elif sys.platform.startswith("win") and os.path.exists("D:\\"):
            default_out = os.path.join("D:\\", "Edited_Videos")
        else:
            default_out = os.path.expanduser("~/Edited_Videos")
        self.output_dir_var = tk.StringVar(value=default_out)
        self.output_prefix_var = tk.StringVar(value="reels_")
        self.output_suffix_var = tk.StringVar(value="")

        # Preset variable
        self.preset_var = tk.StringVar(value="meta_reels")

        # Visual settings variables
        self.speed_var = tk.StringVar(value="1.03")
        self.zoom_var = tk.StringVar(value="3")
        self.flip_h_var = tk.BooleanVar(value=False)
        self.aspect_mode_var = tk.StringVar(value="9:16 Reels Blur (95% Video + Border Canvas)")
        self.color_grade_var = tk.BooleanVar(value=True)
        self.vignette_var = tk.BooleanVar(value=False)
        self.border_var = tk.StringVar(value="none")
        self.custom_bg_path_var = tk.StringVar(value="")
        self.enable_box_frame_var = tk.BooleanVar(value=False)
        self.bg_video_pos_var = tk.StringVar(value="center (ঠিক মাঝখানে)")
        self.bg_video_pos_x_var = tk.StringVar(value="Center (মাঝখানে)")
        self.box_scale_var = tk.StringVar(value="60% (ছবির মতো - ডানপাশের জন্য পারফেক্ট)")
        self.box_height_scale_var = tk.StringVar(value="85% (ছবির মতো - লম্বা ফ্রেম)")
        self.box_fit_mode_var = tk.StringVar(value="Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
        self.box_border_color_var = tk.StringVar(value="None (বর্ডার ছাড়া - ছবির মতো)")
        self.box_border_width_var = tk.StringVar(value="0px (বর্ডার ছাড়া)")
        self.box_custom_x_var = tk.StringVar(value="")
        self.box_custom_y_var = tk.StringVar(value="")
        self.box_crop_y_pct_var = tk.IntVar(value=15)
        self.box_crop_x_pct_var = tk.IntVar(value=50)
        self.bg_template_mute_var = tk.BooleanVar(value=True)

        # Top/Bottom Split variables (Reaction Meme split like in user screenshot)
        self.enable_split_var = tk.BooleanVar(value=False)
        self.split_meme_path_var = tk.StringVar(value="")
        self.split_layout_var = tk.StringVar(value="Top Video + Bottom Meme (উপরে ভিডিও + নিচে মেম - ছবির মতো)")
        self.split_bg_style_var = tk.StringVar(value="Black (কালো - ছবির মতো)")
        self.split_video_h_var = tk.StringVar(value="50% (স্ট্যান্ডার্ড)")
        self.split_meme_h_var = tk.StringVar(value="40% (ছবির মতো - Jim Carrey মেম সাইজ)")
        self.split_box_w_var = tk.StringVar(value="96% (ছবির মতো সাইড মার্জিন)")
        self.split_video_fit_var = tk.StringVar(value="Fit (অরিজিনাল সাইজ - নো ক্রপ)")
        self.split_crop_align_var = tk.StringVar(value="Top Focus (ওপর ঠিক রেখে নিচ থেকে কাটবে - ফেস ফোকাস)")
        self.split_crop_y_pct_var = tk.IntVar(value=15)
        self.crop_top_pct_var = tk.DoubleVar(value=0.0)
        self.crop_bot_pct_var = tk.DoubleVar(value=0.0)
        self.crop_left_pct_var = tk.DoubleVar(value=0.0)
        self.crop_right_pct_var = tk.DoubleVar(value=0.0)
        self.split_custom_bg_var = tk.StringVar(value="")
        self.split_border_color_var = tk.StringVar(value="White (সাদা - ছবির মতো)")
        self.split_border_width_var = tk.StringVar(value="6px (রিলস স্ট্যান্ডার্ড)")
        self.split_border_target_var = tk.StringVar(value="Video Only (শুধু মূল ভিডিওতে)")
        self.split_audio_source_var = tk.StringVar(value="Reel Sound (মূল রিল সাউন্ড - ডিফল্ট)")

        # Audio settings variables
        self.volume_var = tk.StringVar(value="1.15")
        self.anti_audio_hash_var = tk.BooleanVar(value=True)
        self.bgm_path_var = tk.StringVar(value="")
        self.bgm_volume_var = tk.StringVar(value="10")

        # Overlay settings variables
        self.text_overlay_var = tk.StringVar(value="")
        self.text_position_var = tk.StringVar(value="top")
        self.text_color_var = tk.StringVar(value="Yellow (হলুদ - ভাইরাল)")
        self.text_fontsize_var = tk.StringVar(value="54px (স্ট্যান্ডার্ড রিলস)")
        self.text_box_bg_var = tk.StringVar(value="Black Box (কালো বক্স)")
        self.text_custom_x_var = tk.StringVar(value="")
        self.text_custom_y_var = tk.StringVar(value="")
        self.split_custom_y_var = tk.StringVar(value="")
        self.watermark_path_var = tk.StringVar(value="")
        self.watermark_pos_var = tk.StringVar(value="top_right")

        # Quality & Performance variables
        self.crf_var = tk.StringVar(value="21")
        self.preset_speed_var = tk.StringVar(value="Fast (দ্রুত - রিকমেন্ডেড)")
        self.strip_meta_var = tk.BooleanVar(value=True)

        # Status & Stats
        self.overall_status_var = tk.StringVar(value="Ready. Add videos to start.")
        self.current_video_status_var = tk.StringVar(value="Idle")
        self.stats_var = tk.StringVar(value="Total Videos: 0 | Total Duration: 00:00")

        # Video queue and item storage
        self.videos = []
        self.is_processing = False
        self.cancel_requested = False
        self.log_queue = queue.Queue()

        self._setup_style()
        self._build_ui()
        self._apply_preset_values("meta_reels")
        self._check_ffmpeg_startup()
        self._poll_log_queue()

    def _setup_style(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.bg_color = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.primary_color = "#0d6efd"
        self.success_color = "#198754"
        self.danger_color = "#dc3545"
        self.text_color = "#212529"
        self.border_color = "#ced4da"

        self.root.configure(bg=self.bg_color)
        self.style.configure(".", background=self.bg_color, font=("Segoe UI", 9))
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 9))
        self.style.configure("Card.TFrame", background=self.card_bg, relief="solid", borderwidth=1)
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0f172a")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#64748b")
        self.style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"), foreground="#1e293b")
        
        # Treeview styling
        self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=26, background="#ffffff", fieldbackground="#ffffff")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), foreground="#334155")
        self.style.map("Treeview", background=[("selected", "#e0e7ff")], foreground=[("selected", "#1e1b4b")])

    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill="both", expand=True)

        # 1. Header Frame (Top)
        header_frame = ttk.Frame(main_container)
        header_frame.pack(side="top", fill="x", pady=(0, 6))

        title_lbl = ttk.Label(
            header_frame,
            text="🎬 Bulk Video Editor & Remixer",
            style="Header.TLabel"
        )
        title_lbl.pack(anchor="w")

        desc_lbl = ttk.Label(
            header_frame,
            text="Meta & Reels Anti-Duplicate Engine — ফেসবুক ও ইনস্টাগ্রাম রিলসের জন্য ইউনিক ফ্রেম, অডিও ও ক্যানভাস কনভার্টার",
            style="SubHeader.TLabel"
        )
        desc_lbl.pack(anchor="w")

        # 2. Preset Selection Banner (Top Card)
        preset_card = ttk.Frame(main_container, style="Card.TFrame", padding="8")
        preset_card.pack(side="top", fill="x", pady=(0, 6))

        p_row = ttk.Frame(preset_card, style="Card.TFrame")
        p_row.pack(fill="x")

        ttk.Label(
            p_row,
            text="⚡ Smart Presets (প্রিসেট বেছে নিন):",
            font=("Segoe UI", 10, "bold"),
            background=self.card_bg,
            foreground="#0f172a"
        ).pack(side="left", padx=(0, 8))

        presets = [
            ("🌟 Meta & Reels Anti-Duplicate (Recommended)", "meta_reels"),
            ("🌸 Pink Galaxy Hook Frame (ছবির মতো ব্যানার ও ফ্রেম)", "pink_galaxy_frame"),
            ("🎬 Top/Bottom Split (উপরে ভিডিও + নিচে মেম - ছবির মতো)", "top_bottom_split"),
            ("🎭 Side Meme Template (ডানপাশে ভিডিও / Pink Panther)", "custom_meme_template"),
            ("📱 9:16 Reels Blur (95% Video + Border)", "reels_95_blur"),
            ("🎬 Frame Box Template (ছবির মতো ফ্রেম ও ব্যাকগ্রাউন্ড)", "frame_box"),
            ("📱 9:16 Vertical Reel (100% Full Width Blur)", "vertical_9_16"),
            ("🪞 Heavy Remixer (Mirror + Speed + Grade)", "heavy_remix"),
            ("⚡ Fast Mode (Speed + Strip Meta)", "fast_mode"),
            ("🛠️ Custom / Manual Settings", "custom")
        ]

        preset_cb = ttk.Combobox(
            p_row,
            textvariable=self.preset_var,
            values=[p[1] for p in presets],
            state="readonly",
            width=36,
            font=("Segoe UI", 9, "bold")
        )
        preset_cb.pack(side="left", padx=5)

        # Human-friendly labels for presets
        preset_display = {
            "meta_reels": "🌟 Meta & Reels Anti-Duplicate (Recommended)",
            "pink_galaxy_frame": "🌸 Pink Galaxy Hook Frame (ছবির মতো ব্যানার ও ফ্রেম)",
            "top_bottom_split": "🎬 Top/Bottom Split (উপরে ভিডিও + নিচে মেম - ছবির মতো)",
            "custom_meme_template": "🎭 Side Meme Template (ডানপাশে ভিডিও / Pink Panther)",
            "reels_95_blur": "📱 9:16 Reels Blur (95% Video + Border)",
            "frame_box": "🎬 Frame Box Template (ছবির মতো ফ্রেম ও ব্যাকগ্রাউন্ড)",
            "vertical_9_16": "📱 9:16 Vertical Reel (100% Full Width Blur)",
            "heavy_remix": "🪞 Heavy Remixer (Mirror + Speed + Grade)",
            "fast_mode": "⚡ Fast Mode (Speed + Strip Meta)",
            "custom": "🛠️ Custom / Manual Settings"
        }
        self.preset_display_var = tk.StringVar(value=preset_display["meta_reels"])
        preset_cb.config(values=list(preset_display.values()))
        preset_cb.set(preset_display["meta_reels"])

        def on_preset_select(event):
            sel_text = preset_cb.get()
            for key, val in preset_display.items():
                if val == sel_text:
                    self.preset_var.set(key)
                    self._apply_preset_values(key)
                    break

        preset_cb.bind("<<ComboboxSelected>>", on_preset_select)

        self.preset_info_lbl = ttk.Label(
            p_row,
            text="1.03x Speed + 3% Zoom + 9:16 Blur Canvas + Color Grade + Audio EQ + Strip Meta",
            font=("Segoe UI", 8, "italic"),
            foreground="#475569",
            background=self.card_bg
        )
        self.preset_info_lbl.pack(side="left", padx=12)

        # --- DOCK BOTTOM AREA FIRST (Pinned to bottom: ALWAYS visible regardless of screen size) ---
        # 6. Live Log Box (Compact 2 lines at very bottom)
        log_frame = ttk.Frame(main_container)
        log_frame.pack(side="bottom", fill="x", pady=(2, 0))

        self.log_text = tk.Text(log_frame, height=2, bg="#1e293b", fg="#f8fafc", font=("Consolas", 8), wrap="word")
        self.log_text.pack(fill="x")
        self.log_text.insert("end", "[System] Bulk Video Editor & Remixer initialized.\n")
        self.log_text.configure(state="disabled")

        # 5. Bottom Controls & Progress Card (Pinned directly above Log Box)
        bottom_card = ttk.Frame(main_container, style="Card.TFrame", padding="8")
        bottom_card.pack(side="bottom", fill="x", pady=(4, 2))

        # Progress bars row
        prog_row = ttk.Frame(bottom_card, style="Card.TFrame")
        prog_row.pack(fill="x", pady=(0, 4))

        # Current item progress
        c_prog_frame = ttk.Frame(prog_row, style="Card.TFrame")
        c_prog_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Label(c_prog_frame, textvariable=self.current_video_status_var, font=("Segoe UI", 8), background=self.card_bg).pack(anchor="w")
        self.current_prog_bar = ttk.Progressbar(c_prog_frame, orient="horizontal", mode="determinate")
        self.current_prog_bar.pack(fill="x", pady=1)

        # Overall progress
        o_prog_frame = ttk.Frame(prog_row, style="Card.TFrame")
        o_prog_frame.pack(side="left", fill="x", expand=True)

        ttk.Label(o_prog_frame, textvariable=self.overall_status_var, font=("Segoe UI", 8), background=self.card_bg).pack(anchor="w")
        self.overall_prog_bar = ttk.Progressbar(o_prog_frame, orient="horizontal", mode="determinate")
        self.overall_prog_bar.pack(fill="x", pady=1)

        # Execution Buttons Row (Prominent Start Button)
        btn_row = ttk.Frame(bottom_card, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(2, 0))

        self.btn_start = tk.Button(
            btn_row,
            text="🚀 Start Bulk Editing (এডিটিং শুরু করুন)",
            command=self._start_processing,
            bg="#0d6efd",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2"
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_cancel = tk.Button(
            btn_row,
            text="⏹️ Cancel",
            command=self._cancel_processing,
            bg="#dc3545",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=5,
            state="disabled",
            cursor="hand2"
        )
        self.btn_cancel.pack(side="left", padx=(0, 10))

        btn_open_out = tk.Button(
            btn_row,
            text="📂 Open Output Folder",
            command=self._open_output_folder,
            bg="#e2e8f0",
            fg="#1e293b",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2"
        )
        btn_open_out.pack(side="left")

        # 3. Settings Notebook (Tabs) (Top)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(side="top", fill="x", pady=(0, 6))

        tab_visual = ttk.Frame(self.notebook, padding="10")
        self.tab_template = ttk.Frame(self.notebook, padding="10")
        tab_audio = ttk.Frame(self.notebook, padding="10")
        tab_branding = ttk.Frame(self.notebook, padding="10")
        tab_output = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(tab_visual, text="  🎥 Video & Visuals  ")
        self.notebook.add(self.tab_template, text="  🖼️ Custom Template (কাস্টম ফ্রেম)  ")
        self.notebook.add(tab_audio, text="  🎵 Audio & BGM  ")
        self.notebook.add(tab_branding, text="  🏷️ Hook & Watermark  ")
        self.notebook.add(tab_output, text="  ⚙️ Output & Quality  ")

        self._build_tab_visual(tab_visual)
        self._build_tab_template(self.tab_template)
        self._build_tab_audio(tab_audio)
        self._build_tab_branding(tab_branding)
        self._build_tab_output(tab_output)

        # 4. Middle Section: Video Queue (Treeview) - Fills remaining space in center!
        queue_card = ttk.Frame(main_container, style="Card.TFrame", padding="8")
        queue_card.pack(side="top", fill="both", expand=True, pady=(0, 4))

        # Action toolbar for Queue (also includes a TOP Start Button for instant visibility!)
        tb_frame = ttk.Frame(queue_card, style="Card.TFrame")
        tb_frame.pack(fill="x", pady=(0, 6))

        btn_add_files = ttk.Button(tb_frame, text="➕ Add Videos", command=self._add_files)
        btn_add_files.pack(side="left", padx=(0, 5))

        btn_add_folder = ttk.Button(tb_frame, text="📁 Add Folder", command=self._add_folder)
        btn_add_folder.pack(side="left", padx=5)

        self.btn_start_top = tk.Button(
            tb_frame,
            text="🚀 Start Bulk Editing",
            command=self._start_processing,
            bg="#16a34a",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=3,
            cursor="hand2"
        )
        self.btn_start_top.pack(side="left", padx=(10, 5))

        btn_remove = ttk.Button(tb_frame, text="🗑️ Remove Selected", command=self._remove_selected)
        btn_remove.pack(side="left", padx=5)

        btn_clear = ttk.Button(tb_frame, text="🧹 Clear All", command=self._clear_all)
        btn_clear.pack(side="left", padx=5)

        stats_lbl = ttk.Label(tb_frame, textvariable=self.stats_var, font=("Segoe UI", 9, "bold"), foreground="#0284c7", background=self.card_bg)
        stats_lbl.pack(side="right", padx=10)

        # Treeview table
        tree_frame = ttk.Frame(queue_card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)

        columns = ("idx", "name", "resolution", "fps", "duration", "status", "size")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended", height=6)

        self.tree.heading("idx", text="#")
        self.tree.heading("name", text="Video Name")
        self.tree.heading("resolution", text="Resolution")
        self.tree.heading("fps", text="FPS")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("status", text="Status / Progress")
        self.tree.heading("size", text="Output Size")

        self.tree.column("idx", width=40, anchor="center")
        self.tree.column("name", width=380, anchor="w")
        self.tree.column("resolution", width=95, anchor="center")
        self.tree.column("fps", width=65, anchor="center")
        self.tree.column("duration", width=80, anchor="center")
        self.tree.column("status", width=180, anchor="w")
        self.tree.column("size", width=95, anchor="center")

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    # --- TAB BUILDERS ---

    def _build_tab_visual(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True)

        # Row 0: Speed & Zoom
        ttk.Label(grid, text="Speed Factor:").grid(row=0, column=0, sticky="w", pady=6)
        speed_cb = ttk.Combobox(
            grid,
            textvariable=self.speed_var,
            values=["1.00 (Normal)", "1.02 (Micro)", "1.03 (Reels Rec)", "1.05 (Standard)", "1.08", "1.10"],
            width=16,
            state="readonly"
        )
        speed_cb.grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Smart Zoom / Crop:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        zoom_cb = ttk.Combobox(
            grid,
            textvariable=self.zoom_var,
            values=["0% (None)", "2% (Micro)", "3% (Recommended)", "5% (Medium)", "8% (Strong)"],
            width=18,
            state="readonly"
        )
        zoom_cb.grid(row=0, column=3, sticky="w", padx=8)

        # Row 1: Aspect Ratio & Border
        ttk.Label(grid, text="Aspect Ratio / Canvas:").grid(row=1, column=0, sticky="w", pady=6)
        aspect_cb = ttk.Combobox(
            grid,
            textvariable=self.aspect_mode_var,
            values=[
                "9:16 Reels Blur (95% Video + Border Canvas)",
                "9:16 Vertical (Blur Canvas - 100% Full Width)",
                "9:16 Vertical (Center Crop)",
                "1:1 Square (Blur Canvas)",
                "16:9 Landscape (Blur Canvas)",
                "Keep Original"
            ],
            width=28,
            state="readonly"
        )
        aspect_cb.grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Border Style:").grid(row=1, column=2, sticky="w", padx=(20, 0))
        border_cb = ttk.Combobox(
            grid,
            textvariable=self.border_var,
            values=["None", "White (3px)", "Black (3px)", "Gold (3px)", "White (5px)", "Gold (5px)"],
            width=18,
            state="readonly"
        )
        border_cb.grid(row=1, column=3, sticky="w", padx=8)

        # Row 2: Checkboxes (Flip, Color, Vignette)
        chk_frame = ttk.Frame(grid)
        chk_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

        ttk.Checkbutton(chk_frame, text="Flip Horizontal (Mirror Mode)", variable=self.flip_h_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(chk_frame, text="Vibrant Color Grade (+Sat/+Contrast)", variable=self.color_grade_var).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(chk_frame, text="Cinematic Vignette (Edge Shade)", variable=self.vignette_var).pack(side="left")

        # Row 3: Custom Background Image (Canva / Custom Template)
        bg_sep = ttk.Separator(grid, orient="horizontal")
        bg_sep.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 6))

        bg_label_frame = ttk.Frame(grid)
        bg_label_frame.grid(row=4, column=0, columnspan=4, sticky="w", pady=(2, 4))

        ttk.Label(
            bg_label_frame,
            text="🖼️ Custom Background Image (নিজের ব্যাকগ্রাউন্ড ছবি/টেমপ্লেট):",
            font=("Segoe UI", 9, "bold"),
            foreground="#0f172a"
        ).pack(side="left")

        ttk.Label(
            bg_label_frame,
            text="(ঐচ্ছিক — Canva বা ফটোশপে তৈরি ৯:১৬ টেমপ্লেট ছবি সিলেক্ট করুন)",
            font=("Segoe UI", 8, "italic"),
            foreground="#64748b"
        ).pack(side="left", padx=8)

        # Row 5: Custom BG Input Controls
        bg_ctrl_frame = ttk.Frame(grid)
        bg_ctrl_frame.grid(row=5, column=0, columnspan=4, sticky="we", pady=(2, 6))

        ttk.Entry(bg_ctrl_frame, textvariable=self.custom_bg_path_var, width=54).pack(side="left", padx=(0, 6))
        ttk.Button(bg_ctrl_frame, text="Browse Image...", command=self._browse_custom_bg).pack(side="left", padx=(0, 6))
        ttk.Button(bg_ctrl_frame, text="Clear", width=6, command=lambda: self.custom_bg_path_var.set("")).pack(side="left")

        # Row 6: Box Frame Styling Header (ON / OFF Toggle)
        box_sep = ttk.Separator(grid, orient="horizontal")
        box_sep.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(10, 6))

        box_label_frame = ttk.Frame(grid)
        box_label_frame.grid(row=7, column=0, columnspan=4, sticky="w", pady=(2, 4))

        self.chk_box_frame = ttk.Checkbutton(
            box_label_frame,
            text="📦 Enable Video Box & Frame Style (ফ্রেম বক্স ও বর্ডার স্টাইল চালু / বন্ধ):",
            variable=self.enable_box_frame_var,
            command=self._on_box_frame_toggle
        )
        self.chk_box_frame.pack(side="left")

        self.box_status_lbl = ttk.Label(
            box_label_frame,
            text="[ বন্ধ (OFF) ]",
            font=("Segoe UI", 8, "bold"),
            foreground="#64748b"
        )
        self.box_status_lbl.pack(side="left", padx=6)

        btn_box_drag = tk.Button(
            box_label_frame,
            text="🖐️ ড্র্যাগ & ড্রপ স্টুডিও (বক্স সাইজ ও পজিশন)",
            command=self._open_box_drag_studio,
            bg="#6366f1",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_box_drag.pack(side="left", padx=(6, 0))

        btn_crop_studio = tk.Button(
            box_label_frame,
            text="✂️ ম্যানুয়াল ভিডিও ক্রপ (ভিডিওর চারপাশ থেকে কাটুন)",
            command=self._open_video_crop_studio,
            bg="#0284c7",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_crop_studio.pack(side="left", padx=(6, 0))

        # Row 8: Box Width & Fit Style
        ttk.Label(grid, text="Box Size / Width:").grid(row=8, column=0, sticky="w", pady=4)
        self.box_scale_cb = ttk.Combobox(
            grid,
            textvariable=self.box_scale_var,
            values=[
                "75% (ছবির মতো - পিংক গ্যালাক্সি)",
                "82% (ছবির মতো - Recommended)",
                "95% (রিলস ৯৫% ভিডিও - ৫% বর্ডার)",
                "75% (Compact Frame)",
                "80%",
                "85% (Standard)",
                "90% (Wide Frame)",
                "100% (Full Width - নো মার্জিন)"
            ],
            width=24,
            state="readonly"
        )
        self.box_scale_cb.grid(row=8, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Box Fit Style:").grid(row=8, column=2, sticky="w", padx=(15, 0))
        self.box_fit_cb = ttk.Combobox(
            grid,
            textvariable=self.box_fit_mode_var,
            values=[
                "Manual Custom Ratio (ম্যানুয়াল ক্রপ - নিজের ইচ্ছামতো সাইজ ও রেশিও)",
                "Manual Custom Fit (ম্যানুয়াল - বক্সের ভেতর পুরো ভিডিও ফিট)",
                "1:1 Square Box (Fit Full 9:16 Video - পুরো ভিডিও ফিট, নো ক্রপ)",
                "Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)",
                "Fit (ভিডিওর আসল রেশিও ঠিক রাখবে)",
                "Square 1:1 Box (ক্রপ করে চারকোনা)",
                "Portrait 4:5 Box",
                "Landscape 16:9 Box"
            ],
            width=30,
            state="readonly"
        )
        self.box_fit_cb.grid(row=8, column=3, sticky="w", padx=8)

        # Row 9: Manual Box Crop Cut Slider (বক্স কতটুকু কাটবে)
        ttk.Label(grid, text="Box Crop Position:").grid(row=9, column=0, sticky="w", pady=4)
        bcr_frame = ttk.Frame(grid)
        bcr_frame.grid(row=9, column=1, columnspan=3, sticky="w", padx=8, pady=4)

        lbl_bcr_show = ttk.Label(bcr_frame, text=f"{self.box_crop_y_pct_var.get()}% (ফেস ফোকাস)", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

        def on_main_box_crop(val):
            try:
                p = int(float(val))
                self.box_crop_y_pct_var.set(p)
                desc = "একদম ওপর" if p == 0 else ("ফেস ফোকাস" if p <= 25 else ("মাঝখান" if 40 <= p <= 60 else ("নিচ" if p >= 90 else "কাস্টম")))
                lbl_bcr_show.config(text=f"{p}% ({desc})")
            except Exception:
                pass

        ttk.Scale(bcr_frame, from_=0, to=100, orient="horizontal", variable=self.box_crop_y_pct_var, command=on_main_box_crop, length=180).pack(side="left", padx=(0, 6))
        lbl_bcr_show.pack(side="left", padx=(0, 10))

        def set_bcr_val(p):
            self.box_crop_y_pct_var.set(p)
            desc = "একদম ওপর" if p == 0 else ("ফেস ফোকাস" if p <= 25 else ("মাঝখান" if 40 <= p <= 60 else "নিচ"))
            lbl_bcr_show.config(text=f"{p}% ({desc})")

        tk.Button(bcr_frame, text="👤 Face Focus (15%)", command=lambda: set_bcr_val(15), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
        tk.Button(bcr_frame, text="🎯 Center (50%)", command=lambda: set_bcr_val(50), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
        tk.Button(bcr_frame, text="⬇️ Bottom (85%)", command=lambda: set_bcr_val(85), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left")

        # Row 10: Frame Border Color & Width
        ttk.Label(grid, text="Frame Border Color:").grid(row=10, column=0, sticky="w", pady=4)
        self.box_bcol_cb = ttk.Combobox(
            grid,
            textvariable=self.box_border_color_var,
            values=[
                "White (সাদা - ছবির মতো)",
                "Gold (সোনালী)",
                "Black (কালো)",
                "Red (লাল)",
                "Cyan (আকাশি)",
                "None (বর্ডার নেই)"
            ],
            width=24,
            state="readonly"
        )
        self.box_bcol_cb.grid(row=10, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Border Thickness:").grid(row=10, column=2, sticky="w", padx=(15, 0))
        self.box_bw_cb = ttk.Combobox(
            grid,
            textvariable=self.box_border_width_var,
            values=[
                "6px (রিলস স্ট্যান্ডার্ড)",
                "8px (ছবির মতো)",
                "4px (পাতলা)",
                "12px (মোটা)",
                "16px (খুব মোটা)",
                "0px (বর্ডার ছাড়া)"
            ],
            width=24,
            state="readonly"
        )
        self.box_bw_cb.grid(row=10, column=3, sticky="w", padx=8)

        # Row 11: Box Vertical Position & Horizontal Side Position
        ttk.Label(grid, text="Box Vertical Position:").grid(row=11, column=0, sticky="w", pady=4)
        self.pos_y_cb = ttk.Combobox(
            grid,
            textvariable=self.bg_video_pos_var,
            values=[
                "center (ঠিক মাঝখানে)",
                "galaxy_hook (৬৪৮px - পিংক গ্যালাক্সি ফ্রেম)",
                "lower_center (৫৩% - ছবির মতো নিচে)",
                "upper_center (৩৮% - একটু উপরে)",
                "top (উপরে)",
                "bottom (নিচে)"
            ],
            width=24,
            state="readonly"
        )
        self.pos_y_cb.grid(row=11, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Box Horizontal (সাইড):").grid(row=11, column=2, sticky="w", padx=(15, 0))
        self.pos_x_cb = ttk.Combobox(
            grid,
            textvariable=self.bg_video_pos_x_var,
            values=[
                "Center (মাঝখানে)",
                "Right Side (ডানপাশে - ছবির মতো)",
                "Left Side (বামপাশে)"
            ],
            width=24,
            state="readonly"
        )
        self.pos_x_cb.grid(row=11, column=3, sticky="w", padx=8)

    def _on_box_frame_toggle(self):
        is_on = self.enable_box_frame_var.get()
        state = "readonly" if is_on else "disabled"
        if hasattr(self, 'box_scale_cb'):
            self.box_scale_cb.config(state=state)
            self.box_fit_cb.config(state=state)
            self.box_bcol_cb.config(state=state)
            self.box_bw_cb.config(state=state)
            self.pos_y_cb.config(state=state)
        if hasattr(self, 'pos_x_cb'):
            self.pos_x_cb.config(state=state)
        if hasattr(self, 'box_status_lbl'):
            if is_on:
                self.box_status_lbl.config(
                    text="[ চালু (ON) — ফ্রেম বক্স সক্রিয় ]",
                    foreground="#198754"
                )
            else:
                self.box_status_lbl.config(
                    text="[ বন্ধ (OFF) — সাধারণ ক্যানভাস মোড ]",
                    foreground="#64748b"
                )

    def _build_tab_template(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True)

        # Header banner inside tab
        h_frame = ttk.Frame(grid)
        h_frame.pack(fill="x", pady=(0, 4))

        ttk.Label(
            h_frame,
            text="🎭 Template & Meme Split Studio (মেম ও ভাইরাল রিলস টেমপ্লেট)",
            font=("Segoe UI", 10, "bold"),
            foreground="#0f172a"
        ).pack(anchor="w")

        # --- SECTION 1: TOP/BOTTOM SPLIT (LIKE SCREENSHOT) ---
        split_card = ttk.LabelFrame(grid, text=" 🎬 ১. Top/Bottom Split লেআউট (ছবির মতো উপরে ভিডিও + নিচে মেম রিঅ্যাকশন) ", padding="8")
        split_card.pack(fill="x", pady=(0, 6))

        # Checkbox to toggle split
        sp_top = ttk.Frame(split_card)
        sp_top.pack(fill="x", pady=(0, 4))

        def on_toggle_split():
            if self.enable_split_var.get():
                self.enable_box_frame_var.set(False)
                self._on_box_frame_toggle()

        ttk.Checkbutton(
            sp_top,
            text="✅ এই Top/Bottom Split মোড চালু করুন (উপরে ভিডিও + নিচে মেম)",
            variable=self.enable_split_var,
            command=on_toggle_split
        ).pack(side="left")

        # Quick Meme Buttons
        sample_jim = os.path.join(os.path.dirname(__file__), "templates", "sample_reaction_meme.png")
        def load_jim_meme():
            if os.path.exists(sample_jim):
                self.enable_split_var.set(True)
                self.enable_box_frame_var.set(False)
                self.split_meme_path_var.set(sample_jim)
                self.split_layout_var.set("Top Video + Bottom Meme (উপরে ভিডিও + নিচে মেম - ছবির মতো)")
                self.split_bg_style_var.set("Black (কালো - ছবির মতো)")
                self.split_video_h_var.set("50% (স্ট্যান্ডার্ড)")
                self.split_meme_h_var.set("40% (ছবির মতো - Jim Carrey মেম সাইজ)")
                self.split_box_w_var.set("96% (ছবির মতো সাইড মার্জিন)")
                self.split_video_fit_var.set("Fit (অরিজিনাল সাইজ - নো ক্রপ)")
                self.split_border_color_var.set("White (সাদা - ছবির মতো)")
                self.split_border_width_var.set("6px (রিলস স্ট্যান্ডার্ড)")
                self.split_border_target_var.set("Video Only (শুধু মূল ভিডিওতে)")
                self._log("⭐ Loaded Jim Carrey Ace Ventura reaction meme template!")
            else:
                messagebox.showinfo("Not Found", "Sample reaction meme not found.")

        btn_jim = tk.Button(
            sp_top,
            text="⭐ Jim Carrey মেম লোড করুন (ছবির মতো)",
            command=load_jim_meme,
            bg="#fef08a",
            fg="#854d0e",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_jim.pack(side="left", padx=10)

        # File browse row
        sp_row1 = ttk.Frame(split_card)
        sp_row1.pack(fill="x", pady=(2, 4))

        ttk.Label(sp_row1, text="রিঅ্যাকশন মেম (ছবি বা ভিডিও):").pack(side="left", padx=(0, 6))
        ttk.Entry(sp_row1, textvariable=self.split_meme_path_var, width=44).pack(side="left", padx=(0, 6))

        def browse_split_meme():
            file = filedialog.askopenfilename(
                title="Select Reaction Meme (Image or Video)",
                filetypes=[
                    ("All Supported (Image/Video)", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm *.gif"),
                    ("Images (*.png, *.jpg, *.webp)", "*.png *.jpg *.jpeg *.webp"),
                    ("Videos (*.mp4, *.mov, *.webm)", "*.mp4 *.mov *.webm"),
                    ("All Files", "*.*")
                ]
            )
            if file:
                self.split_meme_path_var.set(file)
                self.enable_split_var.set(True)
                self.enable_box_frame_var.set(False)
                self._log(f"Reaction meme selected: {os.path.basename(file)}")

        ttk.Button(sp_row1, text="📁 Browse Meme...", command=browse_split_meme).pack(side="left", padx=(0, 6))
        ttk.Button(sp_row1, text="🧹 Clear", width=6, command=lambda: self.split_meme_path_var.set("")).pack(side="left")

        # Custom Canvas Background Image row
        sp_row_bg = ttk.Frame(split_card)
        sp_row_bg.pack(fill="x", pady=(2, 4))

        ttk.Label(sp_row_bg, text="ক্যানভাস ব্যাকগ্রাউন্ড ছবি:").pack(side="left", padx=(0, 6))
        ttk.Entry(sp_row_bg, textvariable=self.split_custom_bg_var, width=44).pack(side="left", padx=(0, 6))

        def browse_split_bg():
            file = filedialog.askopenfilename(
                title="Select Custom Canvas Background Image",
                filetypes=[
                    ("All Supported (Image/Video)", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm"),
                    ("Images (*.png, *.jpg, *.webp)", "*.png *.jpg *.jpeg *.webp"),
                    ("Videos (*.mp4, *.mov, *.webm)", "*.mp4 *.mov *.webm"),
                    ("All Files", "*.*")
                ]
            )
            if file:
                self.split_custom_bg_var.set(file)
                self.split_bg_style_var.set("Custom Image (কাস্টম ছবি ব্যাকগ্রাউন্ড)")
                self._log(f"Custom canvas background selected: {os.path.basename(file)}")

        def clear_split_bg():
            self.split_custom_bg_var.set("")
            self.split_bg_style_var.set("Black (কালো - ছবির মতো)")

        ttk.Button(sp_row_bg, text="📁 Browse BG Image...", command=browse_split_bg).pack(side="left", padx=(0, 6))
        ttk.Button(sp_row_bg, text="🧹 Clear", width=6, command=clear_split_bg).pack(side="left")

        # Split controls grid
        sp_grid = ttk.Frame(split_card)
        sp_grid.pack(fill="x", pady=(2, 0))

        ttk.Label(sp_grid, text="লেআউট পজিশন:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_layout_var,
            values=[
                "Top Video + Bottom Meme (উপরে ভিডিও + নিচে মেম - ছবির মতো)",
                "Top Meme + Bottom Video (উপরে মেম + নিচে ভিডিও)",
                "50/50 Equal Split (আধাআধি স্ক্রিন)"
            ],
            width=36,
            state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(sp_grid, text="ক্যানভাস ব্যাকগ্রাউন্ড:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_bg_style_var,
            values=[
                "Black (কালো - ছবির মতো)",
                "Blur Canvas (ব্লার ক্যানভাস)",
                "Custom Image (কাস্টম ছবি ব্যাকগ্রাউন্ড)"
            ],
            width=22,
            state="readonly"
        ).grid(row=0, column=3, sticky="w", padx=6)

        # Row 1: Heights & Widths
        ttk.Label(sp_grid, text="ভিডিও উচ্চতা (Top):").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_video_h_var,
            values=["50% (স্ট্যান্ডার্ড)", "55%", "45%", "60%", "40%"],
            width=36,
            state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(sp_grid, text="মেম উচ্চতা (Bottom):").grid(row=1, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_meme_h_var,
            values=["40% (ছবির মতো - Jim Carrey মেম সাইজ)", "35%", "45%", "50%", "30%"],
            width=22,
            state="readonly"
        ).grid(row=1, column=3, sticky="w", padx=6)

        # Row 2: Video Fit & Crop Cut Alignment
        ttk.Label(sp_grid, text="ভিডিও সাইজ / ফিট:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_video_fit_var,
            values=[
                "Fit (অরিজিনাল সাইজ - নো ক্রপ)",
                "Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)",
                "Manual Crop (ম্যানুয়াল ক্রপ - স্লাইডার ও কাস্টম ফ্রেম)"
            ],
            width=36,
            state="readonly"
        ).grid(row=2, column=1, sticky="w", padx=6)

        ttk.Label(sp_grid, text="ক্রপ কাট পজিশন (Fill Box):").grid(row=2, column=2, sticky="w", padx=(12, 0))
        cb_sp_crop = ttk.Combobox(
            sp_grid,
            textvariable=self.split_crop_align_var,
            values=[
                "Top Focus (ওপর ঠিক রেখে নিচ থেকে কাটবে - ফেস ফোকাস)",
                "Center (মাঝখান থেকে ক্রপ - ওপর-নিচ সমান)",
                "Bottom Focus (নিচ ঠিক রেখে ওপর থেকে কাটবে)",
                "Manual Slider (ম্যানুয়াল স্লাইডার - কাস্টম পজিশন)"
            ],
            width=22,
            state="readonly"
        )
        cb_sp_crop.grid(row=2, column=3, sticky="w", padx=6)

        # Row 3: Manual Crop Framing Slider (0% - 100%)
        ttk.Label(sp_grid, text="✂️ ম্যানুয়াল ক্রপ পজিশন:").grid(row=3, column=0, sticky="w", pady=3)
        cr_frame = ttk.Frame(sp_grid)
        cr_frame.grid(row=3, column=1, columnspan=3, sticky="w", padx=6, pady=3)

        lbl_cr_val = ttk.Label(cr_frame, text=f"{self.split_crop_y_pct_var.get()}% (ফেস ফোকাস)", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

        def on_main_crop_slide(val):
            try:
                p = int(float(val))
                self.split_crop_y_pct_var.set(p)
                self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
                self.split_crop_align_var.set("Manual Slider (ম্যানুয়াল স্লাইডার - কাস্টম পজিশন)")
                desc = "একদম ওপর" if p == 0 else ("ফেস ফোকাস" if p <= 25 else ("মাঝখান" if 40 <= p <= 60 else ("একদম নিচ" if p >= 95 else "কাস্টম")))
                lbl_cr_val.config(text=f"{p}% ({desc})")
            except Exception:
                pass

        sc_crop = ttk.Scale(cr_frame, from_=0, to=100, orient="horizontal", variable=self.split_crop_y_pct_var, command=on_main_crop_slide, length=180)
        sc_crop.pack(side="left", padx=(0, 6))
        lbl_cr_val.pack(side="left", padx=(0, 10))

        def set_main_cr_preset(pct, name):
            self.split_crop_y_pct_var.set(pct)
            self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
            self.split_crop_align_var.set(name)
            desc = "একদম ওপর" if pct == 0 else ("ফেস ফোকাস" if pct <= 25 else ("মাঝখান" if 40 <= pct <= 60 else "নিচ"))
            lbl_cr_val.config(text=f"{pct}% ({desc})")

        tk.Button(cr_frame, text="👤 Face Focus (15%)", command=lambda: set_main_cr_preset(15, "Top Focus (ওপর ঠিক রেখে নিচ থেকে কাটবে - ফেস ফোকাস)"), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
        tk.Button(cr_frame, text="🎯 Center (50%)", command=lambda: set_main_cr_preset(50, "Center (মাঝখান থেকে ক্রপ - ওপর-নিচ সমান)"), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
        tk.Button(cr_frame, text="⬇️ Bottom (85%)", command=lambda: set_main_cr_preset(85, "Bottom Focus (নিচ ঠিক রেখে ওপর থেকে কাটবে)"), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left")

        # Row 4: Manual Margin Edge Trim (Top/Bottom/Left/Right %)
        ttk.Label(sp_grid, text="✂️ সাইড / এজ ট্রিম (%):").grid(row=4, column=0, sticky="w", pady=3)
        trim_frame = ttk.Frame(sp_grid)
        trim_frame.grid(row=4, column=1, columnspan=3, sticky="w", padx=6, pady=3)

        ttk.Label(trim_frame, text="ওপর:").pack(side="left")
        ttk.Spinbox(trim_frame, from_=0, to=40, textvariable=self.crop_top_pct_var, width=4).pack(side="left", padx=(2, 8))
        ttk.Label(trim_frame, text="নিচ:").pack(side="left")
        ttk.Spinbox(trim_frame, from_=0, to=40, textvariable=self.crop_bot_pct_var, width=4).pack(side="left", padx=(2, 8))
        ttk.Label(trim_frame, text="বাম:").pack(side="left")
        ttk.Spinbox(trim_frame, from_=0, to=40, textvariable=self.crop_left_pct_var, width=4).pack(side="left", padx=(2, 8))
        ttk.Label(trim_frame, text="ডান:").pack(side="left")
        ttk.Spinbox(trim_frame, from_=0, to=40, textvariable=self.crop_right_pct_var, width=4).pack(side="left", padx=(2, 10))

        def reset_edge_trim():
            self.crop_top_pct_var.set(0.0)
            self.crop_bot_pct_var.set(0.0)
            self.crop_left_pct_var.set(0.0)
            self.crop_right_pct_var.set(0.0)

        ttk.Button(trim_frame, text="🧹 রিসেট ট্রিম", command=reset_edge_trim, width=11).pack(side="left")

        # Row 5: Border Color & Border Size
        ttk.Label(sp_grid, text="বর্ডার কালার:").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_border_color_var,
            values=[
                "White (সাদা - ছবির মতো)",
                "Gold (সোনালী)",
                "Black (কালো)",
                "Red (লাল)",
                "Cyan (আকাশি)",
                "None (বর্ডার ছাড়া)"
            ],
            width=36,
            state="readonly"
        ).grid(row=5, column=1, sticky="w", padx=6)

        ttk.Label(sp_grid, text="বর্ডার সাইজ / পুরুত্ব:").grid(row=5, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_border_width_var,
            values=[
                "6px (রিলস স্ট্যান্ডার্ড)",
                "8px (ছবির মতো)",
                "4px (পাতলা)",
                "12px (মোটা)",
                "0px (বর্ডার ছাড়া)"
            ],
            width=22,
            state="readonly"
        ).grid(row=5, column=3, sticky="w", padx=6)

        # Row 6: Border Target Placement & Audio Source
        ttk.Label(sp_grid, text="বর্ডার কোথায় বসবে:").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_border_target_var,
            values=[
                "Video Only (শুধু মূল ভিডিওতে)",
                "Both (ভিডিও ও মেম দুটোতেই)",
                "Between Split (মাঝের ডিভাইডার লাইন)"
            ],
            width=36,
            state="readonly"
        ).grid(row=6, column=1, sticky="w", padx=6)

        ttk.Label(sp_grid, text="সাউন্ড / অডিও সোর্স:").grid(row=6, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            sp_grid,
            textvariable=self.split_audio_source_var,
            values=[
                "Reel Sound (মূল রিল সাউন্ড - ডিফল্ট)",
                "Meme Sound (রিঅ্যাকশন মেম সাউন্ড)",
                "Mix Both (উভয় সাউন্ড মিক্স - রিল + মেম)",
                "Mute All (কোনো সাউন্ড থাকবে না - মিউট)"
            ],
            width=22,
            state="readonly"
        ).grid(row=6, column=3, sticky="w", padx=6)

        # Row 7: Hook Text in Empty Space (ভিডিওর ওপরের ফাঁকা জায়গার টেক্সট)
        ttk.Label(sp_grid, text="ভিডিওর ওপর ফাঁকা জায়গার টেক্সট:").grid(row=7, column=0, sticky="w", pady=4)
        hk_frame = ttk.Frame(sp_grid)
        hk_frame.grid(row=7, column=1, columnspan=3, sticky="w", padx=6, pady=4)

        ttk.Entry(hk_frame, textvariable=self.text_overlay_var, width=32).pack(side="left", padx=(0, 6))

        def set_hk(txt):
            self.text_overlay_var.set(txt)
            if not self.split_custom_y_var.get():
                self.split_custom_y_var.set("380")

        tk.Button(hk_frame, text="😱 WAIT FOR IT", command=lambda: set_hk("WAIT FOR IT 😱"), bg="#fef08a", fg="#854d0e", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=2)
        tk.Button(hk_frame, text="👇 WAIT TILL END", command=lambda: set_hk("WAIT TILL THE END 👇"), bg="#fed7aa", fg="#9a3412", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=2)
        tk.Button(hk_frame, text="🤣 শেষ পর্যন্ত দেখুন", command=lambda: set_hk("শেষ পর্যন্ত দেখুন 🤣🔥"), bg="#dcfce7", fg="#166534", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=2)
        ttk.Button(hk_frame, text="🧹 মুছুন", width=6, command=lambda: self.text_overlay_var.set("")).pack(side="left", padx=4)

        # Row 6: Text Styling & Drag Studio Button
        ttk.Label(sp_grid, text="টেক্সট কালার ও স্টাইল:").grid(row=8, column=0, sticky="w", pady=3)
        st_frame = ttk.Frame(sp_grid)
        st_frame.grid(row=8, column=1, columnspan=3, sticky="w", padx=6, pady=3)

        ttk.Combobox(
            st_frame,
            textvariable=self.text_color_var,
            values=[
                "Yellow (হলুদ - ভাইরাল)",
                "White (সাদা)",
                "Red (লাল)",
                "Cyan (আকাশি)",
                "Green (সবুজ)",
                "Black (কালো)"
            ],
            width=18,
            state="readonly"
        ).pack(side="left", padx=(0, 6))

        ttk.Combobox(
            st_frame,
            textvariable=self.text_fontsize_var,
            values=[
                "54px (স্ট্যান্ডার্ড রিলস)",
                "40px (ছোট)",
                "48px (মিডিয়াম)",
                "64px (বড়)",
                "76px (এক্সট্রা লার্জ)"
            ],
            width=16,
            state="readonly"
        ).pack(side="left", padx=(0, 6))

        ttk.Combobox(
            st_frame,
            textvariable=self.text_box_bg_var,
            values=[
                "Black Box (কালো বক্স)",
                "White Box (সাদা বক্স)",
                "Red Box (লাল বক্স)",
                "None (বক্স ছাড়া)"
            ],
            width=16,
            state="readonly"
        ).pack(side="left", padx=(0, 10))

        btn_drag_studio = tk.Button(
            st_frame,
            text="🖐️ ড্র্যাগ & ড্রপ স্টুডিও (লাইভ প্রিভিউ ও পজিশন)",
            command=self._open_drag_studio,
            bg="#6366f1",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2"
        )
        btn_drag_studio.pack(side="left")

        # --- SECTION 2: SIDE-BY-SIDE / CUSTOM TEMPLATE ---
        side_card = ttk.LabelFrame(grid, text=" 🖼️ ২. সাইড-বাই-সাইড কাস্টম ফ্রেম (Pink Panther স্টাইল) ", padding="8")
        side_card.pack(fill="x", pady=(0, 6))

        s_row = ttk.Frame(side_card)
        s_row.pack(fill="x", pady=(0, 3))

        sample_pink = os.path.join(os.path.dirname(__file__), "templates", "sample_meme_template.png")
        def load_pink():
            if os.path.exists(sample_pink):
                self.enable_split_var.set(False)
                self.enable_box_frame_var.set(True)
                self.custom_bg_path_var.set(sample_pink)
                self._apply_preset_values("custom_meme_template")
                self._log("⭐ Loaded Pink Panther side-by-side template!")

        ttk.Entry(s_row, textvariable=self.custom_bg_path_var, width=44).pack(side="left", padx=(0, 6))
        ttk.Button(s_row, text="📁 Browse Template...", command=self._browse_custom_bg).pack(side="left", padx=(0, 6))
        def load_galaxy():
            self._apply_preset_values("pink_galaxy_frame")
            self._log("⭐ Loaded Pink Galaxy Hook Frame template!")

        btn_galaxy = tk.Button(
            s_row,
            text="⭐ Pink Galaxy হুক ফ্রেম লোড করুন (ছবির মতো)",
            command=load_galaxy,
            bg="#f43f5e",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        btn_galaxy.pack(side="left", padx=(0, 6))

        btn_pink = tk.Button(
            s_row,
            text="⭐ Pink Panther ফ্রেম লোড করুন",
            command=load_pink,
            bg="#fce7f3",
            fg="#be185d",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        btn_pink.pack(side="left", padx=(0, 6))
        ttk.Button(s_row, text="🧹 Clear", width=6, command=lambda: self.custom_bg_path_var.set("")).pack(side="left")

        # --- PREVIEW ACTION BAR ---
        prev_bar = ttk.Frame(grid)
        prev_bar.pack(fill="x", pady=(4, 0))

        btn_prev = tk.Button(
            prev_bar,
            text="👁️ Preview Layout & Drag Studio (প্রিভিউ ও ড্র্যাগ স্টুডিও)",
            command=self._open_drag_studio,
            bg="#059669",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2"
        )
        btn_prev.pack(side="left", padx=(0, 10))

        ttk.Label(
            prev_bar,
            text="💡 টিপস: উপরের ১ নম্বর অপশনটি দিয়ে ছবির মতো উপরে ভিডিও ও নিচে মেম রিঅ্যাকশন সহজেই বানাতে পারবেন।",
            font=("Segoe UI", 8, "italic"),
            foreground="#64748b"
        ).pack(side="left")

    def _show_template_preview(self):
        self._open_drag_studio()

    def _open_video_crop_studio(self):
        try:
            video_path = self.videos[0]["path"] if self.videos else None
            orig_frame = None
            orig_w, orig_h = 720, 1280

            if video_path and os.path.exists(video_path):
                import tempfile
                tmp_png = os.path.join(tempfile.gettempdir(), f"crop_src_{os.getpid()}.png")
                try:
                    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", video_path, "-vframes", "1", tmp_png]
                    subprocess.run(cmd, timeout=4.0)
                    if os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 500:
                        orig_frame = Image.open(tmp_png).convert("RGB")
                        orig_w, orig_h = orig_frame.size
                except Exception:
                    pass
                finally:
                    if os.path.exists(tmp_png):
                        try:
                            os.remove(tmp_png)
                        except Exception:
                            pass

            if orig_frame is None:
                orig_frame = Image.new("RGB", (orig_w, orig_h), (35, 45, 65))
                d_draw = ImageDraw.Draw(orig_frame)
                d_draw.rectangle([10, 10, orig_w - 10, orig_h - 10], outline=(70, 130, 240), width=4)
                d_draw.text((orig_w // 2, orig_h // 2), "[ Video Sample Frame ]", fill=(255, 255, 255), anchor="mm")

            win = tk.Toplevel(self.root)
            win.title("✂️ Interactive Video Crop Studio (ভিডিও ফ্রেমের যে কোনো অংশ ম্যানুয়াল কাটুন)")
            win.geometry("900x700")
            win.resizable(False, False)
            win.transient(self.root)
            win.grab_set()

            CANVAS_W, CANVAS_H = 340, 580
            scale = min(CANVAS_W / float(orig_w), CANVAS_H / float(orig_h))
            disp_w = int(orig_w * scale)
            disp_h = int(orig_h * scale)
            off_x = (CANVAS_W - disp_w) // 2
            off_y = (CANVAS_H - disp_h) // 2

            crop_state = {
                "top": float(self.crop_top_pct_var.get()),
                "bottom": float(self.crop_bot_pct_var.get()),
                "left": float(self.crop_left_pct_var.get()),
                "right": float(self.crop_right_pct_var.get()),
                "photo": None
            }

            main_f = ttk.Frame(win, padding=12)
            main_f.pack(fill="both", expand=True)

            left_f = ttk.Frame(main_f)
            left_f.pack(side="left", padx=(0, 16))

            ttk.Label(left_f, text=f"📹 ভিডিও ফ্রেম ({orig_w}x{orig_h}px) - লাল দাগে ক্রপ অংশ দেখুন", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

            canvas = tk.Canvas(left_f, width=CANVAS_W, height=CANVAS_H, bg="#050811", highlightthickness=2, highlightbackground="#0284c7")
            canvas.pack()

            right_f = ttk.Frame(main_f)
            right_f.pack(side="left", fill="both", expand=True)

            ttk.Label(right_f, text="✂️ ম্যানুয়াল ভিডিও ক্রপ কন্ট্রোল", font=("Segoe UI", 12, "bold"), foreground="#0369a1").pack(anchor="w", pady=(0, 4))
            ttk.Label(right_f, text="ভিডিওর চারপাশ (ওপর, নিচ, বাম, ডান) থেকে অপ্রয়োজনীয় মেম/কার্টুন/অংশ কেটে বাদ দিন:", font=("Segoe UI", 8), foreground="#64748b").pack(anchor="w", pady=(0, 8))

            ctrl_card = ttk.LabelFrame(right_f, text=" 📐 চারপাশের কাটিং স্লাইডার (%) ", padding=10)
            ctrl_card.pack(fill="x", pady=(0, 8))

            # Crop Top
            r_ct = ttk.Frame(ctrl_card)
            r_ct.pack(fill="x", pady=2)
            ttk.Label(r_ct, text="⬆️ ওপর থেকে কাটুন:").pack(side="left")
            lbl_ct = ttk.Label(r_ct, text=f"{int(crop_state['top'])}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")
            
            def on_ct_slide(val):
                crop_state["top"] = float(val)
                lbl_ct.config(text=f"{int(float(val))}%")
                redraw_crop_canvas()
            sc_ct = ttk.Scale(r_ct, from_=0, to=70, orient="horizontal", value=crop_state["top"], command=on_ct_slide, length=150)
            sc_ct.pack(side="left", padx=6)
            lbl_ct.pack(side="left")

            # Crop Bottom
            r_cb = ttk.Frame(ctrl_card)
            r_cb.pack(fill="x", pady=2)
            ttk.Label(r_cb, text="⬇️ নিচ থেকে কাটুন:").pack(side="left")
            lbl_cb = ttk.Label(r_cb, text=f"{int(crop_state['bottom'])}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")
            def on_cb_slide(val):
                crop_state["bottom"] = float(val)
                lbl_cb.config(text=f"{int(float(val))}%")
                redraw_crop_canvas()
            sc_cb = ttk.Scale(r_cb, from_=0, to=70, orient="horizontal", value=crop_state["bottom"], command=on_cb_slide, length=150)
            sc_cb.pack(side="left", padx=6)
            lbl_cb.pack(side="left")

            # Crop Left (Cut Left Half e.g. Pink Panther)
            r_cl = ttk.Frame(ctrl_card)
            r_cl.pack(fill="x", pady=2)
            ttk.Label(r_cl, text="⬅️ বামপাশ থেকে কাটুন:").pack(side="left")
            lbl_cl = ttk.Label(r_cl, text=f"{int(crop_state['left'])}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")
            def on_cl_slide(val):
                crop_state["left"] = float(val)
                lbl_cl.config(text=f"{int(float(val))}%")
                redraw_crop_canvas()
            sc_cl = ttk.Scale(r_cl, from_=0, to=75, orient="horizontal", value=crop_state["left"], command=on_cl_slide, length=150)
            sc_cl.pack(side="left", padx=6)
            lbl_cl.pack(side="left")

            # Crop Right
            r_cr = ttk.Frame(ctrl_card)
            r_cr.pack(fill="x", pady=2)
            ttk.Label(r_cr, text="➡️ ডানপাশ থেকে কাটুন:").pack(side="left")
            lbl_cr = ttk.Label(r_cr, text=f"{int(crop_state['right'])}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")
            def on_cr_slide(val):
                crop_state["right"] = float(val)
                lbl_cr.config(text=f"{int(float(val))}%")
                redraw_crop_canvas()
            sc_cr = ttk.Scale(r_cr, from_=0, to=75, orient="horizontal", value=crop_state["right"], command=on_cr_slide, length=150)
            sc_cr.pack(side="left", padx=6)
            lbl_cr.pack(side="left")

            preset_card = ttk.LabelFrame(right_f, text=" ⚡ দ্রুত ১-ক্লিক স্মার্ট ক্রপ প্রিসেট ", padding=10)
            preset_card.pack(fill="x", pady=(0, 8))

            def set_crop_all(t, b, l, r):
                crop_state["top"] = t
                crop_state["bottom"] = b
                crop_state["left"] = l
                crop_state["right"] = r
                sc_ct.set(t); lbl_ct.config(text=f"{int(t)}%")
                sc_cb.set(b); lbl_cb.config(text=f"{int(b)}%")
                sc_cl.set(l); lbl_cl.config(text=f"{int(l)}%")
                sc_cr.set(r); lbl_cr.config(text=f"{int(r)}%")
                redraw_crop_canvas()

            r_p1 = ttk.Frame(preset_card)
            r_p1.pack(fill="x", pady=2)
            tk.Button(r_p1, text="👤 শুধু ডানপাশের মানুষ রাখুন (Crop Left 48%)", command=lambda: set_crop_all(0, 0, 48, 0), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_p1, text="🐾 শুধু বামপাশ রাখুন (Crop Right 48%)", command=lambda: set_crop_all(0, 0, 0, 48), bg="#f8fafc", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2").pack(side="left")

            r_p2 = ttk.Frame(preset_card)
            r_p2.pack(fill="x", pady=2)
            tk.Button(r_p2, text="⬛ স্কয়ার ক্রপ (1:1 Center)", command=lambda: set_crop_all(15, 15, 0, 0) if orig_h > orig_w else set_crop_all(0, 0, 15, 15), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_p2, text="🧹 রিসেট (০% - নো ক্রপ)", command=lambda: set_crop_all(0, 0, 0, 0), bg="#fee2e2", fg="#991b1b", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2").pack(side="left")

            lbl_dim = ttk.Label(right_f, text="", font=("Segoe UI", 9, "bold"), foreground="#059669")
            lbl_dim.pack(anchor="w", pady=(4, 8))

            def redraw_crop_canvas():
                t = crop_state["top"]
                b = crop_state["bottom"]
                l = crop_state["left"]
                r = crop_state["right"]

                cw = max(10, orig_w * (1.0 - (l + r) / 100.0))
                ch = max(10, orig_h * (1.0 - (t + b) / 100.0))
                lbl_dim.config(text=f"✂️ ক্রপ আউটপুট সাইজ: {int(cw)} x {int(ch)} px  (মূল: {orig_w}x{orig_h})")

                canvas.delete("all")
                disp_im = orig_frame.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
                crop_state["photo"] = ImageTk.PhotoImage(disp_im)
                canvas.create_image(off_x, off_y, anchor="nw", image=crop_state["photo"])

                # Draw dimmed rectangles outside crop area
                x1 = off_x + int(disp_w * (l / 100.0))
                y1 = off_y + int(disp_h * (t / 100.0))
                x2 = off_x + disp_w - int(disp_w * (r / 100.0))
                y2 = off_y + disp_h - int(disp_h * (b / 100.0))

                # Top dim
                if y1 > off_y:
                    canvas.create_rectangle(off_x, off_y, off_x + disp_w, y1, fill="#000000", stipple="gray50", outline="")
                # Bottom dim
                if y2 < off_y + disp_h:
                    canvas.create_rectangle(off_x, y2, off_x + disp_w, off_y + disp_h, fill="#000000", stipple="gray50", outline="")
                # Left dim
                if x1 > off_x:
                    canvas.create_rectangle(off_x, y1, x1, y2, fill="#000000", stipple="gray50", outline="")
                # Right dim
                if x2 < off_x + disp_w:
                    canvas.create_rectangle(x2, y1, off_x + disp_w, y2, fill="#000000", stipple="gray50", outline="")

                # Active crop outline
                canvas.create_rectangle(x1, y1, x2, y2, outline="#38bdf8", width=3, dash=(6, 2))
                canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=f"✂️ {int(cw)}x{int(ch)}", fill="#ffffff", font=("Segoe UI", 9, "bold"))

            redraw_crop_canvas()

            b_bar = ttk.Frame(right_f)
            b_bar.pack(fill="x", pady=(12, 0))

            def apply_crop():
                self.crop_top_pct_var.set(crop_state["top"])
                self.crop_bot_pct_var.set(crop_state["bottom"])
                self.crop_left_pct_var.set(crop_state["left"])
                self.crop_right_pct_var.set(crop_state["right"])
                self._log(f"✓ Video Crop saved: Top={int(crop_state['top'])}%, Bottom={int(crop_state['bottom'])}%, Left={int(crop_state['left'])}%, Right={int(crop_state['right'])}%")
                win.destroy()
                self._update_preview()

            btn_save = tk.Button(b_bar, text="💾 ক্রপ সংরক্ষণ করুন (Apply & Save Crop)", command=apply_crop, bg="#059669", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=7, cursor="hand2")
            btn_save.pack(side="left", padx=(0, 10))

            btn_cancel = tk.Button(b_bar, text="বাতিল (Cancel)", command=win.destroy, bg="#64748b", fg="white", font=("Segoe UI", 9), relief="flat", padx=14, pady=7, cursor="hand2")
            btn_cancel.pack(side="left")

        except Exception as e:
            messagebox.showerror("Crop Studio Error", f"Failed to open Video Crop Studio: {e}")

    def _open_box_drag_studio(self):
        try:
            self.enable_box_frame_var.set(True)
            self._on_box_frame_toggle()
            config = self._gather_config()
            video_path = self.videos[0]["path"] if self.videos else None

            win = tk.Toplevel(self.root)
            win.title("🖐️ Live Box Drag Studio (কাস্টম ব্যাকগ্রাউন্ড ও ভিডিও বক্স পজিশন)")
            win.geometry("920x840")
            win.resizable(False, False)
            win.transient(self.root)
            win.grab_set()

            CANVAS_W, CANVAS_H = 340, 604
            SCALE = CANVAS_W / 1080.0

            def _calc_target_dims(fit_mode_str, scale_w, scale_h):
                tw = max(160, int(1080 * scale_w))
                f_low = str(fit_mode_str).lower()
                if "1:1" in f_low or "square" in f_low or "1_1" in f_low:
                    th = tw
                elif "4:5" in f_low or "4_5" in f_low or "portrait" in f_low:
                    th = (int(tw * 1.25) // 2) * 2
                elif "16:9" in f_low or "16_9" in f_low or "landscape" in f_low:
                    th = (int(tw * 9 / 16) // 2) * 2
                else:
                    # Manual Custom Ratio / Fill Box / Free scale
                    th = max(160, (int(1920 * scale_h) // 2) * 2)
                return tw, th

            box_scale = float(config.get("box_scale", 0.75))
            cur_h_raw = self.box_height_scale_var.get().split("%")[0].strip()
            try:
                box_height_scale = float(cur_h_raw) / 100.0
            except Exception:
                box_height_scale = 0.55

            cur_fit = self.box_fit_mode_var.get()
            target_w, target_h = _calc_target_dims(cur_fit, box_scale, box_height_scale)

            cur_bx = self.box_custom_x_var.get().strip()
            cur_by = self.box_custom_y_var.get().strip()
            
            init_x = int(cur_bx) if (cur_bx and cur_bx.lstrip("-").isdigit()) else (1080 - target_w) // 2
            
            pos_v_raw = str(self.bg_video_pos_var.get()).lower()
            if cur_by and cur_by.lstrip("-").isdigit():
                init_y = int(cur_by)
            elif "bottom" in pos_v_raw:
                init_y = max(0, 1920 - target_h - 40)
            elif "top" in pos_v_raw:
                init_y = 40
            elif "lower" in pos_v_raw:
                init_y = int((1920 - target_h) * 0.70)
            else:
                init_y = max(0, (1920 - target_h) // 2)

            state = {
                "box_x": init_x,
                "box_y": init_y,
                "box_scale": box_scale,
                "box_height_scale": box_height_scale,
                "target_w": target_w,
                "target_h": target_h,
                "box_crop_y_pct": int(self.box_crop_y_pct_var.get()),
                "box_crop_x_pct": int(self.box_crop_x_pct_var.get()),
                "box_fit_mode": cur_fit,
                "drag_item": None,
                "drag_start_x": 0,
                "drag_start_y": 0,
                "bg_photo": None,
                "cached_bg_im": None
            }

            c_frame = ttk.Frame(win, padding=12)
            c_frame.pack(fill="both", expand=True)

            left_col = ttk.Frame(c_frame)
            left_col.pack(side="left", padx=(0, 16))

            ttk.Label(left_col, text="📱 9:16 Live Canvas (মাউস দিয়ে ভিডিও বক্স ড্র্যাগ করুন)", font=("Segoe UI", 9, "bold"), foreground="#0f172a").pack(anchor="w", pady=(0, 4))

            canvas = tk.Canvas(
                left_col,
                width=CANVAS_W,
                height=CANVAS_H,
                bg="#050811",
                highlightthickness=2,
                highlightbackground="#6366f1",
                cursor="fleur"
            )
            canvas.pack()

            right_col = ttk.Frame(c_frame)
            right_col.pack(side="left", fill="both", expand=True)

            ttk.Label(right_col, text="🎨 কাস্টম ব্যাকগ্রাউন্ড ও ভিডিও বক্স স্টুডিও", font=("Segoe UI", 12, "bold"), foreground="#1e293b").pack(anchor="w", pady=(0, 6))

            fit_card = ttk.LabelFrame(right_col, text=" 📦 ১. ভিডিও বক্স ফিট স্টাইল ও রেশিও মোড ", padding=8)
            fit_card.pack(fill="x", pady=(0, 6))

            ttk.Label(fit_card, text="ফিট স্টাইল / ম্যানুয়াল রেশিও:").pack(anchor="w")
            cb_studio_fit = ttk.Combobox(
                fit_card,
                textvariable=self.box_fit_mode_var,
                values=[
                    "Manual Custom Ratio (ম্যানুয়াল ক্রপ - নিজের ইচ্ছামতো সাইজ ও রেশিও)",
                    "Manual Custom Fit (ম্যানুয়াল - বক্সের ভেতর পুরো ভিডিও ফিট)",
                    "1:1 Square Box (Fit Full 9:16 Video - পুরো ভিডিও ফিট, নো ক্রপ)",
                    "Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)",
                    "Fit (ভিডিওর আসল রেশিও ঠিক রাখবে)",
                    "Square 1:1 Box (ক্রপ করে চারকোনা)",
                    "Portrait 4:5 Box",
                    "Landscape 16:9 Box"
                ],
                width=42,
                state="readonly"
            )
            cb_studio_fit.pack(fill="x", pady=(3, 4))

            def on_studio_fit_change(e=None):
                fit_val = self.box_fit_mode_var.get()
                state["box_fit_mode"] = fit_val
                state["target_w"], state["target_h"] = _calc_target_dims(fit_val, state["box_scale"], state["box_height_scale"])
                state["box_height_scale"] = state["target_h"] / 1920.0
                sc_sz_h.set(int(state["box_height_scale"] * 100))
                lbl_h_txt.config(text=f"{int(state['box_height_scale']*100)}% ({state['target_h']}px)")
                state["box_y"] = max(0, min(1920 - 40, state["box_y"]))
                state["box_x"] = max(0, min(1080 - 40, state["box_x"]))
                redraw_base_and_canvas()

            cb_studio_fit.bind("<<ComboboxSelected>>", on_studio_fit_change)

            crop_card = ttk.LabelFrame(right_col, text=" ✂️ ২. ভিডিও ক্রপ কাট পজিশন (বক্সের ভেতর ভিডিওর কোন অংশ কাটবে) ", padding=8)
            crop_card.pack(fill="x", pady=(0, 6))

            # Vertical Crop Slider
            r_cr_v = ttk.Frame(crop_card)
            r_cr_v.pack(fill="x", pady=(1, 3))
            ttk.Label(r_cr_v, text="ভার্টিক্যাল ক্রপ (Top ↕ Bottom):").pack(side="left")
            lbl_cr_txt = ttk.Label(r_cr_v, text=f"{state['box_crop_y_pct']}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

            def on_studio_cr_slide(val):
                try:
                    p = int(float(val))
                    state["box_crop_y_pct"] = p
                    self.box_crop_y_pct_var.set(p)
                    lbl_cr_txt.config(text=f"{p}%")
                    redraw_base_and_canvas()
                except Exception:
                    pass

            sc_box_cr = ttk.Scale(r_cr_v, from_=0, to=100, orient="horizontal", variable=self.box_crop_y_pct_var, command=on_studio_cr_slide, length=150)
            sc_box_cr.pack(side="left", padx=6)
            lbl_cr_txt.pack(side="left")

            def nudge_box_crop(delta):
                new_p = max(0, min(100, state["box_crop_y_pct"] + delta))
                state["box_crop_y_pct"] = new_p
                self.box_crop_y_pct_var.set(new_p)
                lbl_cr_txt.config(text=f"{new_p}%")
                redraw_base_and_canvas()

            def set_box_cr_preset(pct):
                state["box_crop_y_pct"] = pct
                self.box_crop_y_pct_var.set(pct)
                lbl_cr_txt.config(text=f"{pct}%")
                redraw_base_and_canvas()

            r_cr_btns = ttk.Frame(crop_card)
            r_cr_btns.pack(fill="x", pady=(0, 4))
            tk.Button(r_cr_btns, text="⬆️ ওপর (-5%)", command=lambda: nudge_box_crop(-5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_cr_btns, text="⬇️ নিচ (+5%)", command=lambda: nudge_box_crop(5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(r_cr_btns, text="👤 Face Focus (15%)", command=lambda: set_box_cr_preset(15), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_cr_btns, text="🎯 Center (50%)", command=lambda: set_box_cr_preset(50), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_cr_btns, text="⬇️ Bottom (85%)", command=lambda: set_box_cr_preset(85), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left")

            # Horizontal Crop Slider (Left ↔ Right)
            r_cr_h = ttk.Frame(crop_card)
            r_cr_h.pack(fill="x", pady=(1, 3))
            ttk.Label(r_cr_h, text="হরাইজন্টাল ক্রপ (Left ↔ Right):").pack(side="left")
            lbl_cr_x_txt = ttk.Label(r_cr_h, text=f"{state['box_crop_x_pct']}%", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

            def on_studio_cr_x_slide(val):
                try:
                    p = int(float(val))
                    state["box_crop_x_pct"] = p
                    self.box_crop_x_pct_var.set(p)
                    lbl_cr_x_txt.config(text=f"{p}%")
                    redraw_base_and_canvas()
                except Exception:
                    pass

            sc_box_cr_x = ttk.Scale(r_cr_h, from_=0, to=100, orient="horizontal", variable=self.box_crop_x_pct_var, command=on_studio_cr_x_slide, length=150)
            sc_box_cr_x.pack(side="left", padx=6)
            lbl_cr_x_txt.pack(side="left")

            def nudge_box_crop_x(delta):
                new_p = max(0, min(100, state["box_crop_x_pct"] + delta))
                state["box_crop_x_pct"] = new_p
                self.box_crop_x_pct_var.set(new_p)
                lbl_cr_x_txt.config(text=f"{new_p}%")
                redraw_base_and_canvas()

            r_cr_x_btns = ttk.Frame(crop_card)
            r_cr_x_btns.pack(fill="x", pady=(0, 4))
            tk.Button(r_cr_x_btns, text="⬅️ বাম (-5%)", command=lambda: nudge_box_crop_x(-5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_cr_x_btns, text="➡️ ডান (+5%)", command=lambda: nudge_box_crop_x(5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(r_cr_x_btns, text="👈 Left (15%)", command=lambda: [state.update({"box_crop_x_pct": 15}), self.box_crop_x_pct_var.set(15), lbl_cr_x_txt.config(text="15%"), redraw_base_and_canvas()], bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_cr_x_btns, text="🎯 Center (50%)", command=lambda: [state.update({"box_crop_x_pct": 50}), self.box_crop_x_pct_var.set(50), lbl_cr_x_txt.config(text="50%"), redraw_base_and_canvas()], bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_cr_x_btns, text="👉 Right (85%)", command=lambda: [state.update({"box_crop_x_pct": 85}), self.box_crop_x_pct_var.set(85), lbl_cr_x_txt.config(text="85%"), redraw_base_and_canvas()], bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left")

            btn_open_edge_cr = tk.Button(
                crop_card,
                text="✂️ ভিডিও সাইড/এজ ক্রপ টুল খুলুন (Crop Left/Right/Top/Bottom)",
                command=self._open_video_crop_studio,
                bg="#e0f2fe",
                fg="#0369a1",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                padx=6,
                pady=3,
                cursor="hand2"
            )
            btn_open_edge_cr.pack(fill="x", pady=(4, 2))

            pos_card = ttk.LabelFrame(right_col, text=" 📐 ৩. বক্স সাইজ ও ম্যানুয়াল রেশিও কন্ট্রোল (প্রস্থ ও উচ্চতা) ", padding=8)
            pos_card.pack(fill="x", pady=(0, 6))

            # Row 1: Width Slider
            r_sz_w = ttk.Frame(pos_card)
            r_sz_w.pack(fill="x", pady=1)
            ttk.Label(r_sz_w, text="বক্স প্রস্থ (Width):").pack(side="left")
            lbl_w_txt = ttk.Label(r_sz_w, text=f"{int(state['box_scale']*100)}% ({state['target_w']}px)", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

            def on_box_w_slide(val):
                try:
                    p = int(float(val)) / 100.0
                    state["box_scale"] = p
                    state["target_w"], state["target_h"] = _calc_target_dims(state["box_fit_mode"], p, state["box_height_scale"])
                    state["box_height_scale"] = state["target_h"] / 1920.0
                    lbl_w_txt.config(text=f"{int(p*100)}% ({state['target_w']}px)")
                    lbl_h_txt.config(text=f"{int(state['box_height_scale']*100)}% ({state['target_h']}px)")
                    sc_sz_h.set(int(state["box_height_scale"] * 100))
                    state["box_y"] = max(0, min(1920 - 40, state["box_y"]))
                    state["box_x"] = max(0, min(1080 - 40, state["box_x"]))
                    redraw_base_and_canvas()
                except Exception:
                    pass

            sc_sz_w = ttk.Scale(r_sz_w, from_=15, to=100, orient="horizontal", value=int(state['box_scale']*100), command=on_box_w_slide, length=150)
            sc_sz_w.pack(side="left", padx=6)
            lbl_w_txt.pack(side="left")

            def set_box_w_preset(p):
                sc_sz_w.set(p)
                on_box_w_slide(p)

            r_w_btns = ttk.Frame(pos_card)
            r_w_btns.pack(fill="x", pady=(0, 3))
            for wp in [45, 55, 65, 75, 95]:
                tk.Button(r_w_btns, text=f"{wp}%", command=lambda p=wp: set_box_w_preset(p), bg="#f8fafc", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))

            # Row 2: Height Slider (Manual Ratio / Height Scale)
            r_sz_h = ttk.Frame(pos_card)
            r_sz_h.pack(fill="x", pady=1)
            ttk.Label(r_sz_h, text="বক্স উচ্চতা (Height):").pack(side="left")
            lbl_h_txt = ttk.Label(r_sz_h, text=f"{int(state['box_height_scale']*100)}% ({state['target_h']}px)", font=("Segoe UI", 8, "bold"), foreground="#0284c7")

            def on_box_h_slide(val):
                try:
                    p = int(float(val)) / 100.0
                    state["box_height_scale"] = p
                    state["target_h"] = max(160, (int(1920 * p) // 2) * 2)
                    # Switch to manual custom ratio if previously locked
                    cur_f = state["box_fit_mode"].lower()
                    if "1:1" in cur_f or "square" in cur_f or "4:5" in cur_f or "16:9" in cur_f:
                        state["box_fit_mode"] = "Manual Custom Ratio (ম্যানুয়াল ক্রপ - নিজের ইচ্ছামতো সাইজ ও রেশিও)"
                        self.box_fit_mode_var.set(state["box_fit_mode"])
                    lbl_h_txt.config(text=f"{int(p*100)}% ({state['target_h']}px)")
                    state["box_y"] = max(0, min(1920 - 40, state["box_y"]))
                    state["box_x"] = max(0, min(1080 - 40, state["box_x"]))
                    redraw_base_and_canvas()
                except Exception:
                    pass

            sc_sz_h = ttk.Scale(r_sz_h, from_=15, to=100, orient="horizontal", value=int(state['box_height_scale']*100), command=on_box_h_slide, length=150)
            sc_sz_h.pack(side="left", padx=6)
            lbl_h_txt.pack(side="left")

            def set_box_h_preset(p):
                sc_sz_h.set(p)
                on_box_h_slide(p)

            r_h_btns = ttk.Frame(pos_card)
            r_h_btns.pack(fill="x", pady=(0, 4))
            for hp in [35, 45, 55, 65, 85]:
                tk.Button(r_h_btns, text=f"{hp}%", command=lambda p=hp: set_box_h_preset(p), bg="#f8fafc", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 3))

            r_qa = ttk.Frame(pos_card)
            r_qa.pack(fill="x", pady=(4, 0))

            def align_center():
                state["box_x"] = (1080 - state["target_w"]) // 2
                state["box_y"] = max(0, (1920 - state["target_h"]) // 2)
                redraw_base_and_canvas()

            def align_bottom():
                state["box_x"] = (1080 - state["target_w"]) // 2
                state["box_y"] = max(0, 1920 - state["target_h"] - 40)
                redraw_base_and_canvas()

            def align_top():
                state["box_x"] = (1080 - state["target_w"]) // 2
                state["box_y"] = 40
                redraw_base_and_canvas()

            def align_right():
                state["box_x"] = 1080 - state["target_w"]
                redraw_base_and_canvas()

            def align_left():
                state["box_x"] = 0
                redraw_base_and_canvas()

            def nudge_y(delta):
                state["box_y"] = max(0, min(1920 - 40, state["box_y"] + delta))
                redraw_base_and_canvas()

            def nudge_x(delta):
                state["box_x"] = max(0, min(1080 - 40, state["box_x"] + delta))
                redraw_base_and_canvas()

            tk.Button(r_qa, text="🎯 Center", command=align_center, bg="#f1f5f9", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_qa, text="⬇️ Bottom", command=align_bottom, bg="#dbeafe", fg="#1d4ed8", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_qa, text="⬆️ Top", command=align_top, bg="#f1f5f9", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_qa, text="👉 Right Flush", command=align_right, bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_qa, text="👈 Left Flush", command=align_left, bg="#f1f5f9", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left")

            r_nudge = ttk.Frame(pos_card)
            r_nudge.pack(fill="x", pady=(4, 0))
            tk.Button(r_nudge, text="⬇️ নিচে (+50px)", command=lambda: nudge_y(50), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_nudge, text="⬆️ উপরে (-50px)", command=lambda: nudge_y(-50), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 8, "bold"), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 3))
            tk.Button(r_nudge, text="⬅️ বামে (-30px)", command=lambda: nudge_x(-30), bg="#f8fafc", fg="#475569", font=("Segoe UI", 7), relief="flat", padx=4, pady=2, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_nudge, text="➡️ ডানে (+30px)", command=lambda: nudge_x(30), bg="#f8fafc", fg="#475569", font=("Segoe UI", 7), relief="flat", padx=4, pady=2, cursor="hand2").pack(side="left")

            lbl_coords = ttk.Label(
                right_col,
                text="",
                font=("Segoe UI", 8, "bold"),
                foreground="#0284c7"
            )
            lbl_coords.pack(anchor="w", pady=(3, 5))

            b_bar = ttk.Frame(right_col)
            b_bar.pack(fill="x", pady=(6, 0))

            def apply_and_save():
                self.enable_box_frame_var.set(True)
                self.bg_video_pos_x_var.set("custom")
                self.bg_video_pos_var.set("custom")
                self.box_custom_x_var.set(str(state["box_x"]))
                self.box_custom_y_var.set(str(state["box_y"]))
                self.box_crop_y_pct_var.set(state["box_crop_y_pct"])
                self.box_crop_x_pct_var.set(state["box_crop_x_pct"])
                self.box_fit_mode_var.set(state["box_fit_mode"])
                self.box_scale_var.set(f"{int(state['box_scale']*100)}%")
                self.box_height_scale_var.set(f"{int(state['box_height_scale']*100)}%")
                self._on_box_frame_toggle()
                self._log(f"✓ Saved box: X={state['box_x']}, Y={state['box_y']}, Size={state['target_w']}x{state['target_h']} ({int(state['box_scale']*100)}%x{int(state['box_height_scale']*100)}%), Crop=(V:{state['box_crop_y_pct']}%, H:{state['box_crop_x_pct']}%), Fit={state['box_fit_mode']}")
                win.destroy()

            btn_save = tk.Button(
                b_bar,
                text="💾 সেটিংস সংরক্ষণ করুন (Apply & Save)",
                command=apply_and_save,
                bg="#059669",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                padx=16,
                pady=7,
                cursor="hand2"
            )
            btn_save.pack(side="left", padx=(0, 10))

            btn_cancel = tk.Button(
                b_bar,
                text="বাতিল (Cancel)",
                command=win.destroy,
                bg="#64748b",
                fg="white",
                font=("Segoe UI", 9),
                relief="flat",
                padx=14,
                pady=7,
                cursor="hand2"
            )
            btn_cancel.pack(side="left")

            def redraw_base_and_canvas():
                cfg_temp = dict(self._gather_config())
                cfg_temp["enable_box_frame"] = True
                cfg_temp["bg_video_pos_x"] = "custom"
                cfg_temp["bg_video_pos"] = "custom"
                cfg_temp["custom_x"] = state["box_x"]
                cfg_temp["custom_y"] = state["box_y"]
                cfg_temp["box_scale"] = state["box_scale"]
                cfg_temp["box_height_scale"] = state["box_height_scale"]
                cfg_temp["box_crop_y_pct"] = state["box_crop_y_pct"]
                cfg_temp["box_crop_x_pct"] = state["box_crop_x_pct"]
                cfg_temp["box_fit_mode"] = state["box_fit_mode"]
                try:
                    state["cached_bg_im"] = generate_layout_preview(cfg_temp, video_path=video_path, preview_size=(CANVAS_W, CANVAS_H))
                except Exception:
                    pass
                redraw_canvas_overlay()

            def redraw_canvas_overlay():
                canvas.delete("all")
                if state["cached_bg_im"]:
                    state["bg_photo"] = ImageTk.PhotoImage(state["cached_bg_im"])
                    canvas.create_image(0, 0, anchor="nw", image=state["bg_photo"], tags="bg_layer")
                else:
                    canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H, fill="#050811", outline="", tags="bg_layer")

                bx = int(state["box_x"] * SCALE)
                by = int(state["box_y"] * SCALE)
                bw = int(state["target_w"] * SCALE)
                bh = int(state["target_h"] * SCALE)

                canvas.create_rectangle(bx, by, bx + bw, by + bh, outline="#38bdf8", width=2, dash=(4, 2), tags="box_drag")
                pill_w = 90
                canvas.create_rectangle(bx + bw//2 - pill_w, by + 4, bx + bw//2 + pill_w, by + 22, fill="#0284c7", outline="#ffffff", width=1, tags="box_drag")
                canvas.create_text(bx + bw//2, by + 13, text="🖐️ [ ভিডিও বক্স ড্র্যাগ করুন ]", fill="#ffffff", font=("Segoe UI", 7, "bold"), tags="box_drag")

                lbl_coords.config(text=f"📍 বক্স: X={state['box_x']}, Y={state['box_y']} | সাইজ: {state['target_w']}x{state['target_h']} ({int(state['box_scale']*100)}% x {int(state['box_height_scale']*100)}%) | ক্রপ: V={state['box_crop_y_pct']}%, H={state['box_crop_x_pct']}%")

            def on_canvas_press(event):
                items = canvas.find_withtag("current")
                if not items:
                    return
                tags = canvas.gettags(items[0])
                if "box_drag" in tags or "bg_layer" in tags:
                    state["drag_item"] = "box_drag"
                state["drag_start_x"] = event.x
                state["drag_start_y"] = event.y

            def on_canvas_drag(event):
                if not state["drag_item"]:
                    return
                dx = event.x - state["drag_start_x"]
                dy = event.y - state["drag_start_y"]
                state["drag_start_x"] = event.x
                state["drag_start_y"] = event.y

                state["box_x"] = max(0, min(1080 - 40, int(state["box_x"] + dx / SCALE)))
                state["box_y"] = max(0, min(1920 - 40, int(state["box_y"] + dy / SCALE)))
                redraw_base_and_canvas()

            def on_canvas_release(event):
                state["drag_item"] = None
                redraw_base_and_canvas()

            def on_canvas_wheel(event):
                delta = -3 if event.delta > 0 else 3
                nudge_box_crop(delta)

            canvas.bind("<ButtonPress-1>", on_canvas_press)
            canvas.bind("<B1-Motion>", on_canvas_drag)
            canvas.bind("<ButtonRelease-1>", on_canvas_release)
            canvas.bind("<MouseWheel>", on_canvas_wheel)

            redraw_base_and_canvas()

        except Exception as e:
            messagebox.showerror("Studio Error", f"Failed to open Box Studio: {e}")

    def _open_drag_studio(self):
        try:
            config = self._gather_config()
            video_path = self.videos[0]["path"] if self.videos else None

            # Window setup
            win = tk.Toplevel(self.root)
            win.title("🖐️ Live Drag & Drop Studio (9:16 রিলস টেমপ্লেট ও টেক্সট লাইভ প্রিভিউ)")
            win.geometry("820x720")
            win.resizable(False, False)
            win.transient(self.root)
            win.grab_set()

            CANVAS_W, CANVAS_H = 340, 604
            SCALE = CANVAS_W / 1080.0

            # State coordinates in 1080x1920
            cur_tx = self.text_custom_x_var.get().strip()
            cur_ty = self.text_custom_y_var.get().strip()
            cur_sy = self.split_custom_y_var.get().strip()

            state = {
                "real_text_x": int(cur_tx) if (cur_tx and cur_tx.lstrip("-").isdigit()) else 540,
                "real_text_y": int(cur_ty) if (cur_ty and cur_ty.lstrip("-").isdigit()) else (180 if config.get("enable_top_bottom_split") else 150),
                "real_video_y": int(cur_sy) if (cur_sy and cur_sy.isdigit()) else 380,
                "drag_item": None,
                "drag_start_x": 0,
                "drag_start_y": 0,
                "bg_photo": None,
                "cached_bg_im": None
            }

            # Pre-generate base composite layout preview WITHOUT text overlay
            cfg_no_text = dict(config)
            cfg_no_text["text_overlay"] = ""
            cfg_no_text["split_custom_y"] = state["real_video_y"]

            try:
                base_im = generate_layout_preview(cfg_no_text, video_path=video_path, preview_size=(CANVAS_W, CANVAS_H))
                state["cached_bg_im"] = base_im
            except Exception:
                state["cached_bg_im"] = None

            # Main container
            c_frame = ttk.Frame(win, padding=12)
            c_frame.pack(fill="both", expand=True)

            # Left side: Live Canvas
            left_col = ttk.Frame(c_frame)
            left_col.pack(side="left", padx=(0, 16))

            ttk.Label(left_col, text="📱 9:16 Live Canvas (মাউস দিয়ে ড্র্যাগ করুন)", font=("Segoe UI", 9, "bold"), foreground="#0f172a").pack(anchor="w", pady=(0, 4))

            canvas = tk.Canvas(
                left_col,
                width=CANVAS_W,
                height=CANVAS_H,
                bg="#050811",
                highlightthickness=2,
                highlightbackground="#38bdf8",
                cursor="fleur"
            )
            canvas.pack()

            # Right side: Live Control Dashboard
            right_col = ttk.Frame(c_frame)
            right_col.pack(side="left", fill="both", expand=True)

            ttk.Label(right_col, text="🎨 লাইভ ড্র্যাগ & ড্রপ স্টুডিও কন্ট্রোল", font=("Segoe UI", 12, "bold"), foreground="#1e293b").pack(anchor="w", pady=(0, 8))

            # Card 1: Text Controls
            t_card = ttk.LabelFrame(right_col, text=" ✍️ ১. ভিডিওর ওপরের হুক টেক্সট এডিটর ", padding=10)
            t_card.pack(fill="x", pady=(0, 8))

            ttk.Label(t_card, text="টেক্সট লিখুন (এখানে পরিবর্তন করলে লাইভ দেখতে পাবেন):", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            txt_entry = ttk.Entry(t_card, textvariable=self.text_overlay_var, font=("Segoe UI", 9))
            txt_entry.pack(fill="x", pady=(3, 6))

            # Quick Preset Hook Buttons
            ttk.Label(t_card, text="জনপ্রিয় হুক টেমপ্লেট:", font=("Segoe UI", 8)).pack(anchor="w")
            q_row = ttk.Frame(t_card)
            q_row.pack(fill="x", pady=(2, 6))

            def apply_quick_hook(txt):
                self.text_overlay_var.set(txt)
                if state["real_video_y"] < 320:
                    state["real_video_y"] = 380
                    redraw_base_and_canvas()
                else:
                    redraw_canvas_overlay()

            tk.Button(q_row, text="😱 WAIT FOR IT", command=lambda: apply_quick_hook("WAIT FOR IT 😱"), bg="#fef08a", fg="#854d0e", font=("Segoe UI", 7, "bold"), relief="flat", padx=5, pady=2, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(q_row, text="👇 WAIT TILL END", command=lambda: apply_quick_hook("WAIT TILL THE END 👇"), bg="#fed7aa", fg="#9a3412", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=2, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(q_row, text="🤣 শেষ পর্যন্ত দেখুন", command=lambda: apply_quick_hook("শেষ পর্যন্ত দেখুন 🤣🔥"), bg="#dcfce7", fg="#166534", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=2, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(q_row, text="🔥 OMG WATCH THIS", command=lambda: apply_quick_hook("OMG WATCH THIS 🔥"), bg="#fee2e2", fg="#991b1b", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=2, cursor="hand2").pack(side="left")

            # Style Rows
            r_st = ttk.Frame(t_card)
            r_st.pack(fill="x", pady=3)

            ttk.Label(r_st, text="কালার:").pack(side="left")
            cb_c = ttk.Combobox(r_st, textvariable=self.text_color_var, values=["Yellow (হলুদ - ভাইরাল)", "White (সাদা)", "Red (লাল)", "Cyan (আকাশি)", "Green (সবুজ)", "Black (কালো)"], width=15, state="readonly")
            cb_c.pack(side="left", padx=4)

            ttk.Label(r_st, text="সাইজ:").pack(side="left", padx=(8, 0))
            cb_s = ttk.Combobox(r_st, textvariable=self.text_fontsize_var, values=["54px (স্ট্যান্ডার্ড রিলস)", "40px (ছোট)", "48px (মিডিয়াম)", "64px (বড়)", "76px (এক্সট্রা লার্জ)"], width=14, state="readonly")
            cb_s.pack(side="left", padx=4)

            r_bg = ttk.Frame(t_card)
            r_bg.pack(fill="x", pady=4)
            ttk.Label(r_bg, text="ব্যাকগ্রাউন্ড বক্স:").pack(side="left")
            cb_b = ttk.Combobox(r_bg, textvariable=self.text_box_bg_var, values=["Black Box (কালো বক্স)", "White Box (সাদা বক্স)", "Red Box (লাল বক্স)", "None (বক্স ছাড়া)"], width=16, state="readonly")
            cb_b.pack(side="left", padx=4)

            # Quick Align Buttons for Text
            r_align = ttk.Frame(t_card)
            r_align.pack(fill="x", pady=(4, 0))

            def center_text_h():
                state["real_text_x"] = 540
                redraw_canvas_overlay()

            def place_in_top_empty():
                if config.get("enable_top_bottom_split"):
                    state["real_text_y"] = max(80, state["real_video_y"] // 2)
                else:
                    state["real_text_y"] = 150
                state["real_text_x"] = 540
                redraw_canvas_overlay()

            tk.Button(r_align, text="🎯 মাঝখানে সোজা করুন (Center)", command=center_text_h, bg="#e2e8f0", fg="#334155", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_align, text="⬆️ উপরে ফাঁকা জায়গায় বসান", command=place_in_top_empty, bg="#bae6fd", fg="#0369a1", font=("Segoe UI", 8, "bold"), relief="flat", padx=6, pady=2, cursor="hand2").pack(side="left")

            # Card 2: Video Position Controls
            v_card = ttk.LabelFrame(right_col, text=" 📹 ২. ভিডিও পজিশন ও স্পেসিং কন্ট্রোল ", padding=10)
            v_card.pack(fill="x", pady=(0, 8))

            def shift_video_down():
                state["real_video_y"] = min(750, state["real_video_y"] + 60)
                if state["real_text_y"] > state["real_video_y"] - 40:
                    state["real_text_y"] = max(80, state["real_video_y"] // 2)
                redraw_base_and_canvas()

            def shift_video_up():
                state["real_video_y"] = max(0, state["real_video_y"] - 60)
                redraw_base_and_canvas()

            def reset_video_center():
                state["real_video_y"] = 380 if config.get("enable_top_bottom_split") else 500
                state["real_text_x"] = 540
                state["real_text_y"] = 180 if config.get("enable_top_bottom_split") else 150
                redraw_base_and_canvas()

            # Live Crop Fit and Background selector inside Drag Studio
            r_crop_row = ttk.Frame(v_card)
            r_crop_row.pack(fill="x", pady=(0, 3))
            ttk.Label(r_crop_row, text="ক্রপ কাট:").pack(side="left")

            cb_crop_align = ttk.Combobox(
                r_crop_row,
                textvariable=self.split_crop_align_var,
                values=[
                    "Top Focus (ওপর ঠিক রেখে নিচ থেকে কাটবে - ফেস ফোকাস)",
                    "Center (মাঝখান থেকে ক্রপ - ওপর-নিচ সমান)",
                    "Bottom Focus (নিচ ঠিক রেখে ওপর থেকে কাটবে)",
                    "Manual Slider (ম্যানুয়াল স্লাইডার - কাস্টম পজিশন)"
                ],
                width=24,
                state="readonly"
            )
            cb_crop_align.pack(side="left", padx=(4, 8))

            def on_crop_align_change(e=None):
                self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
                val_txt = self.split_crop_align_var.get()
                if "Top" in val_txt:
                    self.split_crop_y_pct_var.set(0)
                elif "Bottom" in val_txt:
                    self.split_crop_y_pct_var.set(100)
                elif "Center" in val_txt:
                    self.split_crop_y_pct_var.set(50)
                lbl_studio_crop.config(text=f"{self.split_crop_y_pct_var.get()}%")
                redraw_base_and_canvas()

            cb_crop_align.bind("<<ComboboxSelected>>", on_crop_align_change)

            # Interactive Crop Slider & Nudge Buttons inside Studio
            r_crop_slider = ttk.Frame(v_card)
            r_crop_slider.pack(fill="x", pady=(2, 4))
            ttk.Label(r_crop_slider, text="✂️ ক্রপ পজিশন:").pack(side="left")

            def on_studio_crop_slide(val):
                try:
                    pct = int(float(val))
                    self.split_crop_y_pct_var.set(pct)
                    self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
                    self.split_crop_align_var.set("Manual Slider (ম্যানুয়াল স্লাইডার - কাস্টম পজিশন)")
                    lbl_studio_crop.config(text=f"{pct}%")
                    redraw_base_and_canvas()
                except Exception:
                    pass

            crop_scale = ttk.Scale(
                r_crop_slider,
                from_=0,
                to=100,
                orient="horizontal",
                variable=self.split_crop_y_pct_var,
                command=on_studio_crop_slide,
                length=150
            )
            crop_scale.pack(side="left", padx=4)

            lbl_studio_crop = ttk.Label(
                r_crop_slider,
                text=f"{self.split_crop_y_pct_var.get()}%",
                font=("Segoe UI", 8, "bold"),
                foreground="#0284c7"
            )
            lbl_studio_crop.pack(side="left", padx=(2, 4))

            def nudge_crop(delta):
                cur = self.split_crop_y_pct_var.get()
                new_val = max(0, min(100, cur + delta))
                self.split_crop_y_pct_var.set(new_val)
                self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
                self.split_crop_align_var.set("Manual Slider (ম্যানুয়াল স্লাইডার - কাস্টম পজিশন)")
                lbl_studio_crop.config(text=f"{new_val}%")
                redraw_base_and_canvas()

            def set_studio_preset(pct, lbl):
                self.split_crop_y_pct_var.set(pct)
                self.split_video_fit_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
                self.split_crop_align_var.set(lbl)
                lbl_studio_crop.config(text=f"{pct}%")
                redraw_base_and_canvas()

            r_nudge = ttk.Frame(v_card)
            r_nudge.pack(fill="x", pady=(0, 4))
            tk.Button(r_nudge, text="⬆️ ওপর (-5%)", command=lambda: nudge_crop(-5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 4))
            tk.Button(r_nudge, text="⬇️ নিচ (+5%)", command=lambda: nudge_crop(5), bg="#e0f2fe", fg="#0369a1", font=("Segoe UI", 7, "bold"), relief="flat", padx=4, pady=1, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_nudge, text="👤 Face (15%)", command=lambda: set_studio_preset(15, "Top Focus (ওপর ঠিক রেখে নিচ থেকে কাটবে - ফেস ফোকাস)"), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=3, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_nudge, text="🎯 Mid (50%)", command=lambda: set_studio_preset(50, "Center (মাঝখান থেকে ক্রপ - ওপর-নিচ সমান)"), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=3, pady=1, cursor="hand2").pack(side="left", padx=(0, 2))
            tk.Button(r_nudge, text="⬇️ Bot (85%)", command=lambda: set_studio_preset(85, "Bottom Focus (নিচ ঠিক রেখে ওপর থেকে কাটবে)"), bg="#f1f5f9", fg="#334155", font=("Segoe UI", 7), relief="flat", padx=3, pady=1, cursor="hand2").pack(side="left")

            r_vbtn = ttk.Frame(v_card)
            r_vbtn.pack(fill="x", pady=2)
            tk.Button(r_vbtn, text="⬇️ ভিডিও নিচে নামান (ফাঁকা জায়গা বড় করুন)", command=shift_video_down, bg="#f1f5f9", fg="#1e293b", font=("Segoe UI", 8, "bold"), relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_vbtn, text="⬆️ ভিডিও উপরে তুলুন", command=shift_video_up, bg="#f1f5f9", fg="#1e293b", font=("Segoe UI", 8), relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(r_vbtn, text="⚖️ ডিফল্ট রিসেট", command=reset_video_center, bg="#f8fafc", fg="#64748b", font=("Segoe UI", 8), relief="flat", padx=6, pady=3, cursor="hand2").pack(side="left")

            # Coordinates readout
            lbl_coords = ttk.Label(
                right_col,
                text="",
                font=("Segoe UI", 9, "bold"),
                foreground="#0284c7"
            )
            lbl_coords.pack(anchor="w", pady=(4, 8))

            # Bottom Action Buttons
            b_bar = ttk.Frame(right_col)
            b_bar.pack(fill="x", pady=(10, 0))

            def apply_and_close():
                # Store coordinates back into GUI
                self.text_custom_x_var.set(str(state["real_text_x"]))
                self.text_custom_y_var.set(str(state["real_text_y"]))
                self.split_custom_y_var.set(str(state["real_video_y"]))
                self._log(f"✓ Saved live drag positions! Text: ({state['real_text_x']}, {state['real_text_y']}), Video Y: {state['real_video_y']}")
                win.destroy()

            btn_save = tk.Button(
                b_bar,
                text="💾 সেটিংস সংরক্ষণ করুন (Apply & Save)",
                command=apply_and_close,
                bg="#059669",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                padx=18,
                pady=7,
                cursor="hand2"
            )
            btn_save.pack(side="left", padx=(0, 10))

            btn_cancel = tk.Button(
                b_bar,
                text="বাতিল (Cancel)",
                command=win.destroy,
                bg="#64748b",
                fg="white",
                font=("Segoe UI", 9),
                relief="flat",
                padx=14,
                pady=7,
                cursor="hand2"
            )
            btn_cancel.pack(side="left")

            # Redraw functions
            def redraw_base_and_canvas():
                cfg_temp = dict(self._gather_config())
                cfg_temp["text_overlay"] = ""
                cfg_temp["split_custom_y"] = state["real_video_y"]
                cfg_temp["split_crop_y_pct"] = self.split_crop_y_pct_var.get()
                cfg_temp["split_video_fit"] = "crop_fill" if ("Fill" in self.split_video_fit_var.get() or "Manual" in self.split_video_fit_var.get() or "Top" in self.split_crop_align_var.get() or "Bottom" in self.split_crop_align_var.get() or "Center" in self.split_crop_align_var.get() or "Manual" in self.split_crop_align_var.get()) else "fit"
                cfg_temp["split_crop_align"] = "manual" if ("Manual" in self.split_crop_align_var.get() or "ম্যানুয়াল" in self.split_crop_align_var.get()) else ("top" if "Top" in self.split_crop_align_var.get() else ("bottom" if "Bottom" in self.split_crop_align_var.get() else "center"))
                try:
                    state["cached_bg_im"] = generate_layout_preview(cfg_temp, video_path=video_path, preview_size=(CANVAS_W, CANVAS_H))
                except Exception:
                    pass
                redraw_canvas_overlay()

            def redraw_canvas_overlay():
                canvas.delete("all")
                # Draw background composite
                if state["cached_bg_im"]:
                    state["bg_photo"] = ImageTk.PhotoImage(state["cached_bg_im"])
                    canvas.create_image(0, 0, anchor="nw", image=state["bg_photo"], tags="bg_layer")
                else:
                    canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H, fill="#050811", outline="", tags="bg_layer")

                # Video handle zone indicator (allows dragging video frame & meme together)
                vy = int(state["real_video_y"] * SCALE)
                # Transparent full-width hit-box for smooth dragging anywhere on video
                canvas.create_rectangle(0, vy, CANVAS_W, CANVAS_H, fill="", outline="", tags="video_block")
                # Subtle drag handle pill at the top of video
                pill_w = 110
                canvas.create_rectangle(CANVAS_W//2 - pill_w, vy + 4, CANVAS_W//2 + pill_w, vy + 22, fill="#0284c7", outline="#ffffff", width=1, tags="video_block")
                canvas.create_text(CANVAS_W // 2, vy + 13, text="↕️ [ ভিডিও ও মেম ড্র্যাগ করুন ]", fill="#ffffff", font=("Segoe UI", 7, "bold"), tags="video_block")

                # Draw Text Block
                tx = int(state["real_text_x"] * SCALE)
                ty = int(state["real_text_y"] * SCALE)

                text_val = self.text_overlay_var.get().strip()
                if text_val:
                    t_col_raw = self.text_color_var.get().lower()
                    col_map = {
                        "yellow": "#facc15",
                        "white": "#ffffff",
                        "red": "#ef4444",
                        "cyan": "#06b6d4",
                        "green": "#22c55e",
                        "black": "#000000"
                    }
                    fg_col = "#facc15"
                    for k, v in col_map.items():
                        if k in t_col_raw:
                            fg_col = v
                            break

                    b_raw = self.text_box_bg_var.get().lower()
                    if "none" in b_raw or "ছাড়া" in b_raw:
                        bg_col = None
                    elif "white" in b_raw or "সাদা" in b_raw:
                        bg_col = "#ffffff"
                        if fg_col == "#ffffff":
                            fg_col = "#000000"
                    elif "red" in b_raw or "লাল" in b_raw:
                        bg_col = "#b91c1c"
                    else:
                        bg_col = "#000000"

                    try:
                        fs_raw = int(self.text_fontsize_var.get().split("px")[0].split()[0].strip())
                    except Exception:
                        fs_raw = 54
                    fs = max(11, int(fs_raw * SCALE))

                    # Approximate bounding box
                    tw = max(80, len(text_val) * (fs * 65 // 100))
                    th = fs * 2

                    if bg_col:
                        canvas.create_rectangle(tx - tw//2, ty - th//2, tx + tw//2, ty + th//2, fill=bg_col, outline="#f59e0b", width=1, tags="text_block")

                    canvas.create_text(tx, ty, text=text_val, fill=fg_col, font=("Segoe UI", fs, "bold"), tags="text_block")
                    # Visual drag handle pill
                    canvas.create_text(tx, ty - th//2 - 7, text="✍️ [ হুক টেক্সট ড্র্যাগ করুন ]", fill="#f59e0b", font=("Segoe UI", 6, "bold"), tags="text_block")

                lbl_coords.config(text=f"📍 টেক্সট পজিশন: X={state['real_text_x']}, Y={state['real_text_y']}  |  ভিডিও শুরু: Y={state['real_video_y']}")

            # Drag event handlers
            def on_canvas_press(event):
                items = canvas.find_withtag("current")
                if not items:
                    return
                tags = canvas.gettags(items[0])
                if "text_block" in tags:
                    state["drag_item"] = "text_block"
                elif "video_block" in tags:
                    state["drag_item"] = "video_block"
                else:
                    state["drag_item"] = None
                state["drag_start_x"] = event.x
                state["drag_start_y"] = event.y

            def on_canvas_drag(event):
                if not state["drag_item"]:
                    return
                dx = event.x - state["drag_start_x"]
                dy = event.y - state["drag_start_y"]
                state["drag_start_x"] = event.x
                state["drag_start_y"] = event.y

                if state["drag_item"] == "text_block":
                    state["real_text_x"] = max(50, min(1030, int(state["real_text_x"] + dx / SCALE)))
                    state["real_text_y"] = max(30, min(1890, int(state["real_text_y"] + dy / SCALE)))
                    redraw_canvas_overlay()
                elif state["drag_item"] == "video_block":
                    state["real_video_y"] = max(0, min(800, int(state["real_video_y"] + dy / SCALE)))
                    redraw_canvas_overlay()

            def on_canvas_release(event):
                if state["drag_item"] == "video_block":
                    redraw_base_and_canvas()
                state["drag_item"] = None

            canvas.bind("<ButtonPress-1>", on_canvas_press)
            canvas.bind("<B1-Motion>", on_canvas_drag)
            canvas.bind("<ButtonRelease-1>", on_canvas_release)

            def on_canvas_wheel(event):
                delta = -3 if event.delta > 0 else 3
                nudge_crop(delta)
            canvas.bind("<MouseWheel>", on_canvas_wheel)

            # Auto-redraw when text or combos change
            txt_entry.bind("<KeyRelease>", lambda e: redraw_canvas_overlay())
            cb_c.bind("<<ComboboxSelected>>", lambda e: redraw_canvas_overlay())
            cb_s.bind("<<ComboboxSelected>>", lambda e: redraw_canvas_overlay())
            cb_b.bind("<<ComboboxSelected>>", lambda e: redraw_canvas_overlay())

            redraw_canvas_overlay()

        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to open Drag Studio: {e}")

    def _build_tab_audio(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True)

        # Row 0: Volume & Anti-Audio Hash
        ttk.Label(grid, text="Volume Boost:").grid(row=0, column=0, sticky="w", pady=6)
        vol_cb = ttk.Combobox(
            grid,
            textvariable=self.volume_var,
            values=["1.00 (Normal)", "1.10 (+10%)", "1.15 (+15% Recommended)", "1.25 (+25%)"],
            width=20,
            state="readonly"
        )
        vol_cb.grid(row=0, column=1, sticky="w", padx=8)

        ttk.Checkbutton(
            grid,
            text="Anti-Audio Fingerprint (Frequency EQ Shift)",
            variable=self.anti_audio_hash_var
        ).grid(row=0, column=2, columnspan=2, sticky="w", padx=(20, 0))

        # Row 1: Top/Bottom Split Audio Source
        ttk.Label(grid, text="Top/Bottom Split Audio:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            grid,
            textvariable=self.split_audio_source_var,
            values=[
                "Reel Sound (মূল রিল সাউন্ড - ডিফল্ট)",
                "Meme Sound (রিঅ্যাকশন মেম সাউন্ড)",
                "Mix Both (উভয় সাউন্ড মিক্স - রিল + মেম)",
                "Mute All (কোনো সাউন্ড থাকবে না - মিউট)"
            ],
            width=30,
            state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=8)

        # Row 2: Background Music (BGM)
        ttk.Label(grid, text="Background Music (Optional):").grid(row=2, column=0, sticky="w", pady=6)
        bgm_entry = ttk.Entry(grid, textvariable=self.bgm_path_var, width=40)
        bgm_entry.grid(row=2, column=1, sticky="w", padx=8)

        btn_browse_bgm = ttk.Button(grid, text="Browse Audio...", command=self._browse_bgm)
        btn_browse_bgm.grid(row=2, column=2, sticky="w", padx=5)

        # Row 3: BGM Volume
        ttk.Label(grid, text="BGM Volume:").grid(row=2, column=0, sticky="w", pady=6)
        bgm_vol_cb = ttk.Combobox(
            grid,
            textvariable=self.bgm_volume_var,
            values=["5%", "8%", "10% (Recommended)", "15%", "20%"],
            width=18,
            state="readonly"
        )
        bgm_vol_cb.grid(row=2, column=1, sticky="w", padx=8)

    def _build_tab_branding(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True)

        # Row 0: Hook Banner Text
        ttk.Label(grid, text="Top/Bottom Hook Text:").grid(row=0, column=0, sticky="w", pady=6)
        text_entry = ttk.Entry(grid, textvariable=self.text_overlay_var, width=35)
        text_entry.grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Text Position:").grid(row=0, column=2, sticky="w", padx=(15, 0))
        pos_cb = ttk.Combobox(
            grid,
            textvariable=self.text_position_var,
            values=["top", "bottom", "center"],
            width=12,
            state="readonly"
        )
        pos_cb.grid(row=0, column=3, sticky="w", padx=8)

        btn_drag_b = tk.Button(
            grid,
            text="🖐️ ড্র্যাগ & ড্রপ স্টুডিও",
            command=self._open_drag_studio,
            bg="#6366f1",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_drag_b.grid(row=0, column=4, sticky="w", padx=8)

        # Row 1: Logo / Watermark PNG
        ttk.Label(grid, text="Watermark Logo PNG:").grid(row=1, column=0, sticky="w", pady=6)
        wm_entry = ttk.Entry(grid, textvariable=self.watermark_path_var, width=35)
        wm_entry.grid(row=1, column=1, sticky="w", padx=8)

        btn_browse_wm = ttk.Button(grid, text="Browse Logo...", command=self._browse_watermark)
        btn_browse_wm.grid(row=1, column=2, sticky="w", padx=5)

        wm_pos_cb = ttk.Combobox(
            grid,
            textvariable=self.watermark_pos_var,
            values=["top_right", "top_left", "bottom_right", "bottom_left"],
            width=12,
            state="readonly"
        )
        wm_pos_cb.grid(row=1, column=3, sticky="w", padx=8)

    def _build_tab_output(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill="both", expand=True)

        # Row 0: Output Directory
        ttk.Label(grid, text="Output Directory:").grid(row=0, column=0, sticky="w", pady=6)
        out_entry = ttk.Entry(grid, textvariable=self.output_dir_var, width=45)
        out_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=8)

        btn_browse_out = ttk.Button(grid, text="Browse...", command=self._browse_output_dir)
        btn_browse_out.grid(row=0, column=3, sticky="w", padx=5)

        # Row 1: Prefix / Suffix
        ttk.Label(grid, text="Filename Prefix:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(grid, textvariable=self.output_prefix_var, width=15).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Filename Suffix:").grid(row=1, column=2, sticky="w", padx=(10, 0))
        ttk.Entry(grid, textvariable=self.output_suffix_var, width=15).grid(row=1, column=3, sticky="w", padx=8)

        # Row 2: Encoding Quality & Preset
        ttk.Label(grid, text="Video Quality (CRF):").grid(row=2, column=0, sticky="w", pady=6)
        crf_cb = ttk.Combobox(
            grid,
            textvariable=self.crf_var,
            values=["18 (High Quality)", "21 (Balanced - Rec)", "24 (Smaller Size)"],
            width=20,
            state="readonly"
        )
        crf_cb.grid(row=2, column=1, sticky="w", padx=8)

        ttk.Checkbutton(
            grid,
            text="Erase Original Metadata (-map_metadata -1)",
            variable=self.strip_meta_var
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(10, 0))

        # Row 3: Speed Preset
        ttk.Label(grid, text="রেন্ডারিং স্পিড (Speed):").grid(row=3, column=0, sticky="w", pady=6)
        spd_cb = ttk.Combobox(
            grid,
            textvariable=self.preset_speed_var,
            values=[
                "Fast (দ্রুত - রিকমেন্ডেড)",
                "Very Fast (সুপার ফাস্ট - ৩ সেকেন্ডে রেন্ডার)",
                "Ultra Fast (টার্বো স্পিড - ২ সেকেন্ডে রেন্ডার)",
                "Medium (ব্যালান্সড)"
            ],
            width=32,
            state="readonly"
        )
        spd_cb.grid(row=3, column=1, columnspan=2, sticky="w", padx=8)

    # --- PRESET LOGIC ---

    def _apply_preset_values(self, preset_key: str):
        if preset_key == "meta_reels":
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("3% (Recommended)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Reels Blur (95% Video + Border Canvas)")
            self.enable_box_frame_var.set(False)
            self.box_border_color_var.set("White (সাদা - ছবির মতো)")
            self.box_border_width_var.set("6px (রিলস স্ট্যান্ডার্ড)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="1.03x Speed + 3% Zoom + 95% Reels Blur Canvas + Color Grade + Audio EQ + Strip Meta"
            )
            self._on_box_frame_toggle()

        elif preset_key == "pink_galaxy_frame":
            self.enable_split_var.set(False)
            self.enable_box_frame_var.set(True)
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Vertical (Blur Canvas - 100% Full Width)")
            self.box_scale_var.set("75% (ছবির মতো - পিংক গ্যালাক্সি)")
            self.box_height_scale_var.set("51% (বক্স মাপ)")
            self.box_fit_mode_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
            self.box_border_color_var.set("White (সাদা - ছবির মতো)")
            self.box_border_width_var.set("6px (রিলস স্ট্যান্ডার্ড)")
            self.bg_video_pos_var.set("galaxy_hook (৬৪৮px - পিংক গ্যালাক্সি ফ্রেম)")
            self.bg_video_pos_x_var.set("Center (মাঝখানে)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)

            sample_galaxy = os.path.join(os.path.dirname(__file__), "templates", "sample_pink_galaxy_template.png")
            if os.path.exists(sample_galaxy):
                self.custom_bg_path_var.set(sample_galaxy)

            self.preset_info_lbl.config(
                text="ছবির মতো ফ্রেম: পিংক গ্যালাক্সি + উপরে ডাবল হুক ব্যানার + ৭৫% সাইজের হোয়াইট ফ্রেম বক্স"
            )
            self._on_box_frame_toggle()
            if hasattr(self, 'notebook') and hasattr(self, 'tab_template'):
                try:
                    self.notebook.select(self.tab_template)
                except Exception:
                    pass

        elif preset_key == "top_bottom_split":
            self.enable_split_var.set(True)
            self.enable_box_frame_var.set(False)
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Vertical (Blur Canvas - 100% Full Width)")
            self.split_layout_var.set("Top Video + Bottom Meme (উপরে ভিডিও + নিচে মেম - ছবির মতো)")
            self.split_bg_style_var.set("Black (কালো - ছবির মতো)")
            self.split_video_h_var.set("50% (স্ট্যান্ডার্ড)")
            self.split_meme_h_var.set("40% (ছবির মতো - Jim Carrey মেম সাইজ)")
            self.split_box_w_var.set("96% (ছবির মতো সাইড মার্জিন)")
            self.split_video_fit_var.set("Fit (অরিজিনাল সাইজ - নো ক্রপ)")
            self.split_border_color_var.set("White (সাদা - ছবির মতো)")
            self.split_border_width_var.set("6px (রিলস স্ট্যান্ডার্ড)")
            self.split_border_target_var.set("Video Only (শুধু মূল ভিডিওতে)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)

            sample_jim = os.path.join(os.path.dirname(__file__), "templates", "sample_reaction_meme.png")
            if not self.split_meme_path_var.get() and os.path.exists(sample_jim):
                self.split_meme_path_var.set(sample_jim)

            self.preset_info_lbl.config(
                text="ছবির মতো স্প্লিট: উপরে মূল ভিডিও + নিচে জিম ক্যারি/মেম রিঅ্যাকশন + কালো ক্যানভাস"
            )
            self._on_box_frame_toggle()
            if hasattr(self, 'notebook') and hasattr(self, 'tab_template'):
                try:
                    self.notebook.select(self.tab_template)
                except Exception:
                    pass

        elif preset_key == "custom_meme_template":
            self.enable_box_frame_var.set(True)
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Vertical (Blur Canvas - 100% Full Width)")
            self.bg_video_pos_x_var.set("Right Side (ডানপাশে - ছবির মতো)")
            self.bg_video_pos_var.set("below_header (১৪% - হেডারের নিচে ছবির মতো)")
            self.box_scale_var.set("60% (ছবির মতো - ডানপাশের জন্য পারফেক্ট)")
            self.box_height_scale_var.set("85% (ছবির মতো - লম্বা ফ্রেম)")
            self.box_fit_mode_var.set("Fill Box (ক্রপ করে পুরো বক্স ফিল করবে)")
            self.box_border_color_var.set("None (বর্ডার ছাড়া - ছবির মতো)")
            self.box_border_width_var.set("0px (বর্ডার ছাড়া)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)

            sample_tmpl = os.path.join(os.path.dirname(__file__), "templates", "sample_meme_template.png")
            if not self.custom_bg_path_var.get() and os.path.exists(sample_tmpl):
                self.custom_bg_path_var.set(sample_tmpl)

            self.preset_info_lbl.config(
                text="ছবির মতো সাইড মেম: ৬০% চওড়া ও ৮৫% লম্বা ভিডিও ডানপাশে + কাস্টম টেমপ্লেট ব্যাকগ্রাউন্ড"
            )
            self._on_box_frame_toggle()
            if hasattr(self, 'notebook') and hasattr(self, 'tab_template'):
                try:
                    self.notebook.select(self.tab_template)
                except Exception:
                    pass

        elif preset_key == "reels_95_blur":
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("3% (Recommended)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Reels Blur (95% Video + Border Canvas)")
            self.enable_box_frame_var.set(False)
            self.box_border_color_var.set("White (সাদা - ছবির মতো)")
            self.box_border_width_var.set("6px (রিলস স্ট্যান্ডার্ড)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="৯৫% ভিডিও + চারদিকে বর্ডার ও পেছনের ব্লার ক্যানভাস (রিলস ও শর্টসের জন্য আদর্শ)"
            )
            self._on_box_frame_toggle()

        elif preset_key == "frame_box":
            self.enable_box_frame_var.set(True)
            self.speed_var.set("1.03 (Reels Rec)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Reels Blur (95% Video + Border Canvas)")
            self.box_scale_var.set("82% (ছবির মতো - Recommended)")
            self.box_fit_mode_var.set("Square 1:1 Box (চারকোনা - ছবির মতো)")
            self.box_border_color_var.set("White (সাদা - ছবির মতো)")
            self.box_border_width_var.set("8px (ছবির মতো)")
            self.bg_video_pos_var.set("lower_center (৫৩% - ছবির মতো নিচে)")
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="ছবির মতো লেআউট: ৮২% সাইজের স্কয়ার বক্স + ৮px সাদা ফ্রেম বর্ডার + ব্যাকগ্রাউন্ড"
            )
            self._on_box_frame_toggle()

        elif preset_key == "vertical_9_16":
            self.speed_var.set("1.02 (Micro)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("9:16 Vertical (Blur Canvas - 100% Full Width)")
            self.enable_box_frame_var.set(False)
            self.color_grade_var.set(True)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.10 (+10%)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="100% Full Width 9:16 Vertical (1080x1920) with blurred ambient canvas"
            )
            self._on_box_frame_toggle()

        elif preset_key == "heavy_remix":
            self.speed_var.set("1.05 (Standard)")
            self.zoom_var.set("5% (Medium)")
            self.flip_h_var.set(True)
            self.aspect_mode_var.set("Keep Original")
            self.enable_box_frame_var.set(False)
            self.color_grade_var.set(True)
            self.vignette_var.set(True)
            self.border_var.set("Gold (3px)")
            self.volume_var.set("1.15 (+15% Recommended)")
            self.anti_audio_hash_var.set(True)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="Mirror Flip + 1.05x Speed + 5% Zoom + Gold Border + Vignette (100% Hash Break)"
            )
            self._on_box_frame_toggle()

        elif preset_key == "fast_mode":
            self.speed_var.set("1.02 (Micro)")
            self.zoom_var.set("0% (None)")
            self.flip_h_var.set(False)
            self.aspect_mode_var.set("Keep Original")
            self.enable_box_frame_var.set(False)
            self.color_grade_var.set(False)
            self.vignette_var.set(False)
            self.border_var.set("None")
            self.volume_var.set("1.00 (Normal)")
            self.anti_audio_hash_var.set(False)
            self.strip_meta_var.set(True)
            self.preset_info_lbl.config(
                text="Minimal visual alteration + Speed 1.02x + Metadata Scrubbing (Super Fast)"
            )
            self._on_box_frame_toggle()

        elif preset_key == "custom":
            self.preset_info_lbl.config(text="Custom manual mode: Configure all settings as you prefer.")

    # --- FILE / FOLDER ADDITION ---

    def _add_files(self):
        filetypes = [
            ("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm *.flv *.ts *.m4v *.wmv *.3gp"),
            ("All Files", "*.*")
        ]
        paths = filedialog.askopenfilenames(title="Select Videos to Edit", filetypes=filetypes)
        if paths:
            threading.Thread(target=self._ingest_videos, args=(list(paths),), daemon=True).start()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select Video Folder")
        if folder:
            paths = []
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(SUPPORTED_EXTENSIONS):
                        paths.append(os.path.join(root, f))
            if paths:
                threading.Thread(target=self._ingest_videos, args=(paths,), daemon=True).start()
            else:
                messagebox.showinfo("No Videos", "No supported video files found in the selected folder.")

    def _ingest_videos(self, paths: list[str]):
        existing_paths = {v["path"] for v in self.videos}
        new_items = []
        for p in paths:
            if p in existing_paths:
                continue
            info = get_video_info(p)
            item = {
                "id": str(len(self.videos) + len(new_items) + 1),
                "path": p,
                "name": os.path.basename(p),
                "duration": info.get("duration", 0.0),
                "duration_str": info.get("duration_str", "00:00"),
                "resolution": info.get("resolution", "Unknown"),
                "fps": f"{info.get('fps', 30.0):.0f} fps",
                "status": "Pending",
                "size_str": "-"
            }
            new_items.append(item)

        self.root.after(0, self._append_to_tree, new_items)

    def _append_to_tree(self, items: list[dict]):
        for it in items:
            self.videos.append(it)
            self.tree.insert(
                "",
                "end",
                iid=it["path"],
                values=(
                    it["id"],
                    it["name"],
                    it["resolution"],
                    it["fps"],
                    it["duration_str"],
                    it["status"],
                    it["size_str"]
                )

            )
        self._update_stats()
        self._log(f"Added {len(items)} video(s) to the editing queue.")

    def _remove_selected(self):
        selected_iids = self.tree.selection()
        if not selected_iids:
            return
        selected_set = set(selected_iids)
        self.videos = [v for v in self.videos if v["path"] not in selected_set]
        for iid in selected_iids:
            self.tree.delete(iid)
        # Re-index
        for idx, v in enumerate(self.videos, 1):
            v["id"] = str(idx)
            self.tree.set(v["path"], "idx", str(idx))
        self._update_stats()

    def _clear_all(self):
        if self.is_processing:
            messagebox.showwarning("Busy", "Cannot clear while processing is active.")
            return
        self.videos.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._update_stats()
        self._log("Cleared video list.")

    def _update_stats(self):
        total_count = len(self.videos)
        total_sec = sum(v["duration"] for v in self.videos)
        self.stats_var.set(f"Total Videos: {total_count} | Total Duration: {format_duration(total_sec)}")

    # --- BROWSE HELPERS ---

    def _browse_output_dir(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir_var.set(folder)

    def _browse_bgm(self):
        file = filedialog.askopenfilename(
            title="Select Background Music",
            filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("All Files", "*.*")]
        )
        if file:
            self.bgm_path_var.set(file)

    def _browse_watermark(self):
        file = filedialog.askopenfilename(
            title="Select Logo/Watermark PNG",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp"), ("All Files", "*.*")]
        )
        if file:
            self.watermark_path_var.set(file)

    def _browse_custom_bg(self):
        # Auto-center video when loading custom template
        if "right" in self.bg_video_pos_x_var.get().lower():
            self.bg_video_pos_x_var.set("Center (মাঝখানে)")
        file = filedialog.askopenfilename(
            title="Select Custom Background Template (Image or Video)",
            filetypes=[
                ("All Supported Templates (Image/Video)", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.webm *.mkv *.avi"),
                ("Video Templates (*.mp4, *.mov, *.webm)", "*.mp4 *.mov *.webm *.mkv *.avi"),
                ("Image Templates (*.png, *.jpg, *.webp)", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All Files", "*.*")
            ]
        )
        if file:
            self.custom_bg_path_var.set(file)
            kind = "Video" if is_video_file(file) else "Image"
            self._log(f"Custom background {kind.lower()} template selected: {os.path.basename(file)}")

    def _open_output_folder(self):
        out_dir = self.output_dir_var.get().strip()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        if os.name == 'nt':
            os.startfile(out_dir)
        else:
            subprocess.run(["xdg-open", out_dir])

    # --- LOGGING & STATUS ---

    def _log(self, msg: str):
        self.log_queue.put(msg)

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{timestamp}] {msg}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(100, self._poll_log_queue)

    def _check_ffmpeg_startup(self):
        res = check_ffmpeg()
        if not res["all_ready"]:
            self._log("[WARNING] FFmpeg or FFprobe was not detected in PATH!")
            messagebox.showwarning(
                "FFmpeg Warning",
                "FFmpeg or FFprobe was not found in system PATH. Video editing may fail."
            )
        else:
            self._log("[Ready] FFmpeg & FFprobe detected and fully operational.")

    # --- PARSE CONFIGURATION ---

    def _gather_config(self) -> dict:
        # Speed parse
        speed_raw = self.speed_var.get().split()[0]
        try:
            speed = float(speed_raw)
        except Exception:
            speed = 1.03

        # Zoom parse
        zoom_raw = self.zoom_var.get().split("%")[0]
        try:
            zoom_pct = float(zoom_raw)
        except Exception:
            zoom_pct = 3.0

        # Aspect mode mapping
        aspect_raw = self.aspect_mode_var.get()
        aspect_map = {
            "Keep Original": "keep",
            "9:16 Reels Blur (95% Video + Border Canvas)": "9_16_blur_95",
            "9:16 Vertical (Blur Canvas - 95% Video + Border)": "9_16_blur_95",
            "9:16 Vertical (Blur Canvas - 100% Full Width)": "9_16_blur",
            "9:16 Vertical (Blur Canvas)": "9_16_blur",
            "9:16 Vertical (Center Crop)": "9_16_crop",
            "1:1 Square (Blur Canvas)": "1_1_blur",
            "16:9 Landscape (Blur Canvas)": "16_9_blur"
        }
        aspect_mode = aspect_map.get(aspect_raw, "9_16_blur_95")

        # Border mapping
        border_raw = self.border_var.get()
        border_map = {
            "None": "none",
            "White (3px)": "white_3px",
            "Black (3px)": "black_3px",
            "Gold (3px)": "gold_3px",
            "White (5px)": "white_5px",
            "Gold (5px)": "gold_5px"
        }
        border = border_map.get(border_raw, "none")

        # Volume parse
        vol_raw = self.volume_var.get().split()[0]
        try:
            volume = float(vol_raw)
        except Exception:
            volume = 1.15

        # BGM volume parse
        bgm_vol_raw = self.bgm_volume_var.get().split("%")[0]
        try:
            bgm_volume = float(bgm_vol_raw) / 100.0
        except Exception:
            bgm_volume = 0.10

        # CRF parse
        crf_raw = self.crf_var.get().split()[0]
        try:
            crf = int(crf_raw)
        except Exception:
            crf = 21

        # Box Frame scale parse
        box_scale_raw = self.box_scale_var.get().split("%")[0].strip()
        try:
            box_scale = float(box_scale_raw) / 100.0
        except Exception:
            box_scale = 0.95

        # Height scale parse
        box_h_raw = self.box_height_scale_var.get().split("%")[0].strip()
        try:
            box_height_scale = float(box_h_raw) / 100.0
        except Exception:
            box_height_scale = 0.85

        # Horizontal (X) position parse
        pos_x_raw = self.bg_video_pos_x_var.get().lower()
        if "right" in pos_x_raw and "flush" in pos_x_raw:
            bg_video_pos_x = "right_flush"
        elif "right" in pos_x_raw or "ডান" in pos_x_raw:
            bg_video_pos_x = "right"
        elif "left" in pos_x_raw and "flush" in pos_x_raw:
            bg_video_pos_x = "left_flush"
        elif "left" in pos_x_raw or "বাম" in pos_x_raw:
            bg_video_pos_x = "left"
        elif "custom" in pos_x_raw:
            bg_video_pos_x = "custom"
        else:
            bg_video_pos_x = "center"

        # Fit mode parse
        fit_raw = self.box_fit_mode_var.get()
        if "1:1" in fit_raw and ("full" in fit_raw.lower() or "fit" in fit_raw.lower() or "পুরু" in fit_raw or "পুরো" in fit_raw or "নো" in fit_raw):
            box_fit_mode = "1_1_fit"
        elif "Fill" in fit_raw or "ফিল" in fit_raw:
            box_fit_mode = "crop_fill"
        elif "Square" in fit_raw or "1:1" in fit_raw:
            box_fit_mode = "crop_1_1"
        elif "4:5" in fit_raw:
            box_fit_mode = "crop_4_5"
        else:
            box_fit_mode = "fit"

        # Box border color parse
        border_col_raw = self.box_border_color_var.get().lower()
        if "white" in border_col_raw or "সাদা" in border_col_raw:
            box_border_color = "white"
        elif "gold" in border_col_raw or "সোনালী" in border_col_raw:
            box_border_color = "gold"
        elif "black" in border_col_raw or "কালো" in border_col_raw:
            box_border_color = "black"
        elif "red" in border_col_raw or "লাল" in border_col_raw:
            box_border_color = "red"
        elif "cyan" in border_col_raw or "আকাশি" in border_col_raw:
            box_border_color = "cyan"
        else:
            box_border_color = "none"

        # Box border width parse
        b_width_raw = self.box_border_width_var.get().split("px")[0].strip()
        try:
            box_border_width = int(b_width_raw)
        except Exception:
            box_border_width = 0

        bg_pos_raw = self.bg_video_pos_var.get().split()[0]

        # Split parsing
        sp_layout_raw = self.split_layout_var.get()
        if "Bottom Video" in sp_layout_raw or "নিচে ভিডিও" in sp_layout_raw:
            split_layout = "bottom_video"
        elif "50/50" in sp_layout_raw:
            split_layout = "split_50_50"
        else:
            split_layout = "top_video"

        sp_bg_raw = "blur" if "Blur" in self.split_bg_style_var.get() else "black"

        try:
            split_v_h = float(self.split_video_h_var.get().split("%")[0].strip()) / 100.0
        except Exception:
            split_v_h = 0.50

        try:
            split_m_h = float(self.split_meme_h_var.get().split("%")[0].strip()) / 100.0
        except Exception:
            split_m_h = 0.40

        try:
            split_b_w = float(self.split_box_w_var.get().split("%")[0].strip()) / 100.0
        except Exception:
            split_b_w = 0.96

        return {
            "enable_top_bottom_split": self.enable_split_var.get(),
            "split_meme_path": self.split_meme_path_var.get().strip(),
            "split_layout": split_layout,
            "split_bg_style": "custom" if ("custom" in self.split_bg_style_var.get().lower() or "কাস্টম" in self.split_bg_style_var.get()) else ("blur" if "Blur" in self.split_bg_style_var.get() else "black"),
            "split_custom_bg_path": self.split_custom_bg_var.get().strip(),
            "split_video_h_scale": split_v_h,
            "split_meme_h_scale": split_m_h,
            "split_box_w_scale": split_b_w,
            "split_video_fit": "crop_fill" if ("Fill" in self.split_video_fit_var.get() or "বক্স ফিল" in self.split_video_fit_var.get() or "Manual" in self.split_video_fit_var.get() or "ম্যানুয়াল" in self.split_video_fit_var.get() or "Top" in self.split_video_fit_var.get() or "Bottom" in self.split_video_fit_var.get() or "Center" in self.split_video_fit_var.get()) else "fit",
            "split_crop_align": "manual" if ("Manual" in self.split_crop_align_var.get() or "ম্যানুয়াল" in self.split_crop_align_var.get() or "Manual" in self.split_video_fit_var.get() or "ম্যানুয়াল" in self.split_video_fit_var.get()) else ("top" if ("Top" in (self.split_crop_align_var.get() + " " + self.split_video_fit_var.get()) or "ওপর" in (self.split_crop_align_var.get() + " " + self.split_video_fit_var.get())) else ("bottom" if ("Bottom" in (self.split_crop_align_var.get() + " " + self.split_video_fit_var.get()) or "নিচ" in (self.split_crop_align_var.get() + " " + self.split_video_fit_var.get())) else "center")),
            "split_crop_y_pct": int(self.split_crop_y_pct_var.get()),
            "crop_top_pct": float(self.crop_top_pct_var.get()),
            "crop_bot_pct": float(self.crop_bot_pct_var.get()),
            "crop_left_pct": float(self.crop_left_pct_var.get()),
            "crop_right_pct": float(self.crop_right_pct_var.get()),
            "split_border_color": "white" if ("white" in self.split_border_color_var.get().lower() or "সাদা" in self.split_border_color_var.get()) else ("gold" if ("gold" in self.split_border_color_var.get().lower() or "সোনালী" in self.split_border_color_var.get()) else ("black" if ("black" in self.split_border_color_var.get().lower() or "কালো" in self.split_border_color_var.get()) else ("red" if ("red" in self.split_border_color_var.get().lower() or "লাল" in self.split_border_color_var.get()) else ("cyan" if ("cyan" in self.split_border_color_var.get().lower() or "আকাশি" in self.split_border_color_var.get()) else "none")))),
            "split_border_width": int(self.split_border_width_var.get().split("px")[0].strip()) if "px" in self.split_border_width_var.get() else 0,
            "split_border_target": "between" if ("between" in self.split_border_target_var.get().lower() or "ডিভাইডার" in self.split_border_target_var.get()) else ("both" if ("both" in self.split_border_target_var.get().lower() or "দুটো" in self.split_border_target_var.get()) else "video_only"),
            "split_audio_source": "mute" if ("mute" in self.split_audio_source_var.get().lower() or "মিউট" in self.split_audio_source_var.get()) else ("meme" if ("meme" in self.split_audio_source_var.get().lower() or "মেম" in self.split_audio_source_var.get()) else ("mix" if ("mix" in self.split_audio_source_var.get().lower() or "মিক্স" in self.split_audio_source_var.get()) else "reel")),
            "speed": speed,
            "zoom_percent": zoom_pct,
            "flip_h": self.flip_h_var.get(),
            "aspect_mode": aspect_mode,
            "custom_bg_path": self.custom_bg_path_var.get().strip(),
            "enable_box_frame": self.enable_box_frame_var.get(),
            "bg_video_mute": self.bg_template_mute_var.get(),
            "bg_video_pos": bg_pos_raw,
            "bg_video_pos_x": bg_video_pos_x,
            "box_scale": box_scale,
            "box_height_scale": box_height_scale,
            "box_fit_mode": box_fit_mode,
            "box_crop_y_pct": int(self.box_crop_y_pct_var.get()),
            "box_crop_x_pct": int(self.box_crop_x_pct_var.get()),
            "box_border_color": box_border_color,
            "box_border_width": box_border_width,
            "custom_x": int(self.box_custom_x_var.get()) if (self.box_custom_x_var.get() and self.box_custom_x_var.get().lstrip("-").isdigit()) else (0 if "left" in pos_x_raw else (1080 - int(1080 * box_scale)) // 2),
            "custom_y": int(self.box_custom_y_var.get()) if (self.box_custom_y_var.get() and self.box_custom_y_var.get().lstrip("-").isdigit()) else (648 if "galaxy_hook" in bg_pos_raw else int(1920 * 0.53)),
            "color_grade": self.color_grade_var.get(),
            "vignette": self.vignette_var.get(),
            "border": border,
            "volume_boost": volume,
            "anti_audio_hash": self.anti_audio_hash_var.get(),
            "bgm_path": self.bgm_path_var.get().strip(),
            "bgm_volume": bgm_volume,
            "text_overlay": self.text_overlay_var.get().strip(),
            "text_position": self.text_position_var.get(),
            "text_color": "yellow" if ("yellow" in self.text_color_var.get().lower() or "হলুদ" in self.text_color_var.get()) else ("white" if ("white" in self.text_color_var.get().lower() or "সাদা" in self.text_color_var.get()) else ("red" if ("red" in self.text_color_var.get().lower() or "লাল" in self.text_color_var.get()) else ("cyan" if ("cyan" in self.text_color_var.get().lower() or "আকাশি" in self.text_color_var.get()) else ("green" if ("green" in self.text_color_var.get().lower() or "সবুজ" in self.text_color_var.get()) else ("black" if ("black" in self.text_color_var.get().lower() or "কালো" in self.text_color_var.get()) else "yellow"))))),
            "text_fontsize": int(self.text_fontsize_var.get().split("px")[0].split()[0].strip()) if "px" in self.text_fontsize_var.get() else 54,
            "text_box_bg": "none" if ("none" in self.text_box_bg_var.get().lower() or "ছাড়া" in self.text_box_bg_var.get()) else ("white_box" if ("white" in self.text_box_bg_var.get().lower() or "সাদা" in self.text_box_bg_var.get()) else ("red_box" if ("red" in self.text_box_bg_var.get().lower() or "লাল" in self.text_box_bg_var.get()) else "black_box")),
            "text_custom_x": self.text_custom_x_var.get().strip() if self.text_custom_x_var.get().strip() else None,
            "text_custom_y": self.text_custom_y_var.get().strip() if self.text_custom_y_var.get().strip() else None,
            "split_custom_y": self.split_custom_y_var.get().strip() if self.split_custom_y_var.get().strip() else None,
            "watermark_path": self.watermark_path_var.get().strip(),
            "watermark_pos": self.watermark_pos_var.get(),
            "strip_metadata": self.strip_meta_var.get(),
            "crf": crf,
            "preset": "ultrafast" if "ultra" in self.preset_speed_var.get().lower() else ("veryfast" if "very" in self.preset_speed_var.get().lower() else ("medium" if "medium" in self.preset_speed_var.get().lower() else "fast"))
        }

    # --- PROCESSING WORKFLOW ---

    def _start_processing(self):
        if not self.videos:
            messagebox.showinfo("Queue Empty", "Please add at least one video to process.")
            return

        out_dir = self.output_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Missing Output", "Please choose an output directory.")
            return

        os.makedirs(out_dir, exist_ok=True)

        self.is_processing = True
        self.cancel_requested = False
        self.btn_start.config(state="disabled", bg="#94a3b8")
        if hasattr(self, 'btn_start_top'):
            self.btn_start_top.config(state="disabled", bg="#94a3b8")
        self.btn_cancel.config(state="normal", bg="#dc3545")

        config = self._gather_config()
        threading.Thread(target=self._worker_loop, args=(config,), daemon=True).start()

    def _cancel_processing(self):
        if self.is_processing:
            self.cancel_requested = True
            self._log("Cancel requested... stopping current task.")
            self.overall_status_var.set("Cancelling...")

    def _worker_loop(self, config: dict):
        total = len(self.videos)
        out_dir = self.output_dir_var.get().strip()
        prefix = self.output_prefix_var.get().strip()
        suffix = self.output_suffix_var.get().strip()

        self._log(f"Starting bulk processing of {total} video(s)...")

        success_count = 0
        fail_count = 0

        for i, video_item in enumerate(self.videos, 1):
            if self.cancel_requested:
                break

            in_path = video_item["path"]
            base_name, _ = os.path.splitext(os.path.basename(in_path))
            out_name = f"{prefix}{base_name}{suffix}.mp4"
            out_path = os.path.join(out_dir, out_name)

            # Collision prevention: avoid writing to the exact same file as input
            if os.path.abspath(out_path).lower() == os.path.abspath(in_path).lower():
                out_name = f"{prefix}{base_name}{suffix}_edited.mp4"
                out_path = os.path.join(out_dir, out_name)

            self.root.after(0, self._update_item_status, in_path, "Encoding: 0%", "-")
            self.root.after(0, self._set_overall_progress, i, total, f"Video {i}/{total}: {video_item['name']}")

            def prog_cb(pct, text):
                self.root.after(0, self._set_current_progress, pct, f"{video_item['name']} ({pct:.0f}%)")
                self.root.after(0, self._update_item_status, in_path, f"Encoding ({pct:.0f}%)", "-")

            def cancel_check():
                return self.cancel_requested

            res = process_single_video(in_path, out_path, config, prog_cb, cancel_check)

            if res["success"]:
                success_count += 1
                self._log(f"✅ Finished [{i}/{total}]: {out_name} ({res['size_str']})")
                self.root.after(0, self._update_item_status, in_path, "✅ Done", res["size_str"])
            else:
                fail_count += 1
                err = res.get("error", "Error")
                self.last_error = err
                self._log(f"❌ Failed [{i}/{total}]: {video_item['name']} -> {err}")
                self.root.after(0, self._update_item_status, in_path, "❌ Failed", "-")

        self.root.after(0, self._finish_processing, success_count, fail_count, total)

    def _set_current_progress(self, pct: float, status_text: str):
        self.current_prog_bar["value"] = pct
        self.current_video_status_var.set(status_text)

    def _set_overall_progress(self, current: int, total: int, status_text: str):
        pct = (current / total) * 100.0 if total > 0 else 0.0
        self.overall_prog_bar["value"] = pct
        self.overall_status_var.set(status_text)

    def _update_item_status(self, path: str, status: str, size_str: str):
        if self.tree.exists(path):
            self.tree.set(path, "status", status)
            if size_str != "-":
                self.tree.set(path, "size", size_str)

    def _finish_processing(self, success: int, fail: int, total: int):
        self.is_processing = False
        self.btn_start.config(state="normal", bg="#0d6efd")
        if hasattr(self, 'btn_start_top'):
            self.btn_start_top.config(state="normal", bg="#16a34a")
        self.btn_cancel.config(state="disabled", bg="#94a3b8")
        self.current_prog_bar["value"] = 100.0
        self.overall_prog_bar["value"] = 100.0

        if self.cancel_requested:
            self.overall_status_var.set(f"Stopped by user. Completed: {success}/{total}")
            self._log(f"Processing cancelled. Completed: {success}, Failed: {fail}")
            messagebox.showinfo("Cancelled", f"Process was stopped.\nSuccessfully edited: {success} video(s)")
        else:
            self.overall_status_var.set(f"Completed! {success} edited, {fail} failed.")
            self._log(f"Batch complete: {success} succeeded, {fail} failed.")
            err_info = f"\n\n❌ Error Details:\n{getattr(self, 'last_error', '')[:400]}" if fail > 0 else ""
            messagebox.showinfo(
                "Batch Complete",
                f"🎉 Bulk Video Editing Complete!\n\n"
                f"✅ Successful: {success}\n"
                f"❌ Failed: {fail}"
                f"{err_info}\n\n"
                f"Output Location:\n{self.output_dir_var.get()}"
            )

def main():
    root = tk.Tk()
    app = BulkVideoEditorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
