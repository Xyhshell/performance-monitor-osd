"""
settings.py - 设置管理模块
"""

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


DEFAULT_CONFIG_FILENAME = "settings.json"


def get_config_path() -> str:
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DEFAULT_CONFIG_FILENAME)


THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "默认": {
        "cpu_header": "#4A9EFF", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#B4B4B4", "cpu_p_core": "#B4B4B4", "cpu_e_core": "#B4B4B4",
        "cpu_temp": "#B4B4B4", "cpu_voltage": "#B4B4B4", "cpu_power": "#B4B4B4",
        "gpu_header": "#FFD700", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#B4B4B4", "gpu_temp": "#B4B4B4", "gpu_voltage": "#B4B4B4",
        "gpu_power": "#B4B4B4", "gpu_memory": "#B4B4B4",
        "fps_header": "#00FF00", "fps_value": "#00FF00", "fps_1low": "#FFFF00", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "暗夜霓虹": {
        "cpu_header": "#00D4FF", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#00FFC8", "cpu_p_core": "#00FFC8", "cpu_e_core": "#00FFC8",
        "cpu_temp": "#00B4D8", "cpu_voltage": "#00B4D8", "cpu_power": "#00B4D8",
        "gpu_header": "#FF00FF", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FF69B4", "gpu_temp": "#CC66FF", "gpu_voltage": "#CC66FF",
        "gpu_power": "#CC66FF", "gpu_memory": "#CC66FF",
        "fps_header": "#00FF41", "fps_value": "#39FF14", "fps_1low": "#FFD700", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "清新": {
        "cpu_header": "#2E8B57", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#66CDAA", "cpu_p_core": "#66CDAA", "cpu_e_core": "#66CDAA",
        "cpu_temp": "#8FBC8F", "cpu_voltage": "#8FBC8F", "cpu_power": "#8FBC8F",
        "gpu_header": "#4682B4", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#87CEEB", "gpu_temp": "#B0C4DE", "gpu_voltage": "#B0C4DE",
        "gpu_power": "#B0C4DE", "gpu_memory": "#B0C4DE",
        "fps_header": "#3CB371", "fps_value": "#90EE90", "fps_1low": "#FFD700", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "赛博朋克": {
        "cpu_header": "#FF2E63", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FF6B6B", "cpu_p_core": "#FF6B6B", "cpu_e_core": "#FF6B6B",
        "cpu_temp": "#FF8E8E", "cpu_voltage": "#FF8E8E", "cpu_power": "#FF8E8E",
        "gpu_header": "#08D9D6", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#25B7D3", "gpu_temp": "#4ECDC4", "gpu_voltage": "#4ECDC4",
        "gpu_power": "#4ECDC4", "gpu_memory": "#4ECDC4",
        "fps_header": "#FFED4A", "fps_value": "#FFE66D", "fps_1low": "#FF2E63", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "极简白": {
        "cpu_header": "#CCCCCC", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#AAAAAA", "cpu_p_core": "#AAAAAA", "cpu_e_core": "#AAAAAA",
        "cpu_temp": "#999999", "cpu_voltage": "#999999", "cpu_power": "#999999",
        "gpu_header": "#CCCCCC", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#AAAAAA", "gpu_temp": "#999999", "gpu_voltage": "#999999",
        "gpu_power": "#999999", "gpu_memory": "#999999",
        "fps_header": "#FFFFFF", "fps_value": "#FFFFFF", "fps_1low": "#CCCCCC", "fps_latency": "#999999",
        "label_color": "#8C8C8C",
    },
    "烈焰": {
        "cpu_header": "#FF4500", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FF6347", "cpu_p_core": "#FF6347", "cpu_e_core": "#FF6347",
        "cpu_temp": "#FF7F50", "cpu_voltage": "#FF7F50", "cpu_power": "#FF7F50",
        "gpu_header": "#FF8C00", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FFA500", "gpu_temp": "#FFB347", "gpu_voltage": "#FFB347",
        "gpu_power": "#FFB347", "gpu_memory": "#FFB347",
        "fps_header": "#FFD700", "fps_value": "#FFFF00", "fps_1low": "#FF4500", "fps_latency": "#FFCCCB",
        "label_color": "#8C8C8C",
    },
    "薄荷": {
        "cpu_header": "#00C9A7", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#4ECDC4", "cpu_p_core": "#4ECDC4", "cpu_e_core": "#4ECDC4",
        "cpu_temp": "#88D8B0", "cpu_voltage": "#88D8B0", "cpu_power": "#88D8B0",
        "gpu_header": "#FF6F61", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FF8A80", "gpu_temp": "#FFB3B0", "gpu_voltage": "#FFB3B0",
        "gpu_power": "#FFB3B0", "gpu_memory": "#FFB3B0",
        "fps_header": "#FFD93D", "fps_value": "#FFC107", "fps_1low": "#FF6F61", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "星空": {
        "cpu_header": "#7B68EE", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#9B8FFF", "cpu_p_core": "#9B8FFF", "cpu_e_core": "#9B8FFF",
        "cpu_temp": "#B0A4FF", "cpu_voltage": "#B0A4FF", "cpu_power": "#B0A4FF",
        "gpu_header": "#FF8C42", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FFA86C", "gpu_temp": "#FFC49B", "gpu_voltage": "#FFC49B",
        "gpu_power": "#FFC49B", "gpu_memory": "#FFC49B",
        "fps_header": "#00E5FF", "fps_value": "#18FFFF", "fps_1low": "#FFD740", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "樱花": {
        "cpu_header": "#FF90BC", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FFB3C6", "cpu_p_core": "#FFB3C6", "cpu_e_core": "#FFB3C6",
        "cpu_temp": "#FFC2D1", "cpu_voltage": "#FFC2D1", "cpu_power": "#FFC2D1",
        "gpu_header": "#B8C0FF", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#C8D0FF", "gpu_temp": "#D8DFFF", "gpu_voltage": "#D8DFFF",
        "gpu_power": "#D8DFFF", "gpu_memory": "#D8DFFF",
        "fps_header": "#FFC8DD", "fps_value": "#FFB4C2", "fps_1low": "#FF90BC", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "深海": {
        "cpu_header": "#0077B6", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#0096C7", "cpu_p_core": "#0096C7", "cpu_e_core": "#0096C7",
        "cpu_temp": "#00B4D8", "cpu_voltage": "#00B4D8", "cpu_power": "#00B4D8",
        "gpu_header": "#48CAE4", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#90E0EF", "gpu_temp": "#ADE8F4", "gpu_voltage": "#ADE8F4",
        "gpu_power": "#ADE8F4", "gpu_memory": "#ADE8F4",
        "fps_header": "#CAF0F8", "fps_value": "#FFFFFF", "fps_1low": "#48CAE4", "fps_latency": "#90E0EF",
        "label_color": "#8C8C8C",
    },
    "琥珀": {
        "cpu_header": "#FFB703", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FFC838", "cpu_p_core": "#FFC838", "cpu_e_core": "#FFC838",
        "cpu_temp": "#FFD166", "cpu_voltage": "#FFD166", "cpu_power": "#FFD166",
        "gpu_header": "#FB5607", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FF7B3D", "gpu_temp": "#FF9E5E", "gpu_voltage": "#FF9E5E",
        "gpu_power": "#FF9E5E", "gpu_memory": "#FF9E5E",
        "fps_header": "#FFBE0B", "fps_value": "#FFD60A", "fps_1low": "#FB5607", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "极光": {
        "cpu_header": "#A855F7", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#C084FC", "cpu_p_core": "#C084FC", "cpu_e_core": "#C084FC",
        "cpu_temp": "#D8B4FE", "cpu_voltage": "#D8B4FE", "cpu_power": "#D8B4FE",
        "gpu_header": "#22D3EE", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#67E8F9", "gpu_temp": "#A5F3FC", "gpu_voltage": "#A5F3FC",
        "gpu_power": "#A5F3FC", "gpu_memory": "#A5F3FC",
        "fps_header": "#34D399", "fps_value": "#6EE7B7", "fps_1low": "#FBBF24", "fps_latency": "#B4B4B4",
        "label_color": "#8C8C8C",
    },
    "岩浆": {
        "cpu_header": "#DC2626", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#EF4444", "cpu_p_core": "#EF4444", "cpu_e_core": "#EF4444",
        "cpu_temp": "#F87171", "cpu_voltage": "#F87171", "cpu_power": "#F87171",
        "gpu_header": "#F97316", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FB923C", "gpu_temp": "#FDBA74", "gpu_voltage": "#FDBA74",
        "gpu_power": "#FDBA74", "gpu_memory": "#FDBA74",
        "fps_header": "#FACC15", "fps_value": "#FDE047", "fps_1low": "#DC2626", "fps_latency": "#FCA5A5",
        "label_color": "#8C8C8C",
    },
    "冰霜": {
        "cpu_header": "#67E8F9", "cpu_name": "#8C8C8C", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#A5F3FC", "cpu_p_core": "#A5F3FC", "cpu_e_core": "#A5F3FC",
        "cpu_temp": "#CFFAFE", "cpu_voltage": "#CFFAFE", "cpu_power": "#CFFAFE",
        "gpu_header": "#818CF8", "gpu_name": "#8C8C8C", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#A5B4FC", "gpu_temp": "#C7D2FE", "gpu_voltage": "#C7D2FE",
        "gpu_power": "#C7D2FE", "gpu_memory": "#C7D2FE",
        "fps_header": "#FFFFFF", "fps_value": "#F0F9FF", "fps_1low": "#67E8F9", "fps_latency": "#E0F2FE",
        "label_color": "#8C8C8C",
    },
}

THEME_NAMES: List[str] = list(THEME_PRESETS.keys())


@dataclass
class FontSettings:
    family: str = "隶书"
    size: int = 24


@dataclass
class ColorSettings:
    cpu_header: str = "#FF2E63"
    cpu_name: str = "#8C8C8C"
    cpu_usage: str = "#FFFFFF"
    cpu_freq: str = "#FF6B6B"
    cpu_p_core: str = "#FF6B6B"
    cpu_e_core: str = "#FF6B6B"
    cpu_temp: str = "#FF8E8E"
    cpu_voltage: str = "#FF8E8E"
    cpu_power: str = "#FF8E8E"
    gpu_header: str = "#08D9D6"
    gpu_name: str = "#8C8C8C"
    gpu_usage: str = "#FFFFFF"
    gpu_freq: str = "#25B7D3"
    gpu_temp: str = "#4ECDC4"
    gpu_voltage: str = "#4ECDC4"
    gpu_power: str = "#4ECDC4"
    gpu_memory: str = "#4ECDC4"
    fps_header: str = "#FFED4A"
    fps_value: str = "#FFE66D"
    fps_1low: str = "#FF2E63"
    fps_latency: str = "#B4B4B4"
    label_color: str = "#8C8C8C"


@dataclass
class DisplaySettings:
    show_cpu: bool = True
    show_cpu_usage: bool = True
    show_cpu_freq: bool = True
    show_cpu_p_core: bool = True
    show_cpu_e_core: bool = True
    show_cpu_temp: bool = True
    show_cpu_voltage: bool = True
    show_cpu_power: bool = True

    show_gpu: bool = True
    show_gpu_usage: bool = True
    show_gpu_freq: bool = True
    show_gpu_temp: bool = True
    show_gpu_voltage: bool = True
    show_gpu_power: bool = True
    show_gpu_memory: bool = True

    show_fps: bool = True
    show_fps_1low: bool = True
    show_fps_latency: bool = True


@dataclass
class WindowSettings:
    x: int = 1537
    y: int = 133
    opacity: float = 0.9
    update_interval: int = 1000
    show_background: bool = False
    background_opacity: int = 120
    pinned: bool = False


@dataclass
class GPUCustomSettings:
    custom_name: str = ""


@dataclass
class Settings:
    font: FontSettings = field(default_factory=FontSettings)
    colors: ColorSettings = field(default_factory=ColorSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    window: WindowSettings = field(default_factory=WindowSettings)
    gpu_custom: GPUCustomSettings = field(default_factory=GPUCustomSettings)
    theme_name: str = "赛博朋克"

    def apply_theme(self, name: str):
        if name not in THEME_PRESETS:
            return
        self.theme_name = name
        t = THEME_PRESETS[name]
        for k, v in t.items():
            if hasattr(self.colors, k):
                setattr(self.colors, k, v)

    def save(self, path: Optional[str] = None) -> bool:
        if path is None:
            path = get_config_path()
        try:
            data = asdict(self)
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Settings] 保存失败: {e}")
            return False

    @classmethod
    def load(cls, path: Optional[str] = None) -> 'Settings':
        if path is None:
            path = get_config_path()
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls._from_dict(data)
        except Exception as e:
            print(f"[Settings] 加载失败: {e}")
            return cls()

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        fd = data.get('font', {})
        font = FontSettings(
            family=fd.get('family', FontSettings.family),
            size=fd.get('size', FontSettings.size))

        cd = data.get('colors', {})
        colors = ColorSettings(**{k: cd.get(k, getattr(ColorSettings, k))
                                  for k in ColorSettings.__dataclass_fields__})

        dd = data.get('display', {})
        display_defaults = {k: getattr(DisplaySettings, k) for k in DisplaySettings.__dataclass_fields__}
        display = DisplaySettings(**{k: dd.get(k, display_defaults[k]) for k in display_defaults})

        wd = data.get('window', {})
        window = WindowSettings(
            x=wd.get('x', WindowSettings.x),
            y=wd.get('y', WindowSettings.y),
            opacity=wd.get('opacity', WindowSettings.opacity),
            update_interval=wd.get('update_interval', WindowSettings.update_interval),
            show_background=wd.get('show_background', WindowSettings.show_background),
            background_opacity=wd.get('background_opacity', WindowSettings.background_opacity),
            pinned=wd.get('pinned', WindowSettings.pinned))

        gd = data.get('gpu_custom', {})
        gpu_custom = GPUCustomSettings(
            custom_name=gd.get('custom_name', GPUCustomSettings.custom_name))

        theme_name = data.get('theme_name', Settings.theme_name)

        return cls(font=font, colors=colors, display=display,
                   window=window, gpu_custom=gpu_custom, theme_name=theme_name)
