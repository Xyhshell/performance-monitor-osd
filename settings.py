import json
import os
import sys
import dataclasses
from dataclasses import dataclass, field, asdict, MISSING
from typing import Optional, Dict, Any, List

DEFAULT_CONFIG_FILENAME = "settings.json"

def get_config_path() -> str:
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DEFAULT_CONFIG_FILENAME)

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "赛博朋克": {
        "cpu_header": "#FF2E63", "cpu_name": "#FF6B6B", "cpu_usage": "#FFFFFF",
        "cpu_freq": "#FF8E8E", "cpu_temp": "#FFB3B3", "cpu_voltage": "#FF8E8E", "cpu_power": "#FF8E8E",
        "gpu_header": "#08D9D6", "gpu_name": "#4ECDC4", "gpu_usage": "#FFFFFF",
        "gpu_freq": "#4ECDC4", "gpu_temp": "#FFB3B3", "gpu_voltage": "#4ECDC4",
        "gpu_power": "#4ECDC4", "gpu_memory": "#4ECDC4",
        "fps_header": "#FFED4A", "fps_value": "#FFE66D", "fps_1low": "#FF2E63", "fps_latency": "#B4B4B4",
        "net_header": "#00E676", "net_name": "#8C8C8C",
        "net_upload": "#69F0AE", "net_download": "#FFAB40",
    },
}
THEME_NAMES = list(THEME_PRESETS.keys())

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
    net_header: str = "#00E676"
    net_name: str = "#8C8C8C"
    net_upload: str = "#69F0AE"
    net_download: str = "#FFAB40"

@dataclass
class LabelSettings:
    cpu_title: str = "CPU"
    gpu_title: str = "GPU"
    net_title: str = "网络"
    fps_title: str = "FPS"

    cpu_usage: str = "占用率"
    cpu_freq: str = "频率"
    cpu_freq_avg: str = "频率(avg)"
    cpu_temp: str = "温度"
    cpu_voltage: str = "电压"
    cpu_power: str = "功耗"

    gpu_usage: str = "占用率"
    gpu_freq: str = "频率"
    gpu_temp: str = "温度"
    gpu_voltage: str = "电压"
    gpu_power: str = "功耗"
    gpu_memory: str = "显存"

    net_upload: str = "上行"
    net_download: str = "下行"

    fps_1low: str = "1%Low"
    fps_latency: str = "帧时间"

@dataclass
class DisplaySettings:
    show_cpu: bool = True
    show_cpu_header: bool = True
    show_cpu_usage: bool = True
    show_cpu_freq: bool = True
    show_cpu_temp: bool = True
    show_cpu_voltage: bool = True
    show_cpu_power: bool = True

    show_gpu: bool = True
    show_gpu_header: bool = True
    show_gpu_usage: bool = True
    show_gpu_freq: bool = True
    show_gpu_temp: bool = True
    show_gpu_voltage: bool = True
    show_gpu_power: bool = True
    show_gpu_memory: bool = True

    show_net: bool = True
    show_net_header: bool = True
    show_net_upload: bool = True
    show_net_download: bool = True

    show_fps: bool = True
    show_fps_header: bool = True
    show_fps_1low: bool = True
    show_fps_latency: bool = True
    hide_fps_below_60: bool = False
    sync_osd_with_fps: bool = False

    gpu_selection_mode: str = "auto"   # "auto" 或 "custom"
    selected_gpu_indices: List[int] = field(default_factory=list)

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
    layout_mode: str = "vertical"
    module_order: List[str] = field(default_factory=lambda: ["CPU", "GPU", "Net", "FPS"])

@dataclass
class Settings:
    font: FontSettings = field(default_factory=FontSettings)
    colors: ColorSettings = field(default_factory=ColorSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    window: WindowSettings = field(default_factory=WindowSettings)
    shadow: ShadowSettings = field(default_factory=ShadowSettings)
    labels: LabelSettings = field(default_factory=LabelSettings)
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
        # ---------- 字体 ----------
        fd = data.get('font', {})
        font = FontSettings(
            family=fd.get('family', FontSettings.family),
            size=fd.get('size', FontSettings.size),
            bold=fd.get('bold', FontSettings.bold),
            weight=fd.get('weight', FontSettings.weight),
        )

        # ---------- 颜色 ----------
        cd = data.get('colors', {})
        # 使用类字段默认值作为后备
        color_fields = ColorSettings.__dataclass_fields__
        color_kwargs = {}
        for fname, fdef in color_fields.items():
            if fname in cd:
                color_kwargs[fname] = cd[fname]
            else:
                if fdef.default is not MISSING:
                    color_kwargs[fname] = fdef.default
                elif fdef.default_factory is not MISSING:
                    color_kwargs[fname] = fdef.default_factory()
                else:
                    color_kwargs[fname] = None
        colors = ColorSettings(**color_kwargs)

        # ---------- 显示 ----------
        dd = data.get('display', {})
        display_fields = DisplaySettings.__dataclass_fields__
        display_kwargs = {}
        for fname, fdef in display_fields.items():
            if fname in dd:
                display_kwargs[fname] = dd[fname]
            else:
                if fdef.default is not MISSING:
                    display_kwargs[fname] = fdef.default
                elif fdef.default_factory is not MISSING:
                    display_kwargs[fname] = fdef.default_factory()
                else:
                    display_kwargs[fname] = None
        # 兼容旧版本：将 "all" 转为 "auto"
        if display_kwargs.get('gpu_selection_mode') == 'all':
            display_kwargs['gpu_selection_mode'] = 'auto'
        display = DisplaySettings(**display_kwargs)

        # ---------- 窗口 ----------
        wd = data.get('window', {})
        window = WindowSettings(
            x=wd.get('x', WindowSettings.x),
            y=wd.get('y', WindowSettings.y),
            opacity=wd.get('opacity', WindowSettings.opacity),
            update_interval=wd.get('update_interval', WindowSettings.update_interval),
            show_background=wd.get('show_background', WindowSettings.show_background),
            background_opacity=wd.get('background_opacity', WindowSettings.background_opacity),
            pinned=wd.get('pinned', WindowSettings.pinned),
            layout_mode=wd.get('layout_mode', WindowSettings.layout_mode),
            module_order=wd.get('module_order', ["CPU", "GPU", "Net", "FPS"])
        )

        # ---------- 阴影 ----------
        sd = data.get('shadow', {})
        shadow = ShadowSettings(
            enabled=sd.get('enabled', ShadowSettings.enabled),
            color=sd.get('color', ShadowSettings.color),
            offset_x=sd.get('offset_x', ShadowSettings.offset_x),
            offset_y=sd.get('offset_y', ShadowSettings.offset_y),
            opacity=sd.get('opacity', ShadowSettings.opacity),
        )

        # ---------- 标签 ----------
        ld = data.get('labels', {})
        label_fields = LabelSettings.__dataclass_fields__
        label_kwargs = {}
        for fname, fdef in label_fields.items():
            if fname in ld:
                label_kwargs[fname] = ld[fname]
            else:
                if fdef.default is not MISSING:
                    label_kwargs[fname] = fdef.default
                elif fdef.default_factory is not MISSING:
                    label_kwargs[fname] = fdef.default_factory()
                else:
                    label_kwargs[fname] = None
        labels = LabelSettings(**label_kwargs)

        theme_name = data.get('theme_name', Settings.theme_name)

        return cls(
            font=font,
            colors=colors,
            display=display,
            window=window,
            shadow=shadow,
            labels=labels,
            theme_name=theme_name
        )