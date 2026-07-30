"""
settings.py - 纯粹配置定义（无业务逻辑）
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

# ---------- 主题（仅颜色）----------
THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "赛博朋克": {
        "cpu_header": "#FF2E63", "cpu_name": "#FF6B6B", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FF8E8E", "cpu_p_core": "#FF8E8E", "cpu_e_core": "#FF8E8E",
        "cpu_temp": "#FFB3B3", "cpu_voltage": "#FF8E8E", "cpu_power": "#FF8E8E",
        "gpu_header": "#08D9D6", "gpu_name": "#4ECDC4", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#4ECDC4", "gpu_temp": "#FFB3B3", "gpu_voltage": "#4ECDC4",
        "gpu_power": "#4ECDC4", "gpu_memory": "#4ECDC4",
        "fps_header": "#FFED4A", "fps_value": "#FFE66D", "fps_1low": "#FF2E63", "fps_latency": "#B4B4B4",
    },
    "深海蓝调": {
        "cpu_header": "#4A9EFF", "cpu_name": "#A0C4FF", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#B0D4FF", "cpu_p_core": "#B0D4FF", "cpu_e_core": "#B0D4FF",
        "cpu_temp": "#FFB3B3", "cpu_voltage": "#B0D4FF", "cpu_power": "#B0D4FF",
        "gpu_header": "#FFD700", "gpu_name": "#FFE082", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FFE082", "gpu_temp": "#FFB3B3", "gpu_voltage": "#FFE082",
        "gpu_power": "#FFE082", "gpu_memory": "#FFE082",
        "fps_header": "#00E676", "fps_value": "#69F0AE", "fps_1low": "#FFAB40", "fps_latency": "#B0BEC5",
    },
    "暗夜极光": {
        "cpu_header": "#7C4DFF", "cpu_name": "#B388FF", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#D1C4E9", "cpu_p_core": "#D1C4E9", "cpu_e_core": "#D1C4E9",
        "cpu_temp": "#FF8A80", "cpu_voltage": "#D1C4E9", "cpu_power": "#D1C4E9",
        "gpu_header": "#18FFFF", "gpu_name": "#80DEEA", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#80DEEA", "gpu_temp": "#FF8A80", "gpu_voltage": "#80DEEA",
        "gpu_power": "#80DEEA", "gpu_memory": "#80DEEA",
        "fps_header": "#FFEA00", "fps_value": "#FFF59D", "fps_1low": "#FF6E40", "fps_latency": "#B0BEC5",
    },
    "翠绿清韵": {
        "cpu_header": "#00C853", "cpu_name": "#69F0AE", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#A5D6A7", "cpu_p_core": "#A5D6A7", "cpu_e_core": "#A5D6A7",
        "cpu_temp": "#FFAB91", "cpu_voltage": "#A5D6A7", "cpu_power": "#A5D6A7",
        "gpu_header": "#40C4FF", "gpu_name": "#80D8FF", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#80D8FF", "gpu_temp": "#FFAB91", "gpu_voltage": "#80D8FF",
        "gpu_power": "#80D8FF", "gpu_memory": "#80D8FF",
        "fps_header": "#FFD740", "fps_value": "#FFE082", "fps_1low": "#FF6E40", "fps_latency": "#B0BEC5",
    },
    "琥珀暖阳": {
        "cpu_header": "#FF8F00", "cpu_name": "#FFD54F", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FFE082", "cpu_p_core": "#FFE082", "cpu_e_core": "#FFE082",
        "cpu_temp": "#FF8A80", "cpu_voltage": "#FFE082", "cpu_power": "#FFE082",
        "gpu_header": "#FF5252", "gpu_name": "#FF8A80", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#FF8A80", "gpu_temp": "#FF8A80", "gpu_voltage": "#FF8A80",
        "gpu_power": "#FF8A80", "gpu_memory": "#FF8A80",
        "fps_header": "#69F0AE", "fps_value": "#B9F6CA", "fps_1low": "#FFD740", "fps_latency": "#B0BEC5",
    },
    "樱花粉黛": {
        "cpu_header": "#F48FB1", "cpu_name": "#F8BBD0", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#F8BBD0", "cpu_p_core": "#F8BBD0", "cpu_e_core": "#F8BBD0",
        "cpu_temp": "#FF8A80", "cpu_voltage": "#F8BBD0", "cpu_power": "#F8BBD0",
        "gpu_header": "#90CAF9", "gpu_name": "#BBDEFB", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#BBDEFB", "gpu_temp": "#FF8A80", "gpu_voltage": "#BBDEFB",
        "gpu_power": "#BBDEFB", "gpu_memory": "#BBDEFB",
        "fps_header": "#FFD740", "fps_value": "#FFE082", "fps_1low": "#F48FB1", "fps_latency": "#B0BEC5",
    },
    "极简银灰": {
        "cpu_header": "#78909C", "cpu_name": "#B0BEC5", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#CFD8DC", "cpu_p_core": "#CFD8DC", "cpu_e_core": "#CFD8DC",
        "cpu_temp": "#FFAB91", "cpu_voltage": "#CFD8DC", "cpu_power": "#CFD8DC",
        "gpu_header": "#78909C", "gpu_name": "#B0BEC5", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#CFD8DC", "gpu_temp": "#FFAB91", "gpu_voltage": "#CFD8DC",
        "gpu_power": "#CFD8DC", "gpu_memory": "#CFD8DC",
        "fps_header": "#78909C", "fps_value": "#B0BEC5", "fps_1low": "#FFAB91", "fps_latency": "#90A4AE",
    },
    "冰霜": {
        "cpu_header": "#4DD0E1", "cpu_name": "#80DEEA", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#B2EBF2", "cpu_p_core": "#B2EBF2", "cpu_e_core": "#B2EBF2",
        "cpu_temp": "#FFAB91", "cpu_voltage": "#B2EBF2", "cpu_power": "#B2EBF2",
        "gpu_header": "#B39DDB", "gpu_name": "#D1C4E9", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#D1C4E9", "gpu_temp": "#FFAB91", "gpu_voltage": "#D1C4E9",
        "gpu_power": "#D1C4E9", "gpu_memory": "#D1C4E9",
        "fps_header": "#FFD740", "fps_value": "#FFE082", "fps_1low": "#FF6E40", "fps_latency": "#B0BEC5",
    },
}
THEME_NAMES = list(THEME_PRESETS.keys())

# ---------- 数据类 ----------
@dataclass
class FontSettings:
    family: str = "Microsoft YaHei"
    size: int = 18
    bold: bool = False
    weight: int = 75

@dataclass
class ColorSettings:
    label_color: str = "#66b5ff"
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
class ShadowSettings:
    enabled: bool = True
    color: str = "#000000"
    offset_x: int = 1
    offset_y: int = 1
    opacity: int = 30

@dataclass
class WindowSettings:
    x: int = 1829
    y: int = 152
    opacity: float = 0.9
    update_interval: int = 800
    show_background: bool = True
    background_opacity: int = 180
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
    shadow: ShadowSettings = field(default_factory=ShadowSettings)
    gpu_custom: GPUCustomSettings = field(default_factory=GPUCustomSettings)
    theme_name: str = "赛博朋克"

    def apply_theme(self, name: str):
        if name not in THEME_PRESETS:
            return
        self.theme_name = name
        for k, v in THEME_PRESETS[name].items():
            if hasattr(self.colors, k) and k != "label_color":
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
            size=fd.get('size', FontSettings.size),
            bold=fd.get('bold', FontSettings.bold),
            weight=fd.get('weight', FontSettings.weight),
        )
        cd = data.get('colors', {})
        colors = ColorSettings(**{k: cd.get(k, getattr(ColorSettings, k)) for k in ColorSettings.__dataclass_fields__})
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
        gpu_custom = GPUCustomSettings(custom_name=gd.get('custom_name', GPUCustomSettings.custom_name))
        sd = data.get('shadow', {})
        shadow = ShadowSettings(
            enabled=sd.get('enabled', ShadowSettings.enabled),
            color=sd.get('color', ShadowSettings.color),
            offset_x=sd.get('offset_x', ShadowSettings.offset_x),
            offset_y=sd.get('offset_y', ShadowSettings.offset_y),
            opacity=sd.get('opacity', ShadowSettings.opacity),
        )
        theme_name = data.get('theme_name', Settings.theme_name)
        return cls(font=font, colors=colors, display=display,
                   window=window, gpu_custom=gpu_custom,
                   shadow=shadow, theme_name=theme_name)