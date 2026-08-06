"""
ui.py - 用户界面（完整版，第一部分）
包含：导入、辅助函数、OSDWindow 类
"""
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QCheckBox, QSlider, QSpinBox, QFontComboBox,
    QColorDialog, QSystemTrayIcon, QMenu, QAction, QApplication,
    QGroupBox, QLineEdit, QComboBox, QLabel, QScrollArea, QTabWidget,
    QTextBrowser, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QIcon, QPixmap, QFontMetrics, QPainterPath

from settings import Settings, THEME_PRESETS, THEME_NAMES
from monitor import CPUData, GPUData, NetData, FPSData

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

def format_speed(kb_s):
    """将 KB/s 转换为可读字符串 (自动 KB/s / MB/s)"""
    if kb_s is None:
        return "N/A"
    if kb_s >= 1024:
        return f"{kb_s/1024:.2f} MB/s"
    else:
        return f"{kb_s:.2f} KB/s"

class ModuleLayout:
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"

class OSDWindow(QWidget):
    settings_requested = pyqtSignal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._cpu_data = CPUData()
        self._gpu_data = GPUData()
        self._net_data = None
        self._fps_data = FPSData()
        self._mode = None
        self._drag_offset = QPoint()
        self._fonts = {}
        self._metrics = {}
        self._fonts_dirty = True

        # 记录字段有效性（启动时判定，之后不变）
        self._valid_fields = {
            "cpu_usage": True, "cpu_freq": True, "cpu_freq_avg": True,
            "cpu_p_core_avg": True, "cpu_e_core_avg": True,
            "cpu_temp": True, "cpu_voltage": True, "cpu_power": True,
            "gpu_usage": True, "gpu_freq": True, "gpu_temp": True,
            "gpu_voltage": True, "gpu_power": True, "gpu_memory": True,
            "net_upload": True, "net_download": True,
        }
        self._first_update = True

        self._init_window()

    def _init_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        ws = self._settings.window
        self.move(ws.x, ws.y)
        self.setWindowOpacity(ws.opacity)
        self._apply_pinned(ws.pinned)
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

    # ---------- 尺寸计算 ----------
    def _calc_col_width(self):
        dl = self._metrics.get('label')
        if not dl:
            self._ensure_fonts()
            dl = self._metrics['label']
        labels = ["频率", "P-Core", "E-Core", "占用率", "温度", "电压", "功耗", "显存", "上行", "下行"]
        return max(dl.horizontalAdvance(t) for t in labels)

    def _calc_size(self):
        d = self._settings.display
        layout_mode = self._settings.window.layout_mode
        self._ensure_fonts()
        dl = self._fonts['label']
        dm = self._fonts['data']
        dm_b = self._fonts['data_b']
        dm_l = self._metrics['label']
        dm_m = self._metrics['data']
        dm_bm = self._metrics['data_b']
        lh = dm_m.height() + 2
        pad = 8
        gap = 6
        col_w = self._calc_col_width()
        lbl_x = pad
        val_x = lbl_x + col_w + gap

        if layout_mode == ModuleLayout.VERTICAL:
            return self._calc_size_vertical(d, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x)
        else:  # horizontal
            return self._calc_size_horizontal(d, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x)

    # ---------- 垂直尺寸计算（按顺序迭代） ----------
    def _calc_size_vertical(self, d, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x):
        max_w = 0
        y = pad
        fm_l = self._fonts['fps_label']
        fm_b = self._fonts['fps_big']
        fm_lm = self._metrics['fps_label']
        fm_bm = self._metrics['fps_big']

        def _check_w(x, w):
            nonlocal max_w
            tw = x + w + pad
            if tw > max_w:
                max_w = tw

        def _check_line(label, value):
            _check_w(lbl_x, dm_l.horizontalAdvance(label))
            _check_w(val_x, dm_m.horizontalAdvance(value))

        # 根据模块顺序迭代
        order = self._settings.window.module_order
        for module_name in order:
            if module_name == "CPU" and d.show_cpu:
                if d.show_cpu_header:
                    cpu_header_w = dm_bm.horizontalAdvance("CPU") + gap + dm_l.horizontalAdvance(self._cpu_data.name)
                    _check_w(lbl_x, cpu_header_w)
                    y += lh

                # 占用率
                if d.show_cpu_usage and self._valid_fields.get("cpu_usage", False) and self._cpu_data.usage is not None:
                    _check_line("占用率", fmt_val(self._cpu_data.usage, ".1f", " %")); y += lh

                # 频率：优先显示平均值，若没有则显示最大值（兼容）
                freq_display = None
                if d.show_cpu_freq:
                    if self._cpu_data.frequency_avg is not None:
                        freq_display = fmt_val(self._cpu_data.frequency_avg, ".0f", " MHz")
                        label_text = "频率"
                    elif self._cpu_data.frequency is not None:
                        freq_display = fmt_val(self._cpu_data.frequency, ".0f", " MHz")
                        label_text = "频率"
                    if freq_display:
                        _check_line(label_text, freq_display); y += lh

                # 单独显示 P-Core 和 E-Core 平均频率（若有效且不同于总平均）
                if d.show_cpu_freq and self._cpu_data.frequency_p_core_avg is not None:
                    if self._cpu_data.frequency_e_core_avg is not None:
                        # 若 P/E 均有效，则分别显示
                        if self._valid_fields.get("cpu_p_core_avg", False):
                            _check_line("P-Core", f"{self._cpu_data.frequency_p_core_avg:.0f} MHz"); y += lh
                        if self._valid_fields.get("cpu_e_core_avg", False) and self._cpu_data.frequency_e_core_avg is not None:
                            _check_line("E-Core", f"{self._cpu_data.frequency_e_core_avg:.0f} MHz"); y += lh
                    else:
                        # 只有 P-Core 平均值（无 E-Core），可忽略
                        pass

                if d.show_cpu_temp and self._valid_fields.get("cpu_temp", False) and self._cpu_data.temperature is not None:
                    _check_line("温度", fmt_val(self._cpu_data.temperature, ".1f", "°C")); y += lh
                if d.show_cpu_voltage and self._valid_fields.get("cpu_voltage", False) and self._cpu_data.voltage is not None:
                    _check_line("电压", fmt_val(self._cpu_data.voltage, ".3f", " V")); y += lh
                if d.show_cpu_power and self._valid_fields.get("cpu_power", False) and self._cpu_data.power is not None:
                    _check_line("功耗", fmt_val(self._cpu_data.power, ".1f", " W")); y += lh
                y += 8

            elif module_name == "GPU" and d.show_gpu:
                if d.show_gpu_header:
                    gpu_name = self._settings.gpu_custom.custom_name or self._gpu_data.name
                    gpu_header_w = dm_bm.horizontalAdvance("GPU") + gap + dm_l.horizontalAdvance(gpu_name)
                    _check_w(lbl_x, gpu_header_w)
                    y += lh
                if d.show_gpu_usage and self._valid_fields.get("gpu_usage", False) and self._gpu_data.usage is not None:
                    _check_line("占用率", fmt_val(self._gpu_data.usage, ".1f", " %")); y += lh
                if d.show_gpu_freq and self._valid_fields.get("gpu_freq", False) and self._gpu_data.frequency is not None:
                    _check_line("频率", fmt_val(self._gpu_data.frequency, ".0f", " MHz")); y += lh
                if d.show_gpu_temp and self._valid_fields.get("gpu_temp", False) and self._gpu_data.temperature is not None:
                    _check_line("温度", fmt_val(self._gpu_data.temperature, ".0f", "°C")); y += lh
                if d.show_gpu_voltage and self._valid_fields.get("gpu_voltage", False) and self._gpu_data.voltage is not None:
                    _check_line("电压", fmt_val(self._gpu_data.voltage, ".3f", " V")); y += lh
                if d.show_gpu_power and self._valid_fields.get("gpu_power", False) and self._gpu_data.power is not None:
                    _check_line("功耗", fmt_val(self._gpu_data.power, ".1f", " W")); y += lh
                if d.show_gpu_memory and self._valid_fields.get("gpu_memory", False) and self._gpu_data.memory_used is not None and self._gpu_data.memory_total is not None and self._gpu_data.memory_total > 0:
                    _check_line("显存", f"{self._gpu_data.memory_used:.0f} / {self._gpu_data.memory_total:.0f} MB"); y += lh
                y += 8

            elif module_name == "Net" and d.show_net and self._net_data:
                if d.show_net_header:
                    net_name = self._net_data.name
                    net_header_w = dm_bm.horizontalAdvance("网络") + gap + dm_l.horizontalAdvance(net_name)
                    _check_w(lbl_x, net_header_w)
                    y += lh
                if d.show_net_upload and self._valid_fields.get("net_upload", False) and self._net_data.upload_speed is not None:
                    _check_line("上行", format_speed(self._net_data.upload_speed)); y += lh
                if d.show_net_download and self._valid_fields.get("net_download", False) and self._net_data.download_speed is not None:
                    _check_line("下行", format_speed(self._net_data.download_speed)); y += lh
                y += 8

            elif module_name == "FPS" and d.show_fps and self._fps_data.available and not (d.hide_fps_below_60 and self._fps_data.fps <= 60):
                if d.show_fps_header:
                    _check_w(lbl_x, fm_lm.horizontalAdvance("FPS"))
                    y += fm_lm.height() + 2
                _check_w(lbl_x + 2, fm_bm.horizontalAdvance(f"{self._fps_data.fps:.1f}"))
                y += fm_bm.height() + 8
                if d.show_fps_1low:
                    _check_w(lbl_x, dm_m.horizontalAdvance(f"1%Low: {self._fps_data.fps_1pct_low:.1f}")); y += lh
                if d.show_fps_latency:
                    _check_w(lbl_x, dm_m.horizontalAdvance(f"帧时间: {self._fps_data.frametime_avg:.2f} ms")); y += lh

        w = max(max_w, 180)
        h = max(20, y + pad)
        return QSize(w, h)

    # ---------- 水平尺寸计算（按顺序迭代） ----------
    def _calc_size_horizontal(self, d, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x):
        modules = []
        order = self._settings.window.module_order
        for name in order:
            if name == "CPU" and d.show_cpu:
                modules.append(("CPU", self._cpu_data, d, "cpu"))
            elif name == "GPU" and d.show_gpu:
                modules.append(("GPU", self._gpu_data, d, "gpu"))
            elif name == "Net" and d.show_net and self._net_data:
                modules.append(("网络", self._net_data, d, "net"))
            elif name == "FPS" and d.show_fps and self._fps_data.available and not (d.hide_fps_below_60 and self._fps_data.fps <= 60):
                modules.append(("FPS", self._fps_data, d, "fps"))

        if not modules:
            return QSize(180, 20)

        module_widths = []
        module_heights = []
        for name, data, d_obj, prefix in modules:
            w, h = self._calc_module_size_internal(name, data, d_obj, prefix, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x)
            module_widths.append(w)
            module_heights.append(h)

        total_w = sum(module_widths) + pad * 2 + gap * (len(modules) - 1)
        total_h = max(module_heights) if module_heights else 20
        return QSize(max(total_w, 180), max(total_h, 20))

    def _calc_module_size_internal(self, name, data, d_obj, prefix, dl, dm, dm_b, dm_l, dm_m, dm_bm, lh, pad, gap, col_w, lbl_x, val_x):
        max_w = 0
        y = pad
        if prefix == "cpu":
            show_header = d_obj.show_cpu_header
            show_usage = d_obj.show_cpu_usage
            show_freq = d_obj.show_cpu_freq
            show_temp = d_obj.show_cpu_temp
            show_voltage = d_obj.show_cpu_voltage
            show_power = d_obj.show_cpu_power
            valid_usage = self._valid_fields.get("cpu_usage", False)
            valid_freq = self._valid_fields.get("cpu_freq", False)
            valid_freq_avg = self._valid_fields.get("cpu_freq_avg", False)
            valid_p_core = self._valid_fields.get("cpu_p_core_avg", False)
            valid_e_core = self._valid_fields.get("cpu_e_core_avg", False)
            valid_temp = self._valid_fields.get("cpu_temp", False)
            valid_voltage = self._valid_fields.get("cpu_voltage", False)
            valid_power = self._valid_fields.get("cpu_power", False)
            data_usage = data.usage
            data_freq = data.frequency
            data_freq_avg = data.frequency_avg
            data_p_core = data.frequency_p_core_avg
            data_e_core = data.frequency_e_core_avg
            data_temp = data.temperature
            data_voltage = data.voltage
            data_power = data.power
            name_str = data.name if hasattr(data, 'name') else ""
        elif prefix == "gpu":
            show_header = d_obj.show_gpu_header
            show_usage = d_obj.show_gpu_usage
            show_freq = d_obj.show_gpu_freq
            show_temp = d_obj.show_gpu_temp
            show_voltage = d_obj.show_gpu_voltage
            show_power = d_obj.show_gpu_power
            show_memory = d_obj.show_gpu_memory
            valid_usage = self._valid_fields.get("gpu_usage", False)
            valid_freq = self._valid_fields.get("gpu_freq", False)
            valid_temp = self._valid_fields.get("gpu_temp", False)
            valid_voltage = self._valid_fields.get("gpu_voltage", False)
            valid_power = self._valid_fields.get("gpu_power", False)
            valid_memory = self._valid_fields.get("gpu_memory", False)
            data_usage = data.usage
            data_freq = data.frequency
            data_temp = data.temperature
            data_voltage = data.voltage
            data_power = data.power
            data_memory_used = data.memory_used if hasattr(data, 'memory_used') else None
            data_memory_total = data.memory_total if hasattr(data, 'memory_total') else None
            name_str = self._settings.gpu_custom.custom_name or data.name
        elif prefix == "net":
            show_header = d_obj.show_net_header
            show_upload = d_obj.show_net_upload
            show_download = d_obj.show_net_download
            valid_upload = self._valid_fields.get("net_upload", False)
            valid_download = self._valid_fields.get("net_download", False)
            data_upload = data.upload_speed
            data_download = data.download_speed
            name_str = data.name
        elif prefix == "fps":
            show_header = d_obj.show_fps_header
            show_1low = d_obj.show_fps_1low
            show_latency = d_obj.show_fps_latency
            data_fps = data.fps
            data_1low = data.fps_1pct_low
            data_latency = data.frametime_avg
            name_str = "FPS"
        else:
            return 20, 20

        def _check_w(x, w):
            nonlocal max_w
            tw = x + w + pad
            if tw > max_w:
                max_w = tw

        def _check_line(label, value):
            _check_w(lbl_x, dm_l.horizontalAdvance(label))
            _check_w(val_x, dm_m.horizontalAdvance(value))

        if show_header:
            if prefix == "fps":
                header_label = "FPS"
            else:
                header_label = name
            header_w = dm_bm.horizontalAdvance(header_label) + gap + dm_l.horizontalAdvance(name_str)
            _check_w(lbl_x, header_w)
            y += lh

        if prefix == "cpu":
            if show_usage and valid_usage and data_usage is not None:
                _check_line("占用率", fmt_val(data_usage, ".1f", " %")); y += lh

            # 频率（优先平均值）
            if show_freq:
                if data_freq_avg is not None:
                    _check_line("频率", fmt_val(data_freq_avg, ".0f", " MHz")); y += lh
                elif data_freq is not None:
                    _check_line("频率", fmt_val(data_freq, ".0f", " MHz")); y += lh

                # P/E 核心
                if data_p_core is not None and data_e_core is not None:
                    if valid_p_core:
                        _check_line("P-Core", f"{data_p_core:.0f} MHz"); y += lh
                    if valid_e_core and data_e_core is not None:
                        _check_line("E-Core", f"{data_e_core:.0f} MHz"); y += lh
                elif data_p_core is not None and data_e_core is None:
                    # 无 E-Core，不显示 P-Core 单独行（避免冗余）
                    pass

            if show_temp and valid_temp and data_temp is not None:
                _check_line("温度", fmt_val(data_temp, ".1f", "°C")); y += lh
            if show_voltage and valid_voltage and data_voltage is not None:
                _check_line("电压", fmt_val(data_voltage, ".3f", " V")); y += lh
            if show_power and valid_power and data_power is not None:
                _check_line("功耗", fmt_val(data_power, ".1f", " W")); y += lh

        elif prefix == "gpu":
            if show_usage and valid_usage and data_usage is not None:
                _check_line("占用率", fmt_val(data_usage, ".1f", " %")); y += lh
            if show_freq and valid_freq and data_freq is not None:
                _check_line("频率", fmt_val(data_freq, ".0f", " MHz")); y += lh
            if show_temp and valid_temp and data_temp is not None:
                _check_line("温度", fmt_val(data_temp, ".0f", "°C")); y += lh
            if show_voltage and valid_voltage and data_voltage is not None:
                _check_line("电压", fmt_val(data_voltage, ".3f", " V")); y += lh
            if show_power and valid_power and data_power is not None:
                _check_line("功耗", fmt_val(data_power, ".1f", " W")); y += lh
            if show_memory and valid_memory and data_memory_used is not None and data_memory_total is not None and data_memory_total > 0:
                _check_line("显存", f"{data_memory_used:.0f} / {data_memory_total:.0f} MB"); y += lh

        elif prefix == "net":
            if show_upload and valid_upload and data_upload is not None:
                _check_line("上行", format_speed(data_upload)); y += lh
            if show_download and valid_download and data_download is not None:
                _check_line("下行", format_speed(data_download)); y += lh

        elif prefix == "fps":
            fm_big = self._fonts['fps_big']
            fm_big_m = self._metrics['fps_big']
            _check_w(lbl_x + 2, fm_big_m.horizontalAdvance(f"{data_fps:.1f}"))
            y += fm_big_m.height() + 8
            if show_1low:
                _check_w(lbl_x, dm_m.horizontalAdvance(f"1%Low: {data_1low:.1f}")); y += lh
            if show_latency:
                _check_w(lbl_x, dm_m.horizontalAdvance(f"帧时间: {data_latency:.2f} ms")); y += lh

        w = max_w + pad * 2
        h = max(20, y + pad)
        return w, h

    # ---------- 绘制 ----------
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
        self._draw(p, w, h)
        p.end()

    def _draw(self, p, w, h):
        layout_mode = self._settings.window.layout_mode
        if layout_mode == ModuleLayout.VERTICAL:
            self._draw_vertical(p, w, h)
        else:
            self._draw_horizontal(p, w, h)

    # ---------- 垂直绘制（按顺序迭代） ----------
    def _draw_vertical(self, p, w, h):
        pad = 8
        x = pad
        y = pad
        dl = self._fonts['label']
        df = self._fonts['data']
        db = self._fonts['data_b']
        dm_l = self._metrics['label']
        dm_m = self._metrics['data']
        dm_b = self._metrics['data_b']
        lh = dm_m.height() + 2
        c = self._settings.colors
        d = self._settings.display
        vline_x = w - pad
        col_w = self._calc_col_width()
        lbl_x = x
        val_x = lbl_x + col_w + 6
        gap = 6

        def _draw_header(label, name, header_color, name_color):
            nonlocal y
            p.setFont(db)
            self._draw_text_with_shadow(p, lbl_x, y + dm_b.ascent(), label, hex_to_qcolor(header_color), db)
            hw = dm_b.horizontalAdvance(label) + gap
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x + hw, y + dm_l.ascent(), name, hex_to_qcolor(name_color), dl)
            y += lh

        def _draw_line(label, value, value_color):
            nonlocal y
            if value is None:
                return
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x, y + dm_l.ascent(), label, hex_to_qcolor(c.label_color), dl)
            p.setFont(df)
            self._draw_text_with_shadow(p, val_x, y + dm_m.ascent(), value, hex_to_qcolor(value_color), df)
            y += lh

        def _draw_divider():
            nonlocal y
            y += 4
            p.setPen(QPen(QColor(255, 255, 255, 20), 1))
            p.drawLine(x, y, vline_x, y)
            y += 4

        order = self._settings.window.module_order
        for module_name in order:
            if module_name == "CPU" and d.show_cpu:
                if d.show_cpu_header:
                    _draw_header("CPU", self._cpu_data.name, c.cpu_header, c.cpu_name)
                if d.show_cpu_usage and self._valid_fields.get("cpu_usage", False):
                    _draw_line("占用率", fmt_val(self._cpu_data.usage, ".1f", " %"), c.cpu_usage)

                # 频率
                if d.show_cpu_freq:
                    if self._cpu_data.frequency_avg is not None:
                        _draw_line("频率", fmt_val(self._cpu_data.frequency_avg, ".0f", " MHz"), c.cpu_freq)
                    elif self._cpu_data.frequency is not None:
                        _draw_line("频率", fmt_val(self._cpu_data.frequency, ".0f", " MHz"), c.cpu_freq)
                    # P/E 核心
                    if self._cpu_data.frequency_p_core_avg is not None and self._cpu_data.frequency_e_core_avg is not None:
                        if self._valid_fields.get("cpu_p_core_avg", False):
                            _draw_line("P-Core", f"{self._cpu_data.frequency_p_core_avg:.0f} MHz", c.cpu_p_core)
                        if self._valid_fields.get("cpu_e_core_avg", False) and self._cpu_data.frequency_e_core_avg is not None:
                            _draw_line("E-Core", f"{self._cpu_data.frequency_e_core_avg:.0f} MHz", c.cpu_e_core)

                if d.show_cpu_temp and self._valid_fields.get("cpu_temp", False):
                    _draw_line("温度", fmt_val(self._cpu_data.temperature, ".1f", " °C"), c.cpu_temp)
                if d.show_cpu_voltage and self._valid_fields.get("cpu_voltage", False):
                    _draw_line("电压", fmt_val(self._cpu_data.voltage, ".3f", " V"), c.cpu_voltage)
                if d.show_cpu_power and self._valid_fields.get("cpu_power", False):
                    _draw_line("功耗", fmt_val(self._cpu_data.power, ".1f", " W"), c.cpu_power)
                _draw_divider()

            elif module_name == "GPU" and d.show_gpu:
                if d.show_gpu_header:
                    gpu_name = self._settings.gpu_custom.custom_name or self._gpu_data.name
                    _draw_header("GPU", gpu_name, c.gpu_header, c.gpu_name)
                if d.show_gpu_usage and self._valid_fields.get("gpu_usage", False):
                    _draw_line("占用率", fmt_val(self._gpu_data.usage, ".1f", " %"), c.gpu_usage)
                if d.show_gpu_freq and self._valid_fields.get("gpu_freq", False):
                    _draw_line("频率", fmt_val(self._gpu_data.frequency, ".0f", " MHz"), c.gpu_freq)
                if d.show_gpu_temp and self._valid_fields.get("gpu_temp", False):
                    _draw_line("温度", fmt_val(self._gpu_data.temperature, ".0f", " °C"), c.gpu_temp)
                if d.show_gpu_voltage and self._valid_fields.get("gpu_voltage", False):
                    _draw_line("电压", fmt_val(self._gpu_data.voltage, ".3f", " V"), c.gpu_voltage)
                if d.show_gpu_power and self._valid_fields.get("gpu_power", False):
                    _draw_line("功耗", fmt_val(self._gpu_data.power, ".1f", " W"), c.gpu_power)
                if d.show_gpu_memory and self._valid_fields.get("gpu_memory", False):
                    if self._gpu_data.memory_used is not None and self._gpu_data.memory_total is not None:
                        _draw_line("显存", f"{self._gpu_data.memory_used:.0f} / {self._gpu_data.memory_total:.0f} MB", c.gpu_memory)
                _draw_divider()

            elif module_name == "Net" and d.show_net and self._net_data:
                if d.show_net_header:
                    _draw_header("网络", self._net_data.name, c.net_header, c.net_name)
                if d.show_net_upload and self._valid_fields.get("net_upload", False):
                    _draw_line("上行", format_speed(self._net_data.upload_speed), c.net_upload)
                if d.show_net_download and self._valid_fields.get("net_download", False):
                    _draw_line("下行", format_speed(self._net_data.download_speed), c.net_download)
                _draw_divider()

            elif module_name == "FPS" and d.show_fps and self._fps_data.available and not (d.hide_fps_below_60 and self._fps_data.fps <= 60):
                if d.show_fps_header:
                    fc = get_fps_color(self._fps_data.fps, self._settings)
                    p.setFont(self._fonts['fps_label'])
                    self._draw_text_with_shadow(p, lbl_x, y + self._metrics['fps_label'].ascent(), "FPS", fc, self._fonts['fps_label'])
                    y += self._metrics['fps_label'].height() + 2
                # 大号数值
                ff = self._fonts['fps_big']
                fm = self._metrics['fps_big']
                p.setFont(ff)
                val_color = hex_to_qcolor(c.fps_value)
                y += 2
                self._draw_text_with_shadow(p, lbl_x + 2, y + fm.ascent(), f"{self._fps_data.fps:.1f}", val_color, ff)
                y += fm.height() + 8
                if d.show_fps_1low:
                    p.setFont(df)
                    low_color = hex_to_qcolor(c.fps_1low)
                    self._draw_text_with_shadow(p, lbl_x, y + dm_m.ascent(), f"1%Low: {self._fps_data.fps_1pct_low:.1f}", low_color, df)
                    y += lh
                if d.show_fps_latency:
                    p.setFont(df)
                    lat_color = hex_to_qcolor(c.fps_latency)
                    self._draw_text_with_shadow(p, lbl_x, y + dm_m.ascent(), f"帧时间: {self._fps_data.frametime_avg:.2f} ms", lat_color, df)
                    y += lh

    # ---------- 水平绘制（按顺序迭代） ----------
    def _draw_horizontal(self, p, w, h):
        d = self._settings.display
        modules = []
        order = self._settings.window.module_order
        for name in order:
            if name == "CPU" and d.show_cpu:
                modules.append(("CPU", self._cpu_data, d, "cpu"))
            elif name == "GPU" and d.show_gpu:
                modules.append(("GPU", self._gpu_data, d, "gpu"))
            elif name == "Net" and d.show_net and self._net_data:
                modules.append(("网络", self._net_data, d, "net"))
            elif name == "FPS" and d.show_fps and self._fps_data.available and not (d.hide_fps_below_60 and self._fps_data.fps <= 60):
                modules.append(("FPS", self._fps_data, d, "fps"))

        if not modules:
            return

        pad = 8
        gap = 12
        col_w = self._calc_col_width()
        lbl_x = pad
        val_x = lbl_x + col_w + 6

        module_infos = []
        for name, data, d_obj, prefix in modules:
            w_mod, h_mod = self._calc_module_size_internal(name, data, d_obj, prefix,
                                                           self._fonts['label'], self._fonts['data'],
                                                           self._fonts['data_b'],
                                                           self._metrics['label'], self._metrics['data'],
                                                           self._metrics['data_b'],
                                                           self._metrics['data'].height() + 2,
                                                           pad, 6, col_w, lbl_x, val_x)
            module_infos.append((name, data, d_obj, prefix, w_mod, h_mod))

        cur_x = pad
        max_h = max(info[5] for info in module_infos) if module_infos else 20
        y_base = pad

        for name, data, d_obj, prefix, w_mod, h_mod in module_infos:
            self._draw_module(p, cur_x, y_base, w_mod, h_mod, name, data, d_obj, prefix,
                              self._fonts, self._metrics, self._valid_fields, self._settings)
            cur_x += w_mod + gap

    def _draw_module(self, p, x_start, y_start, w_mod, h_mod, name, data, d_obj, prefix, fonts, metrics, valid_fields, settings):
        dl = fonts['label']
        dm = fonts['data']
        db = fonts['data_b']
        dm_l = metrics['label']
        dm_m = metrics['data']
        dm_b = metrics['data_b']
        lh = dm_m.height() + 2
        pad = 8
        gap = 6
        col_w = self._calc_col_width()
        lbl_x = x_start + pad
        val_x = lbl_x + col_w + gap
        y = y_start + pad
        c = settings.colors
        d = d_obj

        def _draw_header(label, name_str, header_color, name_color):
            nonlocal y
            p.setFont(db)
            self._draw_text_with_shadow(p, lbl_x, y + dm_b.ascent(), label, hex_to_qcolor(header_color), db)
            hw = dm_b.horizontalAdvance(label) + gap
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x + hw, y + dm_l.ascent(), name_str, hex_to_qcolor(name_color), dl)
            y += lh

        def _draw_line(label, value, value_color):
            nonlocal y
            if value is None:
                return
            p.setFont(dl)
            self._draw_text_with_shadow(p, lbl_x, y + dm_l.ascent(), label, hex_to_qcolor(c.label_color), dl)
            p.setFont(dm)
            self._draw_text_with_shadow(p, val_x, y + dm_m.ascent(), value, hex_to_qcolor(value_color), dm)
            y += lh

        if prefix == "cpu":
            if d.show_cpu_header:
                _draw_header("CPU", data.name, c.cpu_header, c.cpu_name)
            if d.show_cpu_usage and valid_fields.get("cpu_usage", False) and data.usage is not None:
                _draw_line("占用率", fmt_val(data.usage, ".1f", " %"), c.cpu_usage)

            if d.show_cpu_freq:
                if data.frequency_avg is not None:
                    _draw_line("频率", fmt_val(data.frequency_avg, ".0f", " MHz"), c.cpu_freq)
                elif data.frequency is not None:
                    _draw_line("频率", fmt_val(data.frequency, ".0f", " MHz"), c.cpu_freq)
                # P/E
                if data.frequency_p_core_avg is not None and data.frequency_e_core_avg is not None:
                    if valid_fields.get("cpu_p_core_avg", False):
                        _draw_line("P-Core", f"{data.frequency_p_core_avg:.0f} MHz", c.cpu_p_core)
                    if valid_fields.get("cpu_e_core_avg", False) and data.frequency_e_core_avg is not None:
                        _draw_line("E-Core", f"{data.frequency_e_core_avg:.0f} MHz", c.cpu_e_core)

            if d.show_cpu_temp and valid_fields.get("cpu_temp", False) and data.temperature is not None:
                _draw_line("温度", fmt_val(data.temperature, ".1f", "°C"), c.cpu_temp)
            if d.show_cpu_voltage and valid_fields.get("cpu_voltage", False) and data.voltage is not None:
                _draw_line("电压", fmt_val(data.voltage, ".3f", " V"), c.cpu_voltage)
            if d.show_cpu_power and valid_fields.get("cpu_power", False) and data.power is not None:
                _draw_line("功耗", fmt_val(data.power, ".1f", " W"), c.cpu_power)

        elif prefix == "gpu":
            gpu_name = settings.gpu_custom.custom_name or data.name
            if d.show_gpu_header:
                _draw_header("GPU", gpu_name, c.gpu_header, c.gpu_name)
            if d.show_gpu_usage and valid_fields.get("gpu_usage", False) and data.usage is not None:
                _draw_line("占用率", fmt_val(data.usage, ".1f", " %"), c.gpu_usage)
            if d.show_gpu_freq and valid_fields.get("gpu_freq", False) and data.frequency is not None:
                _draw_line("频率", fmt_val(data.frequency, ".0f", " MHz"), c.gpu_freq)
            if d.show_gpu_temp and valid_fields.get("gpu_temp", False) and data.temperature is not None:
                _draw_line("温度", fmt_val(data.temperature, ".0f", "°C"), c.gpu_temp)
            if d.show_gpu_voltage and valid_fields.get("gpu_voltage", False) and data.voltage is not None:
                _draw_line("电压", fmt_val(data.voltage, ".3f", " V"), c.gpu_voltage)
            if d.show_gpu_power and valid_fields.get("gpu_power", False) and data.power is not None:
                _draw_line("功耗", fmt_val(data.power, ".1f", " W"), c.gpu_power)
            if d.show_gpu_memory and valid_fields.get("gpu_memory", False) and data.memory_used is not None and data.memory_total is not None and data.memory_total > 0:
                _draw_line("显存", f"{data.memory_used:.0f} / {data.memory_total:.0f} MB", c.gpu_memory)

        elif prefix == "net":
            if d.show_net_header:
                _draw_header("网络", data.name, c.net_header, c.net_name)
            if d.show_net_upload and valid_fields.get("net_upload", False) and data.upload_speed is not None:
                _draw_line("上行", format_speed(data.upload_speed), c.net_upload)
            if d.show_net_download and valid_fields.get("net_download", False) and data.download_speed is not None:
                _draw_line("下行", format_speed(data.download_speed), c.net_download)

        elif prefix == "fps":
            if d.show_fps_header:
                fc = get_fps_color(data.fps, settings)
                p.setFont(fonts['fps_label'])
                self._draw_text_with_shadow(p, lbl_x, y + metrics['fps_label'].ascent(), "FPS", fc, fonts['fps_label'])
                y += metrics['fps_label'].height() + 2
            ff = fonts['fps_big']
            fm = metrics['fps_big']
            p.setFont(ff)
            val_color = hex_to_qcolor(c.fps_value)
            y += 2
            self._draw_text_with_shadow(p, lbl_x + 2, y + fm.ascent(), f"{data.fps:.1f}", val_color, ff)
            y += fm.height() + 8
            if d.show_fps_1low:
                p.setFont(dm)
                low_color = hex_to_qcolor(c.fps_1low)
                self._draw_text_with_shadow(p, lbl_x, y + dm_m.ascent(), f"1%Low: {data.fps_1pct_low:.1f}", low_color, dm)
                y += lh
            if d.show_fps_latency:
                p.setFont(dm)
                lat_color = hex_to_qcolor(c.fps_latency)
                self._draw_text_with_shadow(p, lbl_x, y + dm_m.ascent(), f"帧时间: {data.frametime_avg:.2f} ms", lat_color, dm)
                y += lh

    # ---------- 阴影辅助 ----------
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

    # ---------- 更新数据 ----------
    def update_data(self, cpu, gpu, net=None, fps=None):
        if self._first_update:
            self._valid_fields["cpu_usage"] = cpu.usage is not None
            self._valid_fields["cpu_freq"] = cpu.frequency is not None
            self._valid_fields["cpu_freq_avg"] = cpu.frequency_avg is not None
            self._valid_fields["cpu_p_core_avg"] = cpu.frequency_p_core_avg is not None
            self._valid_fields["cpu_e_core_avg"] = cpu.frequency_e_core_avg is not None
            self._valid_fields["cpu_temp"] = cpu.temperature is not None
            self._valid_fields["cpu_voltage"] = cpu.voltage is not None
            self._valid_fields["cpu_power"] = cpu.power is not None
            self._valid_fields["gpu_usage"] = gpu.usage is not None
            self._valid_fields["gpu_freq"] = gpu.frequency is not None
            self._valid_fields["gpu_temp"] = gpu.temperature is not None
            self._valid_fields["gpu_voltage"] = gpu.voltage is not None
            self._valid_fields["gpu_power"] = gpu.power is not None
            self._valid_fields["gpu_memory"] = (gpu.memory_used is not None and
                                                gpu.memory_total is not None and
                                                gpu.memory_total > 0)
            if net:
                self._valid_fields["net_upload"] = net.upload_speed is not None
                self._valid_fields["net_download"] = net.download_speed is not None
            else:
                self._valid_fields["net_upload"] = False
                self._valid_fields["net_download"] = False
            self._first_update = False

        self._cpu_data = cpu
        self._gpu_data = gpu
        self._net_data = net
        if fps is not None:
            self._fps_data = fps
        new_sz = self._calc_size()
        if new_sz != self.maximumSize():
            self.setFixedSize(new_sz)
        self.update()

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
        self.update()

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._settings.window.pinned:
            self._mode = "move"
            self._drag_offset = event.globalPos() - self.pos()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self._mode == "move" and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._mode == "move":
            self._mode = None
            self._settings.window.x = self.pos().x()
            self._settings.window.y = self.pos().y()
            event.accept()
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.settings_requested.emit()
            event.accept()


# ============================================================
# 设置对话框（完整版，含布局、模块顺序、FPS隐藏选项）
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
        self._build_tab_net()
        self._build_tab_fps()
        self._build_tab_layout()
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

    # ---------- 外观标签页 ----------
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

    # ---------- 布局标签页 ----------
    def _build_tab_layout(self):
        lay = self._build_scroll_tab("布局")

        g_layout = QGroupBox("布局模式")
        l_layout = QFormLayout()
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["垂直", "水平"])
        self.layout_combo.currentIndexChanged.connect(self._apply_layout)
        l_layout.addRow("布局模式:", self.layout_combo)
        g_layout.setLayout(l_layout)
        lay.addWidget(g_layout)

        g_order = QGroupBox("模块顺序")
        v_order = QVBoxLayout()
        self.order_list = QListWidget()
        self.order_list.addItems(["CPU", "GPU", "Net", "FPS"])
        self.order_list.setDragEnabled(False)
        h_btn = QHBoxLayout()
        btn_up = QPushButton("上移")
        btn_up.clicked.connect(self._move_up)
        btn_down = QPushButton("下移")
        btn_down.clicked.connect(self._move_down)
        h_btn.addWidget(btn_up)
        h_btn.addWidget(btn_down)
        v_order.addWidget(self.order_list)
        v_order.addLayout(h_btn)
        g_order.setLayout(v_order)
        lay.addWidget(g_order)

        lay.addStretch()

    def _move_up(self):
        row = self.order_list.currentRow()
        if row > 0:
            item = self.order_list.takeItem(row)
            self.order_list.insertItem(row - 1, item)
            self.order_list.setCurrentRow(row - 1)
            self._apply_order()

    def _move_down(self):
        row = self.order_list.currentRow()
        if row < self.order_list.count() - 1:
            item = self.order_list.takeItem(row)
            self.order_list.insertItem(row + 1, item)
            self.order_list.setCurrentRow(row + 1)
            self._apply_order()

    def _apply_order(self):
        order = [self.order_list.item(i).text() for i in range(self.order_list.count())]
        self._settings.window.module_order = order
        self._apply_and_save()

    # ---------- CPU 标签页 ----------
    def _build_tab_cpu(self):
        lay = self._build_scroll_tab("CPU")
        g_show = QGroupBox("CPU 显示项")
        lc = QVBoxLayout()
        lc.setSpacing(3)
        self.show_cpu = QCheckBox("显示 CPU")
        self.show_cpu.stateChanged.connect(self._apply_display)
        self.show_cpu_header = QCheckBox("显示标题")
        self.show_cpu_header.stateChanged.connect(self._apply_display)
        self.show_cpu_usage = QCheckBox("占用率")
        self.show_cpu_usage.stateChanged.connect(self._apply_display)
        self.show_cpu_freq = QCheckBox("频率")
        self.show_cpu_freq.stateChanged.connect(self._apply_display)
        self.show_cpu_temp = QCheckBox("温度")
        self.show_cpu_temp.stateChanged.connect(self._apply_display)
        self.show_cpu_voltage = QCheckBox("电压")
        self.show_cpu_voltage.stateChanged.connect(self._apply_display)
        self.show_cpu_power = QCheckBox("功耗")
        self.show_cpu_power.stateChanged.connect(self._apply_display)
        for cb in [self.show_cpu, self.show_cpu_header, self.show_cpu_usage, self.show_cpu_freq,
                   self.show_cpu_temp, self.show_cpu_voltage, self.show_cpu_power]:
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

    # ---------- GPU 标签页 ----------
    def _build_tab_gpu(self):
        lay = self._build_scroll_tab("GPU")
        g_show = QGroupBox("GPU 显示项")
        lg = QVBoxLayout()
        lg.setSpacing(3)
        self.show_gpu = QCheckBox("显示 GPU")
        self.show_gpu.stateChanged.connect(self._apply_display)
        self.show_gpu_header = QCheckBox("显示标题")
        self.show_gpu_header.stateChanged.connect(self._apply_display)
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
        for cb in [self.show_gpu, self.show_gpu_header, self.show_gpu_usage, self.show_gpu_freq,
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

    # ---------- 网络标签页 ----------
    def _build_tab_net(self):
        lay = self._build_scroll_tab("网络")
        g_show = QGroupBox("网络显示项")
        ln = QVBoxLayout()
        ln.setSpacing(3)
        self.show_net = QCheckBox("显示网络")
        self.show_net.stateChanged.connect(self._apply_display)
        self.show_net_header = QCheckBox("显示标题")
        self.show_net_header.stateChanged.connect(self._apply_display)
        self.show_net_upload = QCheckBox("上行速率")
        self.show_net_upload.stateChanged.connect(self._apply_display)
        self.show_net_download = QCheckBox("下行速率")
        self.show_net_download.stateChanged.connect(self._apply_display)
        for cb in [self.show_net, self.show_net_header, self.show_net_upload, self.show_net_download]:
            ln.addWidget(cb)
        g_show.setLayout(ln)
        lay.addWidget(g_show)

        g_color = QGroupBox("颜色设置")
        form = QFormLayout()
        form.setSpacing(4)
        net_attrs = [
            ("网络标题", "net_header"),
            ("网络名称", "net_name"),
            ("上行速率", "net_upload"),
            ("下行速率", "net_download"),
        ]
        for label, attr in net_attrs:
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

    # ---------- FPS 标签页 ----------
    def _build_tab_fps(self):
        lay = self._build_scroll_tab("FPS")
        g_show = QGroupBox("FPS 显示项")
        lfps = QVBoxLayout()
        lfps.setSpacing(3)
        self.show_fps = QCheckBox("显示 FPS")
        self.show_fps.stateChanged.connect(self._apply_display)
        self.show_fps_header = QCheckBox("显示标题")
        self.show_fps_header.stateChanged.connect(self._apply_display)
        self.show_fps_1low = QCheckBox("1%Low")
        self.show_fps_1low.stateChanged.connect(self._apply_display)
        self.show_fps_latency = QCheckBox("帧时间")
        self.show_fps_latency.stateChanged.connect(self._apply_display)
        self.hide_fps_below_60 = QCheckBox("帧率 ≤ 60 时隐藏 FPS")
        self.hide_fps_below_60.stateChanged.connect(self._apply_display)
        for cb in [self.show_fps, self.show_fps_header, self.show_fps_1low, self.show_fps_latency, self.hide_fps_below_60]:
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
            ("帧时间", "fps_latency"),
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

    # ---------- 关于 ----------
    def _build_tab_about(self):
        lay = self._build_scroll_tab("关于")
        about_html = """
        <div style="font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; color: #E0E0E0; padding: 8px; line-height: 1.6;">
            <h2 style="color: #4A9EFF; text-align: center; margin-bottom: 4px;">Performance Monitor OSD</h2>
            <p style="text-align: center; color: #B0B0B0; font-size: 14px; margin-top: 0;">极简性能监控悬浮窗 &mdash; 版本 1.1</p>
            <hr style="border-color: #3A3A4A; margin: 12px 0;">

            <h3 style="color: #FFD700; margin-bottom: 4px;">📖 项目简介</h3>
            <p style="margin-top: 0; color: #D0D0D0;">
                一款专为游戏玩家和性能发烧友设计的实时硬件监控工具，以透明悬浮窗形式显示 CPU、GPU、网络及 FPS 关键指标。
                支持双布局、模块顺序调整、智能隐藏，具有较高自由度和DIY特性。
                <li><b>开源地址：</b> &mdash;> <a href="https://github.com/Xyhshell/performance-monitor-osd" style="color: #4A9EFF; text-decoration: none;">GitHub</a></li>
            </p>

            <h3 style="color: #FFD700; margin-bottom: 4px;">⚙️ 技术原理</h3>
            <ul style="margin-top: 4px; padding-left: 20px; color: #D0D0D0;">
                <li><b>硬件传感器</b>：通过 <code>LibreHardwareMonitor</code> + <code>pythonnet</code> 直接读取系统硬件传感器（温度、频率、电压、功耗、显存等）。</li>
                <li><b>FPS 采集</b>：基于 <code>PresentMon</code> 的 ETW 事件捕获，精确计算实时帧率、1% Low、0.1% Low 及帧时间。</li>
                <li><b>网络监控</b>：使用 <code>psutil</code> 获取网卡实时流量，自动过滤虚拟/未连接设备，速率自动换算 KB/s / MB/s。</li>
                <li><b>用户界面</b>：基于 <code>PyQt5</code> 开发，无边框透明窗口，支持拖拽、固定（鼠标穿透）、系统托盘控制。</li>
                <li><b>配置持久化</b>：所有设置（颜色、布局、显示项等）保存为 <code>settings.json</code>，重启自动恢复。</li>
            </ul>

            <h3 style="color: #FFD700; margin-bottom: 4px;">✨ 主要特性</h3>
            <ul style="margin-top: 4px; padding-left: 20px; color: #D0D0D0;">
                <li><b>CPU 监控</b> &mdash; 占用率、温度、频率（平均值 / P-Core / E-Core）【自动研判】、电压、功耗</li>
                <li><b>GPU 监控</b> &mdash; 占用率、温度、频率、显存使用量、电压、功耗</li>
                <li><b>网络监控</b> &mdash; 实时上行/下行速率（自动单位换算），累计传输量</li>
                <li><b>FPS 监控</b> &mdash; 实时帧率、1% Low、0.1% Low、帧时间（基于 PresentMon）</li>
                <li><b>智能隐藏</b> &mdash; 可选择在帧率 ≤ 60 时自动隐藏 FPS 区域，避免干扰</li>
                <li><b>双布局</b> &mdash; 纵向/横向自由切换，适应不同屏幕空间</li>
                <li><b>模块顺序</b> &mdash; 自由调整 CPU/GPU/网络/FPS 的显示顺序</li>
                <li><b>自定义主题</b> &mdash; 内置多种预设配色，所有颜色（标题、名称、数值）可单独调色</li>
                <li><b>固定模式</b> &mdash; 鼠标穿透，不受干扰；取消固定后仍可拖拽移动</li>
                <li><b>系统托盘</b> &mdash; 快速显示/隐藏、固定、设置、退出</li>
            </ul>

            <h3 style="color: #FFD700; margin-bottom: 4px;">🖥️ 兼容性</h3>
            <ul style="margin-top: 4px; padding-left: 20px; color: #D0D0D0;">
                <li><b>操作系统</b> &mdash; Windows 10 / 11（64 位）</li>
                <li><b>CPU</b> &mdash; Intel / AMD 主流处理器（需支持传感器读取）</li>
                <li><b>GPU</b> &mdash; NVIDIA（首选）、Intel 核显（部分传感器受限）</li>
                <li><b>FPS 采集</b> &mdash; 支持 DirectX 9/10/11/12 游戏（需以管理员身份运行 PresentMon）</li>
                <li><b>依赖</b> &mdash; Python 3.8+、PyQt5、psutil、pythonnet、LibreHardwareMonitorLib.dll、PresentMon.exe</li>
            </ul>

            <h3 style="color: #FFD700; margin-bottom: 4px;">📚 致谢</h3>
            <ul style="margin-top: 4px; padding-left: 20px; color: #D0D0D0;">
                <li><b>LibreHardwareMonitor</b> &mdash; 开源硬件监控库（<a href="https://github.com/LibreHardwareMonitor/LibreHardwareMonitor" style="color: #4A9EFF; text-decoration: none;">GitHub</a>）</li>
                <li><b>PresentMon</b> &mdash; Intel 开源的帧率分析工具（<a href="https://github.com/GameTechDev/PresentMon" style="color: #4A9EFF; text-decoration: none;">GitHub</a>）</li>
                <li><b>PyQt5 &amp; pythonnet</b> &mdash; 强大的 Python UI 与 .NET 互操作库</li>
                <li><b>psutil</b> &mdash; 跨平台系统信息库</li>
            </ul>

            <hr style="border-color: #3A3A4A; margin: 12px 0;">
            <p style="text-align: center; color: #888; font-size: 11px; margin: 4px 0;">
                Performance Monitor OSD &copy; 2026 jingmo &nbsp;|&nbsp; 开源许可：MIT
            </p>
            <p style="text-align: center; color: #666; font-size: 10px; margin: 0;">
                仅供学习与研究使用，请勿用于商业用途。
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

    # ---------- 应用函数 ----------
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

    def _apply_layout(self):
        idx = self.layout_combo.currentIndex()
        self._settings.window.layout_mode = "vertical" if idx == 0 else "horizontal"
        self._apply_and_save()

    def _apply_display(self):
        d = self._settings.display
        d.show_cpu = self.show_cpu.isChecked()
        d.show_cpu_header = self.show_cpu_header.isChecked()
        d.show_cpu_usage = self.show_cpu_usage.isChecked()
        d.show_cpu_freq = self.show_cpu_freq.isChecked()
        d.show_cpu_temp = self.show_cpu_temp.isChecked()
        d.show_cpu_voltage = self.show_cpu_voltage.isChecked()
        d.show_cpu_power = self.show_cpu_power.isChecked()
        d.show_gpu = self.show_gpu.isChecked()
        d.show_gpu_header = self.show_gpu_header.isChecked()
        d.show_gpu_usage = self.show_gpu_usage.isChecked()
        d.show_gpu_freq = self.show_gpu_freq.isChecked()
        d.show_gpu_temp = self.show_gpu_temp.isChecked()
        d.show_gpu_voltage = self.show_gpu_voltage.isChecked()
        d.show_gpu_power = self.show_gpu_power.isChecked()
        d.show_gpu_memory = self.show_gpu_memory.isChecked()
        d.show_net = self.show_net.isChecked()
        d.show_net_header = self.show_net_header.isChecked()
        d.show_net_upload = self.show_net_upload.isChecked()
        d.show_net_download = self.show_net_download.isChecked()
        d.show_fps = self.show_fps.isChecked()
        d.show_fps_header = self.show_fps_header.isChecked()
        d.show_fps_1low = self.show_fps_1low.isChecked()
        d.show_fps_latency = self.show_fps_latency.isChecked()
        d.hide_fps_below_60 = self.hide_fps_below_60.isChecked()
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

    def _load_settings(self):
        s = self._settings
        display_checkboxes = [
            self.show_cpu, self.show_cpu_header, self.show_cpu_usage, self.show_cpu_freq,
            self.show_cpu_temp, self.show_cpu_voltage, self.show_cpu_power,
            self.show_gpu, self.show_gpu_header, self.show_gpu_usage, self.show_gpu_freq,
            self.show_gpu_temp, self.show_gpu_voltage, self.show_gpu_power,
            self.show_gpu_memory,
            self.show_fps, self.show_fps_header, self.show_fps_1low, self.show_fps_latency,
            self.hide_fps_below_60,
            self.show_net, self.show_net_header, self.show_net_upload, self.show_net_download
        ]
        for cb in display_checkboxes:
            cb.blockSignals(True)

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
        self.layout_combo.blockSignals(True)
        self.order_list.blockSignals(True)

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

        layout_idx = 0 if s.window.layout_mode == "vertical" else 1
        self.layout_combo.setCurrentIndex(layout_idx)

        order = s.window.module_order
        self.order_list.clear()
        for name in order:
            self.order_list.addItem(name)

        shadow = s.shadow
        self.shadow_enabled.setChecked(shadow.enabled)
        self.shadow_color_btn.setStyleSheet(f"background-color: {shadow.color}; border: 1px solid #999; border-radius: 3px;")
        self.shadow_color_btn.setProperty("color", shadow.color)
        self.shadow_offset_x.setValue(shadow.offset_x)
        self.shadow_offset_y.setValue(shadow.offset_y)
        self.shadow_opacity.setValue(shadow.opacity)

        self.label_color_btn.setStyleSheet(f"background-color: {s.colors.label_color}; border: 1px solid #999; border-radius: 3px;")
        self.label_color_btn.setProperty("color", s.colors.label_color)

        d = s.display
        self.show_cpu.setChecked(d.show_cpu)
        self.show_cpu_header.setChecked(d.show_cpu_header)
        self.show_cpu_usage.setChecked(d.show_cpu_usage)
        self.show_cpu_freq.setChecked(d.show_cpu_freq)
        self.show_cpu_temp.setChecked(d.show_cpu_temp)
        self.show_cpu_voltage.setChecked(d.show_cpu_voltage)
        self.show_cpu_power.setChecked(d.show_cpu_power)
        self.show_gpu.setChecked(d.show_gpu)
        self.show_gpu_header.setChecked(d.show_gpu_header)
        self.show_gpu_usage.setChecked(d.show_gpu_usage)
        self.show_gpu_freq.setChecked(d.show_gpu_freq)
        self.show_gpu_temp.setChecked(d.show_gpu_temp)
        self.show_gpu_voltage.setChecked(d.show_gpu_voltage)
        self.show_gpu_power.setChecked(d.show_gpu_power)
        self.show_gpu_memory.setChecked(d.show_gpu_memory)
        self.show_fps.setChecked(d.show_fps)
        self.show_fps_header.setChecked(d.show_fps_header)
        self.show_fps_1low.setChecked(d.show_fps_1low)
        self.show_fps_latency.setChecked(d.show_fps_latency)
        self.hide_fps_below_60.setChecked(d.hide_fps_below_60)
        self.show_net.setChecked(d.show_net)
        self.show_net_header.setChecked(d.show_net_header)
        self.show_net_upload.setChecked(d.show_net_upload)
        self.show_net_download.setChecked(d.show_net_download)

        self._update_color_buttons()
        self.gpu_name.setText(s.gpu_custom.custom_name)

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
        self.layout_combo.blockSignals(False)
        self.order_list.blockSignals(False)

    def closeEvent(self, event):
        self._settings.save()
        event.accept()


# ============================================================
# 系统托盘（不变）
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