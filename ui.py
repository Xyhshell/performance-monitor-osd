"""
ui.py - 用户界面（修复信号阻塞，彻底解决复选框重置）
"""
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QCheckBox, QSlider, QSpinBox, QFontComboBox,
    QColorDialog, QSystemTrayIcon, QMenu, QAction, QApplication,
    QGroupBox, QLineEdit, QComboBox, QLabel, QScrollArea, QTabWidget,
    QTextBrowser
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QFontMetrics, QPainterPath

from settings import Settings, THEME_PRESETS, THEME_NAMES
from monitor import CPUData, GPUData, FPSData

def hex_to_qcolor(h):
    if not h:
        return QColor(255, 255, 255)
    try:
        return QColor(h if h.startswith('#') else f"#{h}")
    except:
        return QColor(255, 255, 255)

def get_fps_color(fps, s):
    if fps <= 0:
        return QColor(128, 128, 128)
    elif fps >= 60:
        return hex_to_qcolor(s.colors.fps_header)
    elif fps >= 30:
        return hex_to_qcolor(s.colors.fps_1low)
    else:
        return hex_to_qcolor(s.colors.fps_value)

def fmt_val(val, fmt=".1f", unit=""):
    if val is None:
        return "N/A"
    return f"{val:{fmt}}{unit}"

# ============================================================
# OSD 窗口
# ============================================================
class OSDWindow(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._cpu_data = CPUData()
        self._gpu_data = GPUData()
        self._fps_data = FPSData()
        self._mode = None
        self._drag_offset = QPoint()
        self._fonts = {}
        self._metrics = {}
        self._fonts_dirty = True
        self._init_window()

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        ws = self._settings.window
        self.move(ws.x, ws.y)
        self.setWindowOpacity(ws.opacity)
        self._auto_size()

    def _auto_size(self):
        self._ensure_fonts()
        self.setFixedSize(self._calc_size())

    def _ensure_fonts(self):
        if not self._fonts_dirty and self._fonts:
            return
        f = self._settings.font.family if self._settings.font.family else QFont().family()
        s = self._settings.font.size
        weight = self._settings.font.weight if self._settings.font.bold else QFont.Normal
        self._fonts = {
            'label': QFont(f, s - 3, weight),
            'data': QFont(f, s - 2, weight),
            'data_b': QFont(f, s - 2, weight),
            'fps_big': QFont(f, s + 4, weight),
            'fps_label': QFont(f, s - 1, weight),
        }
        self._metrics = {k: QFontMetrics(v) for k, v in self._fonts.items()}
        self._fonts_dirty = False

    def _calc_col_width(self):
        dl = self._metrics.get('label')
        if not dl:
            self._ensure_fonts()
            dl = self._metrics['label']
        labels = ["频率", "占用率", "P-Core", "E-Core", "温度", "电压", "功耗", "显存"]
        return max(dl.horizontalAdvance(t) for t in labels)

    def _calc_size(self):
        d = self._settings.display
        dl = self._metrics.get('label')
        dm = self._metrics.get('data')
        dm_b = self._metrics.get('data_b')
        if not dl or not dm:
            self._ensure_fonts()
            dl = self._metrics['label']
            dm = self._metrics['data']
            dm_b = self._metrics['data_b']

        pad = 8
        lbl_x = pad
        gap = 6
        col_w = self._calc_col_width()
        val_x = lbl_x + col_w + gap
        max_w = 0
        y = pad
        lh = dm.height() + 2
        fm_l = self._metrics.get('fps_label', dl)
        fm_b = self._metrics.get('fps_big', dm)

        def _check_w(x, w):
            nonlocal max_w
            tw = x + w + pad
            if tw > max_w:
                max_w = tw

        def _check_line(label, value):
            _check_w(lbl_x, dl.horizontalAdvance(label))
            _check_w(val_x, dm.horizontalAdvance(value))

        if d.show_cpu:
            cpu_header_w = dm_b.horizontalAdvance("CPU") + gap + dl.horizontalAdvance(self._cpu_data.name)
            _check_w(lbl_x, cpu_header_w)
            y += lh
            if d.show_cpu_usage:
                _check_line("占用率", fmt_val(self._cpu_data.usage, ".1f", " %")); y += lh
            if d.show_cpu_freq:
                _check_line("频率", fmt_val(self._cpu_data.frequency, ".0f", " MHz")); y += lh
                if d.show_cpu_p_core and self._cpu_data.freq_p_core > 0:
                    _check_line("P-Core", f"{self._cpu_data.freq_p_core:.0f} MHz"); y += lh
                if d.show_cpu_e_core and self._cpu_data.freq_e_core > 0:
                    _check_line("E-Core", f"{self._cpu_data.freq_e_core:.0f} MHz"); y += lh
            if d.show_cpu_temp:
                _check_line("温度", fmt_val(self._cpu_data.temperature, ".1f", "°C")); y += lh
            if d.show_cpu_voltage:
                _check_line("电压", fmt_val(self._cpu_data.voltage, ".3f", " V")); y += lh
            if d.show_cpu_power:
                _check_line("功耗", fmt_val(self._cpu_data.power, ".1f", " W")); y += lh
            y += 8

        if d.show_gpu:
            gpu_name = self._settings.gpu_custom.custom_name or self._gpu_data.name
            gpu_header_w = dm_b.horizontalAdvance("GPU") + gap + dl.horizontalAdvance(gpu_name)
            _check_w(lbl_x, gpu_header_w)
            y += lh
            if d.show_gpu_usage:
                _check_line("占用率", fmt_val(self._gpu_data.usage, ".1f", " %")); y += lh
            if d.show_gpu_freq:
                _check_line("频率", fmt_val(self._gpu_data.frequency, ".0f", " MHz")); y += lh
            if d.show_gpu_temp:
                _check_line("温度", fmt_val(self._gpu_data.temperature, ".0f", "°C")); y += lh
            if d.show_gpu_voltage:
                _check_line("电压", fmt_val(self._gpu_data.voltage, ".3f", " V")); y += lh
            if d.show_gpu_power:
                _check_line("功耗", fmt_val(self._gpu_data.power, ".1f", " W")); y += lh
            if d.show_gpu_memory and self._gpu_data.memory_total > 0:
                _check_line("显存", f"{self._gpu_data.memory_used:.0f} / {self._gpu_data.memory_total:.0f} MB"); y += lh
            y += 8

        if d.show_fps:
            _check_w(lbl_x, fm_l.horizontalAdvance("FPS"))
            y += fm_l.height() + 2
            _check_w(lbl_x + 2, fm_b.horizontalAdvance(f"{self._fps_data.fps:.1f}"))
            y += fm_b.height() + 2
            if d.show_fps_1low:
                _check_w(lbl_x, dm.horizontalAdvance(f"1%Low: {self._fps_data.fps_1low:.1f}")); y += lh
            if d.show_fps_latency:
                _check_w(lbl_x, dm.horizontalAdvance(f"延迟: {self._fps_data.render_latency:.1f} ms")); y += lh

        w = max(max_w, 180)
        h = max(20, y + pad)
        return QSize(w, h)

    def update_settings(self, settings: Settings):
        self._settings = settings
        ws = settings.window
        self.move(ws.x, ws.y)
        self.setWindowOpacity(ws.opacity)
        self._fonts_dirty = True
        self._auto_size()
        self._apply_pinned(ws.pinned)
        self.update()

    def _apply_pinned(self, pinned):
        was_visible = self.isVisible()
        if pinned:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.move(self._settings.window.x, self._settings.window.y)
        self.setWindowOpacity(self._settings.window.opacity)
        if was_visible:
            self.show()

    def update_data(self, cpu, gpu, fps):
        self._cpu_data = cpu
        self._gpu_data = gpu
        self._fps_data = fps
        if not self._mode:
            new_sz = self._calc_size()
            if new_sz != self.maximumSize():
                self.setFixedSize(new_sz)
        self.update()

    def paintEvent(self, event):
        self._ensure_fonts()
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._settings.window.show_background:
            alpha = self._settings.window.background_opacity
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, alpha)))
            p.drawRoundedRect(0, 0, w, h, 8, 8)
        self._draw_v(p, w, h)
        p.end()

    # ----- 简单投影阴影（右下偏移）-----
    def _draw_text_with_shadow(self, p, x, y, text, color, font):
        p.setFont(font)
        shadow = self._settings.shadow
        if shadow.enabled:
            ox = shadow.offset_x if shadow.offset_x != 0 else 1
            oy = shadow.offset_y if shadow.offset_y != 0 else 1
            sc = hex_to_qcolor(shadow.color)
            sc.setAlpha(int(shadow.opacity * 2.55))
            p.setPen(sc)
            p.drawText(x + ox, y + oy, text)
        p.setPen(color)
        p.drawText(x, y, text)

    def _draw_v(self, p, w, h):
        pad = 8
        x = pad
        y = pad
        dl = self._fonts['label']
        df = self._fonts['data']
        db = self._fonts['data_b']
        dm_l = self._metrics['label']
        dm = self._metrics['data']
        dm_b = self._metrics['data_b']
        lh = dm.height() + 2
        c = self._settings.colors
        d = self._settings.display
        vline_x = w - pad
        col_w = self._calc_col_width()
        lbl_x = x
        val_x = lbl_x + col_w + 6
        gap = 6

        def _draw_header(label, name, header_color, name_color):
            p.setFont(db)
            self._draw_text_with_shadow(p, lbl_x, y + dm_b.ascent(), label, hex_to_qcolor(header_color), db)
            hw = dm_b.horizontalAdvance(label) + gap
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x + hw, y + dm_l.ascent(), name, hex_to_qcolor(name_color), dl)

        def _draw_line(label, value, value_color):
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x, y + dm_l.ascent(), label, hex_to_qcolor(c.label_color), dl)
            p.setFont(df)
            self._draw_text_with_shadow(p, val_x, y + dm.ascent(), value, hex_to_qcolor(value_color), df)

        def _draw_divider():
            nonlocal y
            y += 4
            p.setPen(QPen(QColor(255, 255, 255, 20), 1))
            p.drawLine(x, y, vline_x, y)
            y += 4

        if d.show_cpu:
            _draw_header("CPU", self._cpu_data.name, c.cpu_header, c.cpu_name)
            y += lh
            if d.show_cpu_usage:
                _draw_line("占用率", fmt_val(self._cpu_data.usage, ".1f", " %"), c.cpu_usage); y += lh
            if d.show_cpu_freq:
                _draw_line("频率", fmt_val(self._cpu_data.frequency, ".0f", " MHz"), c.cpu_freq); y += lh
                if d.show_cpu_p_core and self._cpu_data.freq_p_core > 0:
                    _draw_line("P-Core", f"{self._cpu_data.freq_p_core:.0f} MHz", c.cpu_p_core); y += lh
                if d.show_cpu_e_core and self._cpu_data.freq_e_core > 0:
                    _draw_line("E-Core", f"{self._cpu_data.freq_e_core:.0f} MHz", c.cpu_e_core); y += lh
            if d.show_cpu_temp:
                _draw_line("温度", fmt_val(self._cpu_data.temperature, ".1f", " °C"), c.cpu_temp); y += lh
            if d.show_cpu_voltage:
                _draw_line("电压", fmt_val(self._cpu_data.voltage, ".3f", " V"), c.cpu_voltage); y += lh
            if d.show_cpu_power:
                _draw_line("功耗", fmt_val(self._cpu_data.power, ".1f", " W"), c.cpu_power); y += lh
            _draw_divider()

        if d.show_gpu:
            gpu_name = self._settings.gpu_custom.custom_name or self._gpu_data.name
            _draw_header("GPU", gpu_name, c.gpu_header, c.gpu_name)
            y += lh
            if d.show_gpu_usage:
                _draw_line("占用率", fmt_val(self._gpu_data.usage, ".1f", " %"), c.gpu_usage); y += lh
            if d.show_gpu_freq:
                _draw_line("频率", fmt_val(self._gpu_data.frequency, ".0f", " MHz"), c.gpu_freq); y += lh
            if d.show_gpu_temp:
                _draw_line("温度", fmt_val(self._gpu_data.temperature, ".0f", " °C"), c.gpu_temp); y += lh
            if d.show_gpu_voltage:
                _draw_line("电压", fmt_val(self._gpu_data.voltage, ".3f", " V"), c.gpu_voltage); y += lh
            if d.show_gpu_power:
                _draw_line("功耗", fmt_val(self._gpu_data.power, ".1f", " W"), c.gpu_power); y += lh
            if d.show_gpu_memory and self._gpu_data.memory_total > 0:
                _draw_line("显存", f"{self._gpu_data.memory_used:.0f} / {self._gpu_data.memory_total:.0f} MB", c.gpu_memory); y += lh
            _draw_divider()

        if d.show_fps:
            fc = get_fps_color(self._fps_data.fps, self._settings)
            p.setFont(self._fonts['fps_label'])
            self._draw_text_with_shadow(p, lbl_x, y + self._metrics['fps_label'].ascent(), "FPS", fc, self._fonts['fps_label'])
            y += self._metrics['fps_label'].height() + 2
            ff = self._fonts['fps_big']
            fm = self._metrics['fps_big']
            p.setFont(ff)
            val_color = hex_to_qcolor(c.fps_value)
            self._draw_text_with_shadow(p, lbl_x + 2, y + fm.ascent(), f"{self._fps_data.fps:.1f}", val_color, ff)
            y += fm.height() + 2
            if d.show_fps_1low:
                p.setFont(df)
                low_color = hex_to_qcolor(c.fps_1low)
                self._draw_text_with_shadow(p, lbl_x, y + dm.ascent(), f"1%Low: {self._fps_data.fps_1low:.1f}", low_color, df)
                y += lh
            if d.show_fps_latency:
                p.setFont(df)
                lat_color = hex_to_qcolor(c.fps_latency)
                self._draw_text_with_shadow(p, lbl_x, y + dm.ascent(), f"延迟: {self._fps_data.render_latency:.1f} ms", lat_color, df)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mode = "move"
            self._drag_offset = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._mode == "move":
            self.move(event.globalPos() - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mode = None
            self._settings.window.x = self.pos().x()
            self._settings.window.y = self.pos().y()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.settings_requested.emit()
            event.accept()


# ============================================================
# 设置对话框（加载时阻塞所有显示项复选框信号）
# ============================================================
class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(object)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._color_buttons = {}
        self._init_ui()
        self._load_settings()
        self._center_on_screen()

    def _init_ui(self):
        self.setWindowTitle("OSD 设置")
        self.setMinimumSize(550, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(4)
        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)

        self._build_tab_appearance()
        self._build_tab_cpu()
        self._build_tab_gpu()
        self._build_tab_fps()
        self._build_tab_about()

        btn_close = QPushButton("关闭")
        btn_close.setMinimumHeight(26)
        btn_close.setMinimumWidth(80)
        btn_close.clicked.connect(self.close)
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(btn_close)
        outer.addLayout(hbox)

    def _apply_and_save(self):
        self.settings_changed.emit(self._settings)
        self._settings.save()

    def _build_scroll_tab(self, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(container)
        self._tabs.addTab(scroll, title)
        return layout

    def _build_tab_appearance(self):
        lay = self._build_scroll_tab("外观")

        g0 = QGroupBox("主题预设")
        l0 = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_NAMES)
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        l0.addWidget(QLabel("配色:"))
        l0.addWidget(self.theme_combo, 1)
        g0.setLayout(l0)
        lay.addWidget(g0)

        g_font = QGroupBox("字体")
        lf = QFormLayout()
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._apply_font)
        lf.addRow("字体:", self.font_combo)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 99)
        self.font_size.valueChanged.connect(self._apply_font)
        lf.addRow("字号:", self.font_size)
        self.font_bold = QCheckBox("粗体")
        self.font_bold.stateChanged.connect(self._apply_font)
        lf.addRow("", self.font_bold)
        self.font_weight = QSlider(Qt.Horizontal)
        self.font_weight.setRange(0, 99)
        self.font_weight.setValue(75)
        self.font_weight.setTickPosition(QSlider.TicksBelow)
        self.font_weight.setTickInterval(10)
        self.font_weight.valueChanged.connect(self._apply_font)
        lf.addRow("字重 (仅粗体生效):", self.font_weight)
        g_font.setLayout(lf)
        lay.addWidget(g_font)

        g_shadow = QGroupBox("文字阴影")
        ls = QFormLayout()
        self.shadow_enabled = QCheckBox("启用阴影")
        self.shadow_enabled.stateChanged.connect(self._apply_shadow)
        ls.addRow("", self.shadow_enabled)
        self.shadow_color_btn = QPushButton()
        self.shadow_color_btn.setFixedSize(50, 20)
        self.shadow_color_btn.setCursor(Qt.PointingHandCursor)
        self.shadow_color_btn.setProperty("color", "#000000")
        self.shadow_color_btn.setStyleSheet("background-color: #000000; border: 1px solid #999; border-radius: 3px;")
        self.shadow_color_btn.clicked.connect(lambda: self._pick_color(self.shadow_color_btn, self._apply_shadow))
        ls.addRow("阴影颜色:", self.shadow_color_btn)
        self.shadow_offset_x = QSpinBox()
        self.shadow_offset_x.setRange(-5, 5)
        self.shadow_offset_x.valueChanged.connect(self._apply_shadow)
        ls.addRow("水平偏移:", self.shadow_offset_x)
        self.shadow_offset_y = QSpinBox()
        self.shadow_offset_y.setRange(-5, 5)
        self.shadow_offset_y.valueChanged.connect(self._apply_shadow)
        ls.addRow("垂直偏移:", self.shadow_offset_y)
        self.shadow_opacity = QSlider(Qt.Horizontal)
        self.shadow_opacity.setRange(0, 100)
        self.shadow_opacity.setTickPosition(QSlider.TicksBelow)
        self.shadow_opacity.setTickInterval(10)
        self.shadow_opacity.valueChanged.connect(self._apply_shadow)
        ls.addRow("不透明度 (%):", self.shadow_opacity)
        g_shadow.setLayout(ls)
        lay.addWidget(g_shadow)

        g1 = QGroupBox("窗口外观")
        l1 = QFormLayout()
        self.window_opacity = QSlider(Qt.Horizontal)
        self.window_opacity.setRange(10, 100)
        self.window_opacity.setTickPosition(QSlider.TicksBelow)
        self.window_opacity.setTickInterval(10)
        self.window_opacity.valueChanged.connect(self._apply_window)
        l1.addRow("窗口透明度:", self.window_opacity)
        self.show_bg = QCheckBox("显示背景")
        self.show_bg.stateChanged.connect(self._apply_window)
        l1.addRow(self.show_bg)
        self.bg_opacity = QSlider(Qt.Horizontal)
        self.bg_opacity.setRange(0, 255)
        self.bg_opacity.setTickPosition(QSlider.TicksBelow)
        self.bg_opacity.setTickInterval(10)
        self.bg_opacity.valueChanged.connect(self._apply_window)
        l1.addRow("背景透明度:", self.bg_opacity)
        self.interval = QSpinBox()
        self.interval.setRange(100, 5000)
        self.interval.setSuffix(" ms")
        self.interval.setSingleStep(100)
        self.interval.valueChanged.connect(self._apply_window)
        l1.addRow("刷新间隔:", self.interval)
        g1.setLayout(l1)
        lay.addWidget(g1)

        g_label_color = QGroupBox("标签文字颜色")
        lbl_layout = QHBoxLayout()
        self.label_color_btn = QPushButton()
        self.label_color_btn.setFixedSize(50, 20)
        self.label_color_btn.setCursor(Qt.PointingHandCursor)
        self.label_color_btn.setProperty("color", "#66b5ff")
        self.label_color_btn.setStyleSheet("background-color: #66b5ff; border: 1px solid #999; border-radius: 3px;")
        self.label_color_btn.clicked.connect(lambda: self._pick_color(self.label_color_btn, self._apply_label_color))
        lbl_layout.addWidget(QLabel("标签文字颜色:"))
        lbl_layout.addWidget(self.label_color_btn)
        lbl_layout.addStretch()
        g_label_color.setLayout(lbl_layout)
        lay.addWidget(g_label_color)

        lay.addStretch()

    def _build_tab_cpu(self):
        lay = self._build_scroll_tab("CPU")
        g_show = QGroupBox("CPU 显示项")
        lc = QVBoxLayout()
        lc.setSpacing(3)
        self.show_cpu = QCheckBox("显示 CPU")
        self.show_cpu.stateChanged.connect(self._apply_display)
        self.show_cpu_usage = QCheckBox("占用率")
        self.show_cpu_usage.stateChanged.connect(self._apply_display)
        self.show_cpu_freq = QCheckBox("频率")
        self.show_cpu_freq.stateChanged.connect(self._apply_display)
        self.show_cpu_p_core = QCheckBox("P-Core 频率")
        self.show_cpu_p_core.stateChanged.connect(self._apply_display)
        self.show_cpu_e_core = QCheckBox("E-Core 频率")
        self.show_cpu_e_core.stateChanged.connect(self._apply_display)
        self.show_cpu_temp = QCheckBox("温度")
        self.show_cpu_temp.stateChanged.connect(self._apply_display)
        self.show_cpu_voltage = QCheckBox("电压")
        self.show_cpu_voltage.stateChanged.connect(self._apply_display)
        self.show_cpu_power = QCheckBox("功耗")
        self.show_cpu_power.stateChanged.connect(self._apply_display)
        for cb in [self.show_cpu, self.show_cpu_usage, self.show_cpu_freq,
                   self.show_cpu_p_core, self.show_cpu_e_core, self.show_cpu_temp,
                   self.show_cpu_voltage, self.show_cpu_power]:
            lc.addWidget(cb)
        g_show.setLayout(lc)
        lay.addWidget(g_show)

        g_color = QGroupBox("颜色设置")
        form = QFormLayout()
        form.setSpacing(4)
        cpu_attrs = [
            ("CPU标题", "cpu_header"),
            ("CPU名称", "cpu_name"),
            ("占用率", "cpu_usage"),
            ("频率", "cpu_freq"),
            ("P-Core", "cpu_p_core"),
            ("E-Core", "cpu_e_core"),
            ("温度", "cpu_temp"),
            ("电压", "cpu_voltage"),
            ("功耗", "cpu_power"),
        ]
        for label, attr in cpu_attrs:
            btn = QPushButton()
            btn.setFixedSize(40, 18)
            btn.setCursor(Qt.PointingHandCursor)
            default = getattr(self._settings.colors, attr, "#FFFFFF")
            btn.setStyleSheet(f"background-color: {default}; border: 1px solid #999; border-radius: 3px;")
            btn.setProperty("color", default)
            btn.clicked.connect(lambda checked, a=attr, b=btn: self._pick_color(b, lambda: self._apply_color(a, b)))
            self._color_buttons[attr] = btn
            form.addRow(QLabel(label), btn)
        g_color.setLayout(form)
        lay.addWidget(g_color)
        lay.addStretch()

    def _build_tab_gpu(self):
        lay = self._build_scroll_tab("GPU")
        g_show = QGroupBox("GPU 显示项")
        lg = QVBoxLayout()
        lg.setSpacing(3)
        self.show_gpu = QCheckBox("显示 GPU")
        self.show_gpu.stateChanged.connect(self._apply_display)
        self.show_gpu_usage = QCheckBox("占用率")
        self.show_gpu_usage.stateChanged.connect(self._apply_display)
        self.show_gpu_freq = QCheckBox("频率")
        self.show_gpu_freq.stateChanged.connect(self._apply_display)
        self.show_gpu_temp = QCheckBox("温度")
        self.show_gpu_temp.stateChanged.connect(self._apply_display)
        self.show_gpu_voltage = QCheckBox("电压")
        self.show_gpu_voltage.stateChanged.connect(self._apply_display)
        self.show_gpu_power = QCheckBox("功耗")
        self.show_gpu_power.stateChanged.connect(self._apply_display)
        self.show_gpu_memory = QCheckBox("显存")
        self.show_gpu_memory.stateChanged.connect(self._apply_display)
        for cb in [self.show_gpu, self.show_gpu_usage, self.show_gpu_freq,
                   self.show_gpu_temp, self.show_gpu_voltage, self.show_gpu_power,
                   self.show_gpu_memory]:
            lg.addWidget(cb)
        g_show.setLayout(lg)
        lay.addWidget(g_show)

        g_gname = QGroupBox("GPU 自定义名称（留空=自动）")
        ln = QFormLayout()
        self.gpu_name = QLineEdit()
        self.gpu_name.setPlaceholderText("例如: RTX 5060 Ti")
        self.gpu_name.textChanged.connect(self._apply_gpu_name)
        ln.addRow("名称:", self.gpu_name)
        g_gname.setLayout(ln)
        lay.addWidget(g_gname)

        g_color = QGroupBox("颜色设置")
        form = QFormLayout()
        form.setSpacing(4)
        gpu_attrs = [
            ("GPU标题", "gpu_header"),
            ("GPU名称", "gpu_name"),
            ("占用率", "gpu_usage"),
            ("频率", "gpu_freq"),
            ("温度", "gpu_temp"),
            ("电压", "gpu_voltage"),
            ("功耗", "gpu_power"),
            ("显存", "gpu_memory"),
        ]
        for label, attr in gpu_attrs:
            btn = QPushButton()
            btn.setFixedSize(40, 18)
            btn.setCursor(Qt.PointingHandCursor)
            default = getattr(self._settings.colors, attr, "#FFFFFF")
            btn.setStyleSheet(f"background-color: {default}; border: 1px solid #999; border-radius: 3px;")
            btn.setProperty("color", default)
            btn.clicked.connect(lambda checked, a=attr, b=btn: self._pick_color(b, lambda: self._apply_color(a, b)))
            self._color_buttons[attr] = btn
            form.addRow(QLabel(label), btn)
        g_color.setLayout(form)
        lay.addWidget(g_color)
        lay.addStretch()

    def _build_tab_fps(self):
        lay = self._build_scroll_tab("FPS")
        g_show = QGroupBox("FPS 显示项")
        lfps = QVBoxLayout()
        lfps.setSpacing(3)
        self.show_fps = QCheckBox("显示 FPS")
        self.show_fps.stateChanged.connect(self._apply_display)
        self.show_fps_1low = QCheckBox("1%Low")
        self.show_fps_1low.stateChanged.connect(self._apply_display)
        self.show_fps_latency = QCheckBox("延迟")
        self.show_fps_latency.stateChanged.connect(self._apply_display)
        for cb in [self.show_fps, self.show_fps_1low, self.show_fps_latency]:
            lfps.addWidget(cb)
        g_show.setLayout(lfps)
        lay.addWidget(g_show)

        g_color = QGroupBox("颜色设置")
        form = QFormLayout()
        form.setSpacing(4)
        fps_attrs = [
            ("FPS标题", "fps_header"),
            ("FPS数值", "fps_value"),
            ("1%Low", "fps_1low"),
            ("延迟", "fps_latency"),
        ]
        for label, attr in fps_attrs:
            btn = QPushButton()
            btn.setFixedSize(40, 18)
            btn.setCursor(Qt.PointingHandCursor)
            default = getattr(self._settings.colors, attr, "#FFFFFF")
            btn.setStyleSheet(f"background-color: {default}; border: 1px solid #999; border-radius: 3px;")
            btn.setProperty("color", default)
            btn.clicked.connect(lambda checked, a=attr, b=btn: self._pick_color(b, lambda: self._apply_color(a, b)))
            self._color_buttons[attr] = btn
            form.addRow(QLabel(label), btn)
        g_color.setLayout(form)
        lay.addWidget(g_color)
        lay.addStretch()

    def _build_tab_about(self):
        lay = self._build_scroll_tab("关于")
        about_html = """
        <div style="font-family: 'Microsoft YaHei', sans-serif; color: #E0E0E0; padding: 8px; line-height: 1.6;">
        <h2 style="color: #4A9EFF;">Performance Monitor OSD</h2>
        <p style="color: #B0B0B0;">轻量级性能监控悬浮窗 &mdash; 版本 1.0</p>
        <hr style="border-color: #3A3A4A;">
        <h3 style="color: #FFD700;">功能特性</h3>
        <ul>
        <li><b>CPU 监控</b> &mdash; 占用率、频率、P-Core/E-Core 独立显示、温度、电压、功耗</li>
        <li><b>GPU 监控</b> &mdash; 占用率、频率、温度、电压、功耗、显存使用量</li>
        <li><b>FPS 监控</b> &mdash; 实时帧率、1% Low、0.1% Low、帧间延迟</li>
        <li><b>帧率分析</b> &mdash; 基于 NVIDIA FrameView 标准的 1% Low 算法，支持 DLSS 帧生成感知</li>
        <li><b>DXGI 采集</b> &mdash; 通过 Desktop Duplication API 直接检测显示输出帧，精确捕捉游戏画面变化</li>
        <li><b>GDI 回退</b> &mdash; DXGI 不可用时自动切换 BitBlt 方式作为备选</li>
        <li><b>DLL 传感器</b> &mdash; 通过 pythonnet 加载 LibreHardwareMonitorLib.dll 直接读取硬件传感器</li>
        <li><b>NVIDIA 驱动</b> &mdash; 通过 pynvml 直接读取 GPU 详细数据（频率、功耗、显存等）</li>
        <li><b>系统托盘</b> &mdash; 图标托盘菜单，支持显示/隐藏、固定（鼠标穿透）、设置、退出</li>
        <li><b>自定义主题</b> &mdash; 12 种预设主题，所有颜色均可自定义，包括标题、名称、数值、详情</li>
        <li><b>自适应布局</b> &mdash; 字体大小变化时自动调整窗口尺寸和列宽</li>
        <li><b>透明悬浮</b> &mdash; 无边框、置顶、透明背景，不干扰游戏操作</li>
        </ul>
        <h3 style="color: #FFD700;">技术架构</h3>
        <table style="color: #C0C0C0; border-collapse: collapse;">
        <tr><td style="padding: 2px 12px 2px 0;"><b>语言</b></td><td>Python 3.10</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>GUI</b></td><td>PyQt5</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>FPS 采集</b></td><td>DXGI Desktop Duplication API (Win32 COM)</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>硬件传感器</b></td><td>LibreHardwareMonitorLib.dll (pythonnet)</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>GPU 数据</b></td><td>NVML (nvidia-ml-py)</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>进程信息</b></td><td>psutil</td></tr>
        <tr><td style="padding: 2px 12px 2px 0;"><b>帧率算法</b></td><td>NVIDIA FrameView 标准 (worst 1% average)</td></tr>
        </table>
        <h3 style="color: #FFD700;">关于 1% Low</h3>
        <p style="color: #B0B0B0;">
        1% Low 取最慢 1% 帧的平均帧时间转换为 FPS，反映游戏中的卡顿体验。
        当启用 DLSS Frame Generation 时，显示帧率包含插值生成帧，1% Low 可能会掩盖真实渲染瓶颈。
        本工具同时计算 0.1% Low 以提供更极端的卡顿指标。
        </p>
        <h3 style="color: #FFD700;">操作说明</h3>
        <ul>
        <li>双击 OSD 窗口打开设置</li>
        <li>拖拽 OSD 窗口移动位置，拖拽边缘调整大小</li>
        <li>右键托盘图标访问菜单</li>
        <li>"固定" 模式下 OSD 鼠标穿透，不阻挡游戏操作</li>
        </ul>
        <p style="color: #888; font-size: 11px; text-align: center; margin-top: 16px;">
        Performance Monitor OSD  &copy; jingmo 2026
        </p>
        </div>
        """
        browser = QTextBrowser()
        browser.setHtml(about_html)
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("QTextBrowser { background-color: #2D2D3D; color: #E0E0E0; border: none; }")
        lay.addWidget(browser)

    def _center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(max(0, x), max(0, y))

    # ----- 实时应用函数 -----
    def _apply_theme(self, name):
        if name:
            self._settings.apply_theme(name)
            self._update_color_buttons()
            self._apply_and_save()

    def _update_color_buttons(self):
        for attr, btn in self._color_buttons.items():
            c = getattr(self._settings.colors, attr, "#FFFFFF")
            btn.setStyleSheet(f"background-color: {c}; border: 1px solid #999; border-radius: 3px;")
            btn.setProperty("color", c)
        c = self._settings.colors.label_color
        self.label_color_btn.setStyleSheet(f"background-color: {c}; border: 1px solid #999; border-radius: 3px;")
        self.label_color_btn.setProperty("color", c)

    def _apply_font(self):
        self._settings.font.family = self.font_combo.currentFont().family()
        self._settings.font.size = self.font_size.value()
        self._settings.font.bold = self.font_bold.isChecked()
        self._settings.font.weight = self.font_weight.value()
        self._apply_and_save()

    def _apply_shadow(self):
        self._settings.shadow.enabled = self.shadow_enabled.isChecked()
        self._settings.shadow.color = self.shadow_color_btn.property("color")
        self._settings.shadow.offset_x = self.shadow_offset_x.value()
        self._settings.shadow.offset_y = self.shadow_offset_y.value()
        self._settings.shadow.opacity = self.shadow_opacity.value()
        self._apply_and_save()

    def _apply_window(self):
        self._settings.window.opacity = self.window_opacity.value() / 100.0
        self._settings.window.show_background = self.show_bg.isChecked()
        self._settings.window.background_opacity = self.bg_opacity.value()
        self._settings.window.update_interval = self.interval.value()
        self._apply_and_save()

    def _apply_display(self):
        d = self._settings.display
        d.show_cpu = self.show_cpu.isChecked()
        d.show_cpu_usage = self.show_cpu_usage.isChecked()
        d.show_cpu_freq = self.show_cpu_freq.isChecked()
        d.show_cpu_p_core = self.show_cpu_p_core.isChecked()
        d.show_cpu_e_core = self.show_cpu_e_core.isChecked()
        d.show_cpu_temp = self.show_cpu_temp.isChecked()
        d.show_cpu_voltage = self.show_cpu_voltage.isChecked()
        d.show_cpu_power = self.show_cpu_power.isChecked()
        d.show_gpu = self.show_gpu.isChecked()
        d.show_gpu_usage = self.show_gpu_usage.isChecked()
        d.show_gpu_freq = self.show_gpu_freq.isChecked()
        d.show_gpu_temp = self.show_gpu_temp.isChecked()
        d.show_gpu_voltage = self.show_gpu_voltage.isChecked()
        d.show_gpu_power = self.show_gpu_power.isChecked()
        d.show_gpu_memory = self.show_gpu_memory.isChecked()
        d.show_fps = self.show_fps.isChecked()
        d.show_fps_1low = self.show_fps_1low.isChecked()
        d.show_fps_latency = self.show_fps_latency.isChecked()
        self._apply_and_save()

    def _apply_gpu_name(self):
        self._settings.gpu_custom.custom_name = self.gpu_name.text().strip()
        self._apply_and_save()

    def _apply_color(self, attr, btn):
        c = btn.property("color")
        if c:
            setattr(self._settings.colors, attr, c)
            self._apply_and_save()

    def _apply_label_color(self):
        c = self.label_color_btn.property("color")
        if c:
            self._settings.colors.label_color = c
            self._apply_and_save()

    def _pick_color(self, btn, callback):
        c = QColorDialog.getColor(hex_to_qcolor(btn.property("color") or "#FFFFFF"), self, "选择颜色")
        if c.isValid():
            btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #999; border-radius: 3px;")
            btn.setProperty("color", c.name())
            callback()

    # ----- 加载设置（阻塞所有信号）-----
    def _load_settings(self):
        s = self._settings

        # 阻塞所有显示项复选框的信号
        display_checkboxes = [
            self.show_cpu, self.show_cpu_usage, self.show_cpu_freq,
            self.show_cpu_p_core, self.show_cpu_e_core, self.show_cpu_temp,
            self.show_cpu_voltage, self.show_cpu_power,
            self.show_gpu, self.show_gpu_usage, self.show_gpu_freq,
            self.show_gpu_temp, self.show_gpu_voltage, self.show_gpu_power,
            self.show_gpu_memory,
            self.show_fps, self.show_fps_1low, self.show_fps_latency
        ]
        for cb in display_checkboxes:
            cb.blockSignals(True)

        # 阻塞其他控件信号
        self.theme_combo.blockSignals(True)
        self.font_combo.blockSignals(True)
        self.font_size.blockSignals(True)
        self.font_bold.blockSignals(True)
        self.font_weight.blockSignals(True)
        self.window_opacity.blockSignals(True)
        self.interval.blockSignals(True)
        self.show_bg.blockSignals(True)
        self.bg_opacity.blockSignals(True)
        self.shadow_enabled.blockSignals(True)
        self.shadow_offset_x.blockSignals(True)
        self.shadow_offset_y.blockSignals(True)
        self.shadow_opacity.blockSignals(True)

        # 设置值
        if s.theme_name in THEME_NAMES:
            self.theme_combo.setCurrentText(s.theme_name)

        self.font_combo.setCurrentFont(QFont(s.font.family if s.font.family else "Microsoft YaHei"))
        self.font_size.setValue(s.font.size)
        self.font_bold.setChecked(s.font.bold)
        self.font_weight.setValue(s.font.weight)

        self.window_opacity.setValue(int(s.window.opacity * 100))
        self.interval.setValue(s.window.update_interval)
        self.show_bg.setChecked(s.window.show_background)
        self.bg_opacity.setValue(s.window.background_opacity)

        shadow = s.shadow
        self.shadow_enabled.setChecked(shadow.enabled)
        self.shadow_color_btn.setStyleSheet(f"background-color: {shadow.color}; border: 1px solid #999; border-radius: 3px;")
        self.shadow_color_btn.setProperty("color", shadow.color)
        self.shadow_offset_x.setValue(shadow.offset_x)
        self.shadow_offset_y.setValue(shadow.offset_y)
        self.shadow_opacity.setValue(shadow.opacity)

        self.label_color_btn.setStyleSheet(f"background-color: {s.colors.label_color}; border: 1px solid #999; border-radius: 3px;")
        self.label_color_btn.setProperty("color", s.colors.label_color)

        # 设置显示项复选框
        d = s.display
        self.show_cpu.setChecked(d.show_cpu)
        self.show_cpu_usage.setChecked(d.show_cpu_usage)
        self.show_cpu_freq.setChecked(d.show_cpu_freq)
        self.show_cpu_p_core.setChecked(d.show_cpu_p_core)
        self.show_cpu_e_core.setChecked(d.show_cpu_e_core)
        self.show_cpu_temp.setChecked(d.show_cpu_temp)
        self.show_cpu_voltage.setChecked(d.show_cpu_voltage)
        self.show_cpu_power.setChecked(d.show_cpu_power)
        self.show_gpu.setChecked(d.show_gpu)
        self.show_gpu_usage.setChecked(d.show_gpu_usage)
        self.show_gpu_freq.setChecked(d.show_gpu_freq)
        self.show_gpu_temp.setChecked(d.show_gpu_temp)
        self.show_gpu_voltage.setChecked(d.show_gpu_voltage)
        self.show_gpu_power.setChecked(d.show_gpu_power)
        self.show_gpu_memory.setChecked(d.show_gpu_memory)
        self.show_fps.setChecked(d.show_fps)
        self.show_fps_1low.setChecked(d.show_fps_1low)
        self.show_fps_latency.setChecked(d.show_fps_latency)

        self._update_color_buttons()
        self.gpu_name.setText(s.gpu_custom.custom_name)

        # 解除阻塞
        for cb in display_checkboxes:
            cb.blockSignals(False)
        self.theme_combo.blockSignals(False)
        self.font_combo.blockSignals(False)
        self.font_size.blockSignals(False)
        self.font_bold.blockSignals(False)
        self.font_weight.blockSignals(False)
        self.window_opacity.blockSignals(False)
        self.interval.blockSignals(False)
        self.show_bg.blockSignals(False)
        self.bg_opacity.blockSignals(False)
        self.shadow_enabled.blockSignals(False)
        self.shadow_offset_x.blockSignals(False)
        self.shadow_offset_y.blockSignals(False)
        self.shadow_opacity.blockSignals(False)

    def closeEvent(self, event):
        self._settings.save()
        event.accept()


# ============================================================
# 系统托盘
# ============================================================
class SystemTray(QSystemTrayIcon):
    show_hide_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()
    pin_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._set_rabbit_icon()
        self._create_menu()
        self.setToolTip("Performance Monitor")

    def _set_rabbit_icon(self):
        px = QPixmap(64, 64)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        ear_out = QColor("#F5E6D3")
        ear_in = QColor("#FFB6C1")
        border = QColor("#6B5B3E")
        p.setPen(QPen(border, 1.5))
        p.setBrush(QBrush(ear_out))
        p.drawRoundedRect(14, 0, 12, 26, 6, 6)
        p.setBrush(QBrush(ear_in))
        p.drawRoundedRect(17, 4, 6, 18, 3, 3)
        p.setBrush(QBrush(ear_out))
        p.drawRoundedRect(38, 0, 12, 26, 6, 6)
        p.setBrush(QBrush(ear_in))
        p.drawRoundedRect(41, 4, 6, 18, 3, 3)
        p.setPen(QPen(border, 1.5))
        p.setBrush(QBrush(ear_out))
        p.drawEllipse(10, 16, 44, 42)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#FFB6C1")))
        p.drawEllipse(12, 38, 10, 7)
        p.drawEllipse(42, 38, 10, 7)
        eye_w = QColor("#FFFFFF")
        eye_b = QColor("#333333")
        p.setPen(QPen(eye_b, 1))
        p.setBrush(QBrush(eye_w))
        p.drawEllipse(20, 30, 9, 9)
        p.drawEllipse(35, 30, 9, 9)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(eye_b))
        p.drawEllipse(24, 32, 5, 5)
        p.drawEllipse(39, 32, 5, 5)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(25, 32, 2, 2)
        p.drawEllipse(40, 32, 2, 2)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#FF8C94")))
        p.drawEllipse(30, 41, 4, 3)
        p.setPen(QPen(border, 1.0))
        p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(32, 44)
        path.cubicTo(29, 48, 26, 47, 24, 49)
        path.moveTo(32, 44)
        path.cubicTo(35, 48, 38, 47, 40, 49)
        p.drawPath(path)
        wpen = QPen(border, 0.7)
        p.setPen(wpen)
        p.drawLine(8, 40, 20, 42)
        p.drawLine(7, 44, 20, 44)
        p.drawLine(8, 48, 20, 46)
        p.drawLine(56, 40, 44, 42)
        p.drawLine(57, 44, 44, 44)
        p.drawLine(56, 48, 44, 46)
        p.end()
        self.setIcon(QIcon(px))

    def _create_menu(self):
        m = QMenu()
        m.setStyleSheet("""
            QMenu { background-color: #2D2D3D; border: 1px solid #3D3D4D; border-radius: 4px; padding: 4px; }
            QMenu::item { color: #FFFFFF; padding: 6px 20px; }
            QMenu::item:selected { background-color: #4A9EFF; }
            QMenu::item:checked { color: #4A9EFF; }
        """)
        m.addAction(QAction("显示/隐藏", self, triggered=self.show_hide_clicked.emit))
        m.addAction(QAction("设置", self, triggered=self.settings_clicked.emit))
        m.addSeparator()
        self._pin_action = QAction("固定", self, checkable=True, checked=False)
        self._pin_action.triggered.connect(self._on_pin_toggled)
        m.addAction(self._pin_action)
        m.addSeparator()
        m.addAction(QAction("退出", self, triggered=self.quit_clicked.emit))
        self.setContextMenu(m)

    def _on_pin_toggled(self, checked):
        self.pin_toggled.emit(checked)

    def set_pinned_state(self, pinned):
        self._pin_action.setChecked(pinned)

    def update_tooltip(self, cpu, gpu, fps):
        self.setToolTip(f"CPU: {cpu:.1f}% | GPU: {gpu:.1f}% | FPS: {fps:.1f}")