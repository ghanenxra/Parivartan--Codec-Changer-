"""
Parivartan — Video Transcoder (H.265 ↔ H.264)
A modern, dark-themed desktop tool powered by FFmpeg & FFprobe.
"""
import sys, os, re, json, time, subprocess, logging
from pathlib import Path
from datetime import timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QFileDialog,
    QMessageBox, QDialog, QScrollArea, QFrame, QGridLayout, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QUrl, QTimer, QPropertyAnimation,
    QEasingCurve
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QFont, QDesktopServices, QDragEnterEvent, QDropEvent,
    QColor, QPalette, QFontDatabase
)

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ASSETS    = BASE_DIR / "assets"
FFMPEG    = ASSETS / "ffmpeg.exe"
FFPROBE   = ASSETS / "ffprobe.exe"

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    filename=BASE_DIR / "transcoder.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger("Parivartan")

# ── Colour palette ────────────────────────────────────────────────────
BG       = "#0d0d0d"
PANEL    = "#161616"
PANEL2   = "#1e1e1e"
ACCENT   = "#4CAF50"
ACCENT_H = "#66BB6A"
ACCENT_D = "#388E3C"
TEXT     = "#e0e0e0"
TEXT2    = "#9e9e9e"
BORDER   = "#2a2a2a"
RED      = "#ef5350"
YELLOW   = "#FFB74D"

# ── Global stylesheet ────────────────────────────────────────────────
STYLESHEET = f"""
QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; }}
QLabel {{ color: {TEXT}; }}

/* ── Panels ──────────────────────────────────── */
QFrame#panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ── Buttons ─────────────────────────────────── */
QPushButton {{
    background: {PANEL2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{ background: #2c2c2c; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT_D}; }}

QPushButton#accent {{
    background: {ACCENT};
    color: #fff;
    border: none;
    font-size: 14px;
    padding: 10px 28px;
    border-radius: 10px;
}}
QPushButton#accent:hover {{ background: {ACCENT_H}; }}
QPushButton#accent:pressed {{ background: {ACCENT_D}; }}
QPushButton#accent:disabled {{ background: #2a2a2a; color: #555; }}

QPushButton#link {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: {TEXT2};
}}
QPushButton#link:hover {{ color: {ACCENT}; border-color: {ACCENT}; }}

/* ── ComboBox ────────────────────────────────── */
QComboBox {{
    background: {PANEL2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 160px;
}}
QComboBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    color: {TEXT};
    selection-background-color: {ACCENT_D};
    border: 1px solid {BORDER};
    border-radius: 6px;
    outline: none;
}}

/* ── Progress bar ────────────────────────────── */
QProgressBar {{
    background: {PANEL2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    text-align: center;
    color: {TEXT};
    font-size: 12px;
    font-weight: 600;
    height: 26px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {ACCENT_D}, stop:1 {ACCENT});
    border-radius: 7px;
}}

/* ── ScrollArea ──────────────────────────────── */
QScrollArea {{ border: none; }}
QScrollBar:vertical {{
    background: {PANEL}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #444; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


# ══════════════════════════════════════════════════════════════════════
#  BACKEND — GPU detection, FFprobe, FFmpeg workers
# ══════════════════════════════════════════════════════════════════════

def detect_gpu() -> bool:
    """Return True if FFmpeg can use NVIDIA NVENC."""
    try:
        r = subprocess.run(
            [str(FFMPEG), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return "h264_nvenc" in r.stdout
    except Exception:
        return False


def probe_file(path: str) -> dict | None:
    """Run FFprobe and return parsed media info dict."""
    cmd = [
        str(FFPROBE), "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return json.loads(r.stdout)
    except Exception as e:
        log.error("FFprobe error: %s", e)
        return None


def extract_thumbnail(video: str, out: str) -> bool:
    """Save a single thumbnail frame from the video."""
    cmd = [
        str(FFMPEG), "-y", "-i", video,
        "-vf", "thumbnail,scale=320:-1",
        "-frames:v", "1", out,
    ]
    try:
        subprocess.run(
            cmd, capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return os.path.isfile(out)
    except Exception:
        return False


class ConvertWorker(QThread):
    """Run FFmpeg conversion in a background thread, emitting progress."""
    progress   = pyqtSignal(float)          # 0‑100
    speed      = pyqtSignal(str)            # e.g. "2.1x"
    eta        = pyqtSignal(str)            # remaining time string
    finished   = pyqtSignal(bool, str)      # success, message
    log_line   = pyqtSignal(str)

    def __init__(self, cmd: list[str], duration: float):
        super().__init__()
        self.cmd = cmd
        self.duration = duration  # total duration in seconds
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        log.info("FFmpeg cmd: %s", " ".join(self.cmd))
        start = time.time()
        try:
            proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time_re = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
            speed_re = re.compile(r"speed=\s*([\d.]+)x")

            for line in proc.stdout:
                if self._cancel:
                    proc.kill()
                    self.finished.emit(False, "Cancelled by user")
                    return
                self.log_line.emit(line.strip())
                m = time_re.search(line)
                if m and self.duration > 0:
                    cur = int(m[1])*3600 + int(m[2])*60 + int(m[3]) + int(m[4])/100
                    pct = min(cur / self.duration * 100, 100)
                    self.progress.emit(pct)
                    elapsed = time.time() - start
                    if pct > 0:
                        remaining = elapsed / pct * (100 - pct)
                        self.eta.emit(str(timedelta(seconds=int(remaining))))
                s = speed_re.search(line)
                if s:
                    self.speed.emit(f"{s[1]}x")

            proc.wait()
            if proc.returncode == 0:
                self.progress.emit(100)
                self.finished.emit(True, "Conversion complete!")
            else:
                self.finished.emit(False, f"FFmpeg exited with code {proc.returncode}")
        except Exception as e:
            log.exception("Conversion error")
            self.finished.emit(False, str(e))


# ══════════════════════════════════════════════════════════════════════
#  DONATE DIALOG (Buy Me a Coffee popup)
# ══════════════════════════════════════════════════════════════════════

class DonateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Support the Developer")
        self.setFixedSize(380, 440)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; }}
            QLabel {{ color: {TEXT}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 24)
        layout.setSpacing(14)

        # Title
        t = QLabel("☕  Buy Me a Coffee")
        t.setStyleSheet(f"font-size:20px;font-weight:800;color:{TEXT};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t)

        sub = QLabel("Your support keeps this project alive!")
        sub.setStyleSheet(f"font-size:12px;color:{TEXT2};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(4)

        # QR Code
        qr_path = ASSETS / "qr.png"
        if qr_path.exists():
            qr = QLabel()
            pm = QPixmap(str(qr_path)).scaled(
                200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            qr.setPixmap(pm)
            qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr.setStyleSheet(f"background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:12px;")
            layout.addWidget(qr, alignment=Qt.AlignmentFlag.AlignCenter)

        scan_hint = QLabel("Scan the QR code or click below")
        scan_hint.setStyleSheet(f"font-size:11px;color:{TEXT2};")
        scan_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(scan_hint)

        layout.addSpacing(4)

        # PayPal button
        pp = QPushButton("💳  Open PayPal  →  @ghanenxra")
        pp.setObjectName("accent")
        pp.setCursor(Qt.CursorShape.PointingHandCursor)
        pp.setStyleSheet(pp.styleSheet() + "font-size:14px;padding:12px 20px;")
        pp.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.paypal.com/paypalme/ghanenxra")))
        layout.addWidget(pp)

        layout.addStretch()


# ══════════════════════════════════════════════════════════════════════
#  METADATA DIALOG
# ══════════════════════════════════════════════════════════════════════

class MetadataDialog(QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detailed Metadata")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; }}
            QLabel {{ color: {TEXT}; font-size: 13px; }}
            QLabel#heading {{ color: {ACCENT}; font-size: 15px; font-weight: 700; }}
            QLabel#key {{ color: {TEXT2}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QVBoxLayout(container)
        grid.setSpacing(4)

        def heading(t):
            l = QLabel(t); l.setObjectName("heading"); grid.addWidget(l)

        def row(k, v):
            h = QHBoxLayout()
            kl = QLabel(k); kl.setObjectName("key"); kl.setFixedWidth(160)
            vl = QLabel(str(v)); vl.setWordWrap(True)
            h.addWidget(kl); h.addWidget(vl, 1)
            grid.addLayout(h)

        # Format section
        fmt = info.get("format", {})
        heading("📄  Format")
        row("Format", fmt.get("format_long_name", "N/A"))
        row("Duration", f'{float(fmt.get("duration", 0)):.2f} s')
        row("Size", f'{int(fmt.get("size", 0)) / 1048576:.2f} MB')
        row("Bit Rate", f'{int(fmt.get("bit_rate", 0)) / 1000:.0f} kbps')

        # Streams
        for i, s in enumerate(info.get("streams", [])):
            heading(f"🎞  Stream #{i}  ({s.get('codec_type', '').title()})")
            row("Codec", f"{s.get('codec_long_name', 'N/A')} ({s.get('codec_name', '')})")
            if s.get("width"):
                row("Resolution", f"{s['width']}×{s['height']}")
            if s.get("r_frame_rate"):
                row("Frame Rate", s["r_frame_rate"])
            if s.get("pix_fmt"):
                row("Pixel Format", s["pix_fmt"])
            if s.get("sample_rate"):
                row("Sample Rate", f"{s['sample_rate']} Hz")
            if s.get("channels"):
                row("Channels", s["channels"])
            if s.get("bit_rate"):
                row("Bit Rate", f"{int(s['bit_rate'])/1000:.0f} kbps")
            if s.get("profile"):
                row("Profile", s["profile"])

        # Tags
        tags = fmt.get("tags", {})
        if tags:
            heading("🏷  Tags")
            for k, v in tags.items():
                row(k.replace("_", " ").title(), v)

        grid.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        close = QPushButton("Close")
        close.setObjectName("accent")
        close.setFixedWidth(120)
        close.clicked.connect(self.close)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignCenter)


# ══════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parivartan — Video Transcoder")
        self.setMinimumSize(960, 720)
        self.resize(1060, 780)
        icon_path = ASSETS / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.gpu_available = detect_gpu()
        self.gpu_enabled = self.gpu_available   # user-togglable
        self.file_path: str | None = None
        self.media_info: dict | None = None
        self.worker: ConvertWorker | None = None
        self._start_time = 0.0

        self.setAcceptDrops(True)
        self._build_ui()
        log.info("App started  GPU=%s", self.gpu_available)

    # ── drag & drop ──────────────────────────────────────────────────
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith((".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts")):
                self._load_file(p)
                return

    # ── helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _make_panel():
        f = QFrame(); f.setObjectName("panel"); return f

    @staticmethod
    def _section_label(text, size=11, color=TEXT2):
        l = QLabel(text)
        l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:600;letter-spacing:0.5px;")
        return l

    def _info_value(self, key):
        l = QLabel("—")
        l.setStyleSheet(f"color:{TEXT};font-size:13px;")
        l.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        setattr(self, f"_iv_{key}", l)
        return l

    # ══════════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════════
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 20, 28, 16)
        outer.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────
        hdr = QVBoxLayout(); hdr.setSpacing(2)

        # Load Cormorant Garamond for the app brand name
        font_path = ASSETS / "CormorantGaramond-Bold.ttf"
        cg_family = "Cormorant Garamond"
        if font_path.exists():
            fid = QFontDatabase.addApplicationFont(str(font_path))
            families = QFontDatabase.applicationFontFamilies(fid)
            if families:
                cg_family = families[0]

        app_name = QLabel("Parivartan")
        app_name.setFont(QFont(cg_family, 34, QFont.Weight.Bold))
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet(f"color:{ACCENT};letter-spacing:1px;")
        hdr.addWidget(app_name)

        title = QLabel("Video Transcoder")
        title.setStyleSheet(f"font-size:18px;font-weight:700;color:{TEXT};letter-spacing:-0.3px;")
        sub = QLabel("H.265 ↔ H.264 Converter")
        sub.setStyleSheet(f"font-size:12px;color:{TEXT2};")
        hdr.addWidget(title)
        hdr.addWidget(sub)
        hdr.addSpacing(4)

        # GPU / CPU toggle row
        gpu_row = QHBoxLayout()
        gpu_row.setSpacing(8)
        self.gpu_status = QLabel()
        self._update_gpu_label()
        gpu_row.addWidget(self.gpu_status)

        self.gpu_toggle = QPushButton("Use CPU Instead" if self.gpu_available else "GPU Not Available")
        self.gpu_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gpu_toggle.setEnabled(self.gpu_available)
        self.gpu_toggle.setStyleSheet(
            f"font-size:11px;font-weight:600;padding:4px 12px;border-radius:6px;"
            f"background:{PANEL2};color:{TEXT2};border:1px solid {BORDER};"
        )
        self.gpu_toggle.clicked.connect(self._toggle_gpu)
        gpu_row.addWidget(self.gpu_toggle)
        gpu_row.addStretch()
        hdr.addLayout(gpu_row)
        outer.addLayout(hdr)

        # ── Center panels ────────────────────────────────────────────
        center = QHBoxLayout(); center.setSpacing(14)

        # LEFT — file import
        lp = self._make_panel()
        ll = QVBoxLayout(lp); ll.setContentsMargins(18, 18, 18, 18); ll.setSpacing(10)
        ll.addWidget(self._section_label("INPUT FILE"))
        import_btn = QPushButton("📂  Import Video")
        import_btn.setObjectName("accent")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._open_file)
        ll.addWidget(import_btn)

        drop_label = QLabel("or drag && drop a video here")
        drop_label.setStyleSheet(f"color:{TEXT2};font-size:11px;")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(drop_label)

        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(280, 158)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            f"background:{BG};border:1px solid {BORDER};border-radius:8px;"
            f"color:{TEXT2};font-size:11px;"
        )
        self.thumb_label.setText("No file loaded")
        ll.addWidget(self.thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)

        ll.addWidget(self._section_label("FILE DETAILS"))
        for key in ("name", "size"):
            ll.addWidget(self._info_value(key))
        ll.addStretch()
        center.addWidget(lp, 4)

        # RIGHT — media info
        rp = self._make_panel()
        rl = QVBoxLayout(rp); rl.setContentsMargins(18, 18, 18, 18); rl.setSpacing(8)
        rl.addWidget(self._section_label("VIDEO INFO"))
        for key in ("codec", "resolution", "fps", "duration", "audio"):
            row = QHBoxLayout()
            kl = QLabel(key.upper())
            kl.setFixedWidth(90)
            kl.setStyleSheet(f"color:{TEXT2};font-size:12px;font-weight:600;")
            row.addWidget(kl)
            row.addWidget(self._info_value(key), 1)
            rl.addLayout(row)

        more_btn = QPushButton("Show More ▸")
        more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        more_btn.clicked.connect(self._show_metadata)
        rl.addWidget(more_btn)
        rl.addStretch()
        center.addWidget(rp, 5)

        outer.addLayout(center, 1)

        # ── Conversion settings ──────────────────────────────────────
        sp = self._make_panel()
        sl = QVBoxLayout(sp); sl.setContentsMargins(18, 14, 18, 14); sl.setSpacing(10)
        sl.addWidget(self._section_label("CONVERSION SETTINGS"))

        row1 = QHBoxLayout(); row1.setSpacing(14)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["Convert to H.264 (AVC)", "Convert to H.265 (HEVC)"])
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Original (Max Quality, Large Size)",
            "Balanced (Recommended)",
            "Compressed (Smaller Size)",
        ])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.currentIndexChanged.connect(self._quality_changed)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "MOV", "MKV"])

        for label_text, combo in [
            ("Codec", self.codec_combo),
            ("Quality", self.quality_combo),
            ("Format", self.format_combo),
        ]:
            v = QVBoxLayout(); v.setSpacing(4)
            v.addWidget(self._section_label(label_text.upper(), 10))
            v.addWidget(combo)
            row1.addLayout(v, 1)

        # Output folder
        v = QVBoxLayout(); v.setSpacing(4)
        v.addWidget(self._section_label("OUTPUT FOLDER", 10))
        self.out_btn = QPushButton("📁  Select…")
        self.out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.out_btn.clicked.connect(self._pick_output_dir)
        v.addWidget(self.out_btn)
        row1.addLayout(v, 1)

        sl.addLayout(row1)

        # Warning label (shown conditionally)
        self.warn_label = QLabel()
        self.warn_label.setStyleSheet(
            f"color:{YELLOW};font-size:11px;font-weight:600;"
            f"padding:6px 10px;background:#2d2510;border-radius:6px;"
        )
        self.warn_label.setVisible(False)
        sl.addWidget(self.warn_label)

        outer.addWidget(sp)

        # ── Execution ────────────────────────────────────────────────
        ep = self._make_panel()
        el = QVBoxLayout(ep); el.setContentsMargins(18, 14, 18, 14); el.setSpacing(10)

        exec_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start Conversion")
        self.start_btn.setObjectName("accent")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_conversion)
        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._cancel_conversion)
        exec_row.addWidget(self.start_btn)
        exec_row.addWidget(self.cancel_btn)
        exec_row.addStretch()
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"color:{TEXT2};font-size:12px;")
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet(f"color:{TEXT2};font-size:12px;")
        self.elapsed_label = QLabel("")
        self.elapsed_label.setStyleSheet(f"color:{TEXT2};font-size:12px;")
        exec_row.addWidget(self.speed_label)
        exec_row.addWidget(self.eta_label)
        exec_row.addWidget(self.elapsed_label)
        el.addLayout(exec_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        el.addWidget(self.progress_bar)

        outer.addWidget(ep)

        # ── Timer for elapsed ────────────────────────────────────────
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed)

        # ── Footer / social ──────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(10)
        for text, url in [
            ("GitHub", "https://github.com/ghanenxra"),
            ("Discord", "https://discord.com/users/1323161662739714120"),
        ]:
            b = QPushButton(text)
            b.setObjectName("link")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            footer.addWidget(b)

        # Buy Me a Coffee → opens donate popup
        coffee_btn = QPushButton("Buy Me a Coffee ☕")
        coffee_btn.setObjectName("link")
        coffee_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        coffee_btn.clicked.connect(self._show_donate)
        footer.addWidget(coffee_btn)

        footer.addStretch()
        outer.addLayout(footer)

        # ── State ────────────────────────────────────────────────────
        self.output_dir: str | None = None

    # ══════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════════════════════════════
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video",
            "", "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.ts);;All Files (*)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self.file_path = path
        info = probe_file(path)
        if not info:
            QMessageBox.critical(self, "Error", "Failed to read file with FFprobe.")
            return
        self.media_info = info
        fmt = info.get("format", {})
        v_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
        a_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})

        name = os.path.basename(path)
        size_mb = int(fmt.get("size", 0)) / 1048576
        self._iv_name.setText(name)
        self._iv_size.setText(f"{size_mb:.2f} MB")

        codec = v_stream.get("codec_name", "N/A")
        self._iv_codec.setText(f"{codec.upper()}  ({v_stream.get('codec_long_name', '')})")
        w, h = v_stream.get("width", "?"), v_stream.get("height", "?")
        self._iv_resolution.setText(f"{w} × {h}")

        fps_str = v_stream.get("r_frame_rate", "0/1")
        try:
            n, d = map(int, fps_str.split("/"))
            fps_val = round(n / d, 2) if d else 0
        except Exception:
            fps_val = fps_str
        self._iv_fps.setText(str(fps_val))

        dur = float(fmt.get("duration", 0))
        self._iv_duration.setText(str(timedelta(seconds=int(dur))))

        a_codec = a_stream.get("codec_name", "N/A")
        a_ch = a_stream.get("channels", "?")
        self._iv_audio.setText(f"{a_codec.upper()} · {a_ch}ch")

        # Thumbnail
        thumb_file = str(BASE_DIR / ".thumb_preview.jpg")
        if extract_thumbnail(path, thumb_file):
            pm = QPixmap(thumb_file).scaled(
                280, 158, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb_label.setPixmap(pm)
        else:
            self.thumb_label.setText("Preview unavailable")

        # Auto-select output dir
        if not self.output_dir:
            self.output_dir = os.path.dirname(path)
            self.out_btn.setText(f"📁  {os.path.basename(self.output_dir)}/")

        log.info("Loaded: %s  codec=%s  %sx%s  %.1fs", name, codec, w, h, dur)

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.output_dir = d
            self.out_btn.setText(f"📁  {os.path.basename(d)}/")

    def _show_metadata(self):
        if not self.media_info:
            QMessageBox.information(self, "Info", "Load a video first.")
            return
        MetadataDialog(self.media_info, self).exec()

    def _quality_changed(self, idx):
        if idx == 0:
            self.warn_label.setText("⚠  Original quality — output may be significantly larger than input.")
            self.warn_label.setVisible(True)
        else:
            self.warn_label.setVisible(False)

    def _toggle_gpu(self):
        """Toggle between GPU (NVENC) and CPU encoding."""
        self.gpu_enabled = not self.gpu_enabled
        self._update_gpu_label()
        self.gpu_toggle.setText("Use CPU Instead" if self.gpu_enabled else "Use GPU (NVENC)")

    def _update_gpu_label(self):
        """Refresh the GPU status badge."""
        if not self.gpu_available:
            text = "⚡ GPU: Not detected — CPU fallback"
            bg, fg = "#3a1b1b", "#E57373"
        elif self.gpu_enabled:
            text = "⚡ GPU: Enabled (NVENC)"
            bg, fg = "#1b3a1b", "#81C784"
        else:
            text = "🖥  CPU: Active (GPU disabled)"
            bg, fg = "#1b2a3a", "#64B5F6"
        self.gpu_status.setStyleSheet(
            f"font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;"
            f"background:{bg};color:{fg};"
        )
        self.gpu_status.setText(text)

    def _show_donate(self):
        """Open the Buy Me a Coffee / PayPal popup."""
        DonateDialog(self).exec()

    # ── conversion ───────────────────────────────────────────────────
    def _build_cmd(self) -> list[str]:
        target_h264 = self.codec_combo.currentIndex() == 0
        qi = self.quality_combo.currentIndex()
        ext = self.format_combo.currentText().lower()
        gpu = self.gpu_enabled

        base_name = Path(self.file_path).stem
        out_path = os.path.join(self.output_dir, f"{base_name}_converted.{ext}")

        # Encoder selection
        if target_h264:
            enc = "h264_nvenc" if gpu else "libx264"
        else:
            enc = "hevc_nvenc" if gpu else "libx265"

        cmd = [str(FFMPEG), "-y", "-i", self.file_path, "-c:v", enc]

        # Quality flags
        if qi == 0:  # Original
            if gpu:
                cmd += ["-rc", "constqp", "-qp", "0"]
            else:
                cmd += ["-crf", "0"]
        elif qi == 1:  # Balanced
            if gpu:
                if target_h264:
                    cmd += ["-preset", "p7", "-rc", "vbr", "-cq", "19", "-pix_fmt", "yuv420p"]
                else:
                    cmd += ["-preset", "p5", "-cq", "24"]
            else:
                cmd += ["-crf", "19" if target_h264 else "24"]
        else:  # Compressed
            if gpu:
                cmd += ["-cq", "28"]
            else:
                cmd += ["-crf", "28"]

        cmd += ["-c:a", "copy", out_path]
        return cmd

    def _start_conversion(self):
        if not self.file_path:
            QMessageBox.warning(self, "No File", "Please import a video first.")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "No Output", "Please select an output folder.")
            return

        # Check codec compatibility
        v_stream = next(
            (s for s in self.media_info.get("streams", []) if s.get("codec_type") == "video"), {}
        )
        current_codec = v_stream.get("codec_name", "")
        target_h264 = self.codec_combo.currentIndex() == 0
        if (target_h264 and current_codec == "h264") or (not target_h264 and current_codec == "hevc"):
            QMessageBox.information(
                self, "Already Compatible",
                f"This file is already encoded in {'H.264' if target_h264 else 'H.265'}."
            )
            return

        dur = float(self.media_info.get("format", {}).get("duration", 0))
        cmd = self._build_cmd()

        self.worker = ConvertWorker(cmd, dur)
        self.worker.progress.connect(lambda v: self.progress_bar.setValue(int(v)))
        self.worker.speed.connect(lambda s: self.speed_label.setText(f"Speed: {s}"))
        self.worker.eta.connect(lambda s: self.eta_label.setText(f"ETA: {s}"))
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        self._start_time = time.time()
        self.elapsed_timer.start()

    def _cancel_conversion(self):
        if self.worker:
            self.worker.cancel()

    def _update_elapsed(self):
        e = int(time.time() - self._start_time)
        self.elapsed_label.setText(f"Elapsed: {timedelta(seconds=e)}")

    def _on_finished(self, ok: bool, msg: str):
        self.elapsed_timer.stop()
        self.start_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        if ok:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Done ✅", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
        self.speed_label.clear()
        self.eta_label.clear()
        self.elapsed_label.clear()
        log.info("Conversion %s: %s", "OK" if ok else "FAIL", msg)


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    # Dark palette base
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(BG))
    p.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Base, QColor(PANEL))
    p.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Button, QColor(PANEL2))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    app.setPalette(p)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
