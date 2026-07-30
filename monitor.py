"""
monitor.py - 跨平台硬件监控 + GDI FPS 采集（稳健版）
支持：Intel / AMD CPU & GPU，NVIDIA 独显，Intel 核显，AMD 核显/独显
FPS 采集：GDI 为主，dxcam 可选（若安装则优先）
"""

import os
import sys
import time
import threading
import ctypes
import ctypes.wintypes
from collections import deque
from dataclasses import dataclass
from typing import Tuple, Optional

# ---------- 可选 dxcam ----------
try:
    import dxcam
    HAS_DXCAM = True
except ImportError:
    HAS_DXCAM = False

from fps_low import FPSAnalyzer

# ---------- GDI 常量 ----------
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.wintypes.DWORD),
        ('biWidth', ctypes.wintypes.LONG),
        ('biHeight', ctypes.wintypes.LONG),
        ('biPlanes', ctypes.wintypes.WORD),
        ('biBitCount', ctypes.wintypes.WORD),
        ('biCompression', ctypes.wintypes.DWORD),
        ('biSizeImage', ctypes.wintypes.DWORD),
        ('biXPelsPerMeter', ctypes.wintypes.LONG),
        ('biYPelsPerMeter', ctypes.wintypes.LONG),
        ('biClrUsed', ctypes.wintypes.DWORD),
        ('biClrImportant', ctypes.wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', ctypes.wintypes.DWORD * 3),
    ]

# ---------- 依赖 ----------
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

HAS_DLL = False
_Computer = None

def _init_dll():
    global HAS_DLL, _Computer
    try:
        import clr
    except ImportError:
        print("[Monitor] pythonnet 未安装，硬件传感器将受限。请安装: pip install pythonnet")
        return False

    search_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "LibreHardwareMonitorLib.dll"),
        os.path.join(os.path.dirname(sys.executable), "LibreHardwareMonitorLib.dll"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "LibreHardwareMonitor", "LibreHardwareMonitorLib.dll"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "LibreHardwareMonitor", "LibreHardwareMonitorLib.dll"),
    ]

    dll_path = None
    for p in search_paths:
        if os.path.exists(p):
            dll_path = p
            break

    if not dll_path:
        print("[Monitor] LibreHardwareMonitorLib.dll 未找到，硬件传感器将不可用。")
        return False

    try:
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer
        _Computer = Computer
        HAS_DLL = True
        print(f"[Monitor] DLL 加载成功: {dll_path}")
        return True
    except Exception as e:
        print(f"[Monitor] DLL 加载失败: {e}")
        return False

# ---------- 数据结构 ----------
@dataclass
class CPUData:
    name: str = "CPU"
    frequency: float = 0.0
    freq_p_core: float = 0.0
    freq_e_core: float = 0.0
    usage: float = 0.0
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    power: Optional[float] = None

@dataclass
class GPUData:
    name: str = "N/A"
    frequency: float = 0.0
    usage: float = 0.0
    temperature: Optional[float] = None
    voltage: Optional[float] = None
    power: Optional[float] = None
    memory_used: float = 0.0
    memory_total: float = 0.0

@dataclass
class FPSData:
    fps: float = 0.0
    fps_1low: float = 0.0
    fps_01low: float = 0.0
    render_latency: float = 0.0

# ============================================================
# DLL 传感器 - 兼容 Intel / AMD / NVIDIA
# ============================================================
class DLLSensorReader:
    def __init__(self):
        self._computer = None
        self._initialized = False
        if not HAS_DLL:
            return
        try:
            c = _Computer()
            c.IsCpuEnabled = True
            c.IsGpuEnabled = True
            c.IsMotherboardEnabled = True
            c.IsStorageEnabled = False
            c.IsNetworkEnabled = False
            c.IsMemoryEnabled = False
            c.Open()
            self._computer = c
            self._initialized = True
            print("[DLLSensor] 初始化成功")
        except Exception as e:
            print(f"[DLLSensor] 初始化失败: {e}")

    def update(self):
        if not self._initialized or not self._computer:
            return
        try:
            for hw in self._computer.Hardware:
                hw.Update()
                for sub in hw.SubHardware:
                    sub.Update()
        except Exception:
            pass

    def get_all_sensors(self):
        result = {}
        if not self._initialized or not self._computer:
            return result
        try:
            for hw in self._computer.Hardware:
                hw_type = str(hw.HardwareType)
                hw_name = hw.Name
                for sensor in hw.Sensors:
                    if sensor.Value is None:
                        continue
                    key = (hw_type, hw_name, str(sensor.SensorType), sensor.Name)
                    result[key] = float(sensor.Value)
                for sub in hw.SubHardware:
                    for sensor in sub.Sensors:
                        if sensor.Value is None:
                            continue
                        key = (hw_type, hw_name, str(sensor.SensorType), sensor.Name)
                        result[key] = float(sensor.Value)
        except Exception:
            pass
        return result

    def get_cpu_data(self) -> CPUData:
        data = CPUData()
        # 使用 psutil 获取使用率和基础频率（即使 DLL 不可用也有数据）
        if HAS_PSUTIL:
            try:
                data.usage = psutil.cpu_percent(interval=None)
            except Exception:
                pass
            try:
                freq = psutil.cpu_freq()
                if freq:
                    data.frequency = freq.current
            except Exception:
                pass

        if not self._initialized:
            return data

        try:
            sensors = self.get_all_sensors()
        except Exception:
            return data

        # 获取 CPU 名称
        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type:
                data.name = hw_name
                break
        if data.name == "CPU" and HAS_PSUTIL:
            try:
                import platform
                data.name = platform.processor()
                if not data.name:
                    data.name = "CPU"
            except Exception:
                pass

        # 温度（优先 package/tctl/tdie）
        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type and stype == "Temperature":
                n = name.lower()
                if "package" in n or "tctl" in n or "tdie" in n or "average" in n:
                    if 0 < value < 200:
                        data.temperature = round(value, 1)
                        break
        if data.temperature is None:
            for (hw_type, hw_name, stype, name), value in sensors.items():
                if "Cpu" in hw_type and stype == "Temperature":
                    if 0 < value < 200:
                        data.temperature = round(value, 1)
                        break

        # 电压（core/vid/vcore）
        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type and stype == "Voltage":
                n = name.lower()
                if "core" in n or "vid" in n or "vcore" in n:
                    if 0.3 < value < 2.0:
                        data.voltage = round(value, 3)
                        break

        # 功耗（package/cpu）
        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type and stype == "Power":
                n = name.lower()
                if "package" in n or "cpu" in n:
                    if 0 < value < 500:
                        data.power = round(value, 1)
                        break
        if data.power is None:
            for (hw_type, hw_name, stype, name), value in sensors.items():
                if "Cpu" in hw_type and stype == "Power":
                    if 0 < value < 500:
                        data.power = round(value, 1)
                        break

        # 核心频率（区分 P/E 核）
        core_clocks = []
        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type and stype == "Clock":
                n = name.lower()
                if "core" in n and 100 < value < 10000:
                    core_clocks.append(value)

        if core_clocks:
            data.frequency = round(sum(core_clocks) / len(core_clocks), 0)
            if len(core_clocks) >= 2:
                clocks_sorted = sorted(core_clocks)
                max_gap = 0
                split_idx = len(clocks_sorted) // 2
                for i in range(len(clocks_sorted) - 1):
                    a, b = clocks_sorted[i], clocks_sorted[i + 1]
                    if b > 0:
                        gap = (b - a) / b
                        if gap > max_gap and gap > 0.15:
                            max_gap = gap
                            split_idx = i + 1
                e_clocks = clocks_sorted[:split_idx]
                p_clocks = clocks_sorted[split_idx:]
                if p_clocks:
                    data.freq_p_core = round(sum(p_clocks) / len(p_clocks), 0)
                if e_clocks:
                    data.freq_e_core = round(sum(e_clocks) / len(e_clocks), 0)
                if not e_clocks and p_clocks:
                    data.freq_p_core = data.frequency

        return data

    def get_gpu_data(self) -> GPUData:
        data = GPUData()

        # ---------- 优先使用 NVIDIA NVML ----------
        nvml_initialized = False
        if HAS_PYNVML:
            try:
                import pynvml as _nvml
                _nvml.nvmlInit()
                nvml_initialized = True
                h = _nvml.nvmlDeviceGetHandleByIndex(0)

                name = _nvml.nvmlDeviceGetName(h)
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                data.name = name

                data.usage = _nvml.nvmlDeviceGetUtilizationRates(h).gpu
                data.frequency = _nvml.nvmlDeviceGetClockInfo(h, _nvml.NVML_CLOCK_GRAPHICS)
                data.temperature = _nvml.nvmlDeviceGetTemperature(h, _nvml.NVML_TEMPERATURE_GPU)
                data.power = _nvml.nvmlDeviceGetPowerUsage(h) / 1000.0

                mem = _nvml.nvmlDeviceGetMemoryInfo(h)
                data.memory_used = mem.used / (1024 * 1024)
                data.memory_total = mem.total / (1024 * 1024)

                try:
                    data.voltage = _nvml.nvmlDeviceGetVoltage(h) / 1000.0
                except Exception:
                    pass

                _nvml.nvmlShutdown()
                # 如果有电压则直接返回（否则继续走 DLL 补全电压）
                if data.voltage is not None:
                    return data
            except Exception:
                if nvml_initialized:
                    try:
                        _nvml.nvmlShutdown()
                    except Exception:
                        pass

        # ---------- 回退到 DLL（支持 Intel/AMD 核显/独显） ----------
        if self._initialized:
            try:
                sensors = self.get_all_sensors()
                gpu_name_found = None
                temp_values = []
                power_values = []
                voltage_values = []
                clock_values = []
                load_values = []

                for (hw_type, hw_name, stype, name), value in sensors.items():
                    if "Gpu" in hw_type:
                        if gpu_name_found is None:
                            gpu_name_found = hw_name

                        # 温度
                        if stype == "Temperature" and 0 < value < 200:
                            temp_values.append(value)
                        # 功耗
                        elif stype == "Power" and 0 < value < 1000:
                            power_values.append(value)
                        # 电压（自动识别单位）
                        elif stype == "Voltage" or "voltage" in name.lower():
                            if 0 < value < 2.0:
                                voltage_values.append(value)
                            elif 100 < value < 2000:
                                voltage_values.append(value / 1000.0)
                        # 频率
                        elif stype == "Clock" and 100 < value < 5000:
                            clock_values.append(value)
                        # 负载
                        elif stype == "Load" and 0 <= value <= 100:
                            load_values.append(value)

                # 若未找到电压，尝试从任何传感器中找（备选）
                if not voltage_values:
                    for (hw_type, hw_name, stype, name), value in sensors.items():
                        if stype == "Voltage" or "voltage" in name.lower():
                            if 0 < value < 2.0:
                                voltage_values.append(value)
                            elif 100 < value < 2000:
                                voltage_values.append(value / 1000.0)
                            if voltage_values:
                                break

                if gpu_name_found and data.name == "N/A":
                    data.name = gpu_name_found
                if temp_values:
                    data.temperature = round(sum(temp_values) / len(temp_values), 1)
                if power_values:
                    data.power = round(sum(power_values) / len(power_values), 1)
                if voltage_values:
                    data.voltage = round(sum(voltage_values) / len(voltage_values), 3)
                if clock_values:
                    data.frequency = round(sum(clock_values) / len(clock_values), 0)
                if load_values:
                    data.usage = round(sum(load_values) / len(load_values), 1)

            except Exception:
                pass

        return data

    def cleanup(self):
        if self._initialized and self._computer:
            try:
                self._computer.Close()
            except Exception:
                pass

# ============================================================
# FPS 采集 - 智能选择 dxcam 或 GDI（永不报错）
# ============================================================
class FPSMonitor:
    def __init__(self, buffer_size: int = 3000):
        self._frame_times = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._frame_count = 0
        self._method = "none"
        self._analyzer = FPSAnalyzer(buffer_size=5000)
        self._camera = None
        self._use_dxcam = False
        self._start_capture()

    def _start_capture(self):
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="FPS-Capture")
        self._thread.start()
        print("[FPS] 采集线程已启动")

    def _capture_loop(self):
        # ---------- 尝试 dxcam（如果已安装） ----------
        if HAS_DXCAM:
            try:
                self._camera = dxcam.create(output_idx=0, output_color="BGR")
                # 等待最多 1.5 秒尝试获取一帧以验证可用性
                print("[FPS] dxcam 预热中...")
                start_wait = time.perf_counter()
                frame = None
                while time.perf_counter() - start_wait < 1.5 and self._running:
                    frame = self._camera.get_latest_frame()
                    if frame is not None:
                        break
                    time.sleep(0.01)
                if frame is not None:
                    self._use_dxcam = True
                    self._method = "dxcam"
                    print("[FPS] dxcam (DXGI) 捕获成功")
                    self._capture_dxcam()
                    return
                else:
                    print("[FPS] dxcam 未捕获到帧，回退 GDI")
            except Exception as e:
                print(f"[FPS] dxcam 不可用 ({e})，回退 GDI")
                self._camera = None

        # ---------- 回退到 GDI（稳定且兼容所有系统） ----------
        print("[FPS] 使用 GDI BitBlt 模式")
        self._method = "gdi"
        self._capture_gdi()

    # ---------- dxcam 采集 ----------
    def _capture_dxcam(self):
        last_time = 0.0
        self._last_cleanup = time.perf_counter()
        while self._running:
            try:
                frame = self._camera.get_latest_frame()
            except Exception:
                frame = None
            if frame is None:
                time.sleep(0.001)
                continue

            current_time = time.perf_counter()
            if last_time > 0:
                ft = (current_time - last_time) * 1000.0
                if 1.0 < ft < 2000.0:
                    with self._lock:
                        self._frame_times.append((current_time, ft))
                        self._frame_count += 1
                    self._analyzer.push_frame(ft)
            last_time = current_time

            # 定期清理
            if time.perf_counter() - self._last_cleanup > 30.0:
                with self._lock:
                    now = time.perf_counter()
                    self._frame_times = deque(
                        [(t, ft) for t, ft in self._frame_times if t > now - 5.0],
                        maxlen=self._frame_times.maxlen
                    )
                self._last_cleanup = time.perf_counter()

            time.sleep(0.001)

        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None
        print("[FPS] dxcam 采集线程退出")

    # ---------- GDI 采集（优化版） ----------
    def _capture_gdi(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        w, h = 256, 256
        cx = (sw - w) // 2
        cy = (sh - h) // 2
        print(f"[FPS] GDI 采集区域: ({cx},{cy}) {w}x{h}  屏幕: {sw}x{sh}")

        hdc_screen = user32.GetDC(0)
        if not hdc_screen:
            print("[FPS] GetDC(0) 失败")
            return
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        if not hbitmap:
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            return
        old_bmp = gdi32.SelectObject(hdc_mem, hbitmap)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        buf_size = w * h * 4
        buf = (ctypes.c_ubyte * buf_size)()
        last_hash = None
        last_time = 0.0
        sample_count = 0
        change_count = 0

        while self._running:
            try:
                if not gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, cx, cy, SRCCOPY):
                    time.sleep(0.001)
                    continue
                if not gdi32.GetDIBits(hdc_mem, hbitmap, 0, h, ctypes.byref(buf), ctypes.byref(bmi), DIB_RGB_COLORS):
                    time.sleep(0.001)
                    continue
            except Exception:
                time.sleep(0.001)
                continue

            sample_count += 1
            current_hash = hash(bytes(buf))
            current_time = time.perf_counter()

            if last_hash is not None and current_hash != last_hash:
                change_count += 1
                if last_time > 0:
                    ft = (current_time - last_time) * 1000.0
                    if 1.0 < ft < 2000.0:
                        with self._lock:
                            self._frame_times.append((current_time, ft))
                            self._frame_count += 1
                        self._analyzer.push_frame(ft)
                last_time = current_time

            if sample_count == 100:
                if change_count > 0:
                    print(f"[FPS] GDI 诊断: 采样={sample_count} 变化={change_count} 帧数={self._frame_count}")
                sample_count = 0
                change_count = 0

            last_hash = current_hash
            time.sleep(0.001)

        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        print("[FPS] GDI 采集线程退出")

    # ---------- 统计计算 ----------
    def update(self) -> FPSData:
        now = time.perf_counter()
        with self._lock:
            items = list(self._frame_times)

        window_10s = [ft for t, ft in items if now - t <= 10.0]
        window_300ms = [ft for t, ft in items if now - t <= 0.3]

        # 瞬时 FPS
        if len(window_300ms) >= 2:
            avg = sum(window_300ms) / len(window_300ms)
            std = (sum((x - avg) ** 2 for x in window_300ms) / len(window_300ms)) ** 0.5
            filtered = [x for x in window_300ms if abs(x - avg) <= 3 * std + 1.0]
            if filtered:
                final_avg = sum(filtered) / len(filtered)
                instant_fps = 1000.0 / final_avg if final_avg > 0 else 0.0
                render_latency = final_avg
            else:
                instant_fps = 1000.0 / avg if avg > 0 else 0.0
                render_latency = avg
        elif len(window_300ms) == 1:
            instant_fps = 1000.0 / window_300ms[0] if window_300ms[0] > 0 else 0.0
            render_latency = window_300ms[0]
        else:
            if len(window_10s) >= 2:
                avg = sum(window_10s) / len(window_10s)
                instant_fps = 1000.0 / avg if avg > 0 else 0.0
                render_latency = avg
            else:
                instant_fps = 0.0
                render_latency = 0.0

        # 1% Low & 0.1% Low
        if len(window_10s) >= 10:
            sorted_fts = sorted(window_10s, reverse=True)
            n = len(sorted_fts)
            count_1 = max(1, int(n * 0.01))
            avg_worst_1 = sum(sorted_fts[:count_1]) / count_1
            fps_1low = 1000.0 / avg_worst_1 if avg_worst_1 > 0 else 0.0

            count_01 = max(1, int(n * 0.001))
            avg_worst_01 = sum(sorted_fts[:count_01]) / count_01
            fps_01low = 1000.0 / avg_worst_01 if avg_worst_01 > 0 else 0.0
        else:
            fps_1low = 0.0
            fps_01low = 0.0

        return FPSData(
            fps=instant_fps,
            fps_1low=fps_1low,
            fps_01low=fps_01low,
            render_latency=render_latency,
        )

    def cleanup(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._camera = None

# ============================================================
# 主控制器
# ============================================================
class HardwareMonitor:
    def __init__(self):
        print("[Monitor] 初始化中...")
        _init_dll()
        self._reader = DLLSensorReader()
        self.fps = FPSMonitor()
        print("[Monitor] 初始化完成")

    def get_all_data(self) -> Tuple[CPUData, GPUData, FPSData]:
        try:
            self._reader.update()
        except Exception:
            pass
        try:
            cpu = self._reader.get_cpu_data()
        except Exception:
            cpu = CPUData()
        try:
            gpu = self._reader.get_gpu_data()
        except Exception:
            gpu = GPUData()
        try:
            fps = self.fps.update()
        except Exception:
            fps = FPSData()
        return cpu, gpu, fps

    def cleanup(self):
        try:
            self._reader.cleanup()
        except Exception:
            pass
        try:
            self.fps.cleanup()
        except Exception:
            pass

class DataWorker:
    def __init__(self, monitor: HardwareMonitor, interval_ms: int = 1000):
        self._monitor = monitor
        self._interval = interval_ms / 1000.0
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._cpu = CPUData()
        self._gpu = GPUData()
        self._fps = FPSData()
        self._start()

    def _start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DataWorker")
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                cpu, gpu, fps = self._monitor.get_all_data()
                with self._lock:
                    self._cpu = cpu
                    self._gpu = gpu
                    self._fps = fps
            except Exception:
                pass
            time.sleep(self._interval)

    def get_latest(self) -> Tuple[CPUData, GPUData, FPSData]:
        with self._lock:
            return self._cpu, self._gpu, self._fps

    def set_interval(self, interval_ms: int):
        self._interval = interval_ms / 1000.0

    def cleanup(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)