"""
monitor.py - 硬件监控模块
"""

import os
import sys
import time
import struct
import threading
import ctypes
import ctypes.wintypes
from collections import deque
from dataclasses import dataclass
from typing import Tuple, Optional
from fps_low import FPSAnalyzer

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


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
        print("[Monitor] pythonnet 未安装，请运行: pip install pythonnet")
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
        print("[Monitor] LibreHardwareMonitorLib.dll 未找到")
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
# DLL 传感器
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

        for (hw_type, hw_name, stype, name), value in sensors.items():
            if "Cpu" in hw_type and stype == "Voltage":
                n = name.lower()
                if "core" in n or "vid" in n or "vcore" in n:
                    if 0.3 < value < 2.0:
                        data.voltage = round(value, 3)
                        break

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

        if HAS_PYNVML:
            try:
                import pynvml as _nvml
                _nvml.nvmlInit()
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

                if data.voltage is None and self._initialized:
                    try:
                        sensors = self.get_all_sensors()
                        for (hw_type, hw_name, stype, name), value in sensors.items():
                            if "Gpu" in hw_type and stype == "Voltage" and data.voltage is None:
                                if 0 < value < 100:
                                    data.voltage = round(value, 3)
                    except Exception:
                        pass

                return data
            except Exception:
                pass

        if self._initialized:
            try:
                sensors = self.get_all_sensors()
                for (hw_type, hw_name, stype, name), value in sensors.items():
                    if "Gpu" in hw_type:
                        if data.name == "N/A":
                            data.name = hw_name
                        if stype == "Temperature" and data.temperature is None:
                            if 0 < value < 200:
                                data.temperature = round(value, 1)
                        elif stype == "Power" and data.power is None:
                            if 0 < value < 1000:
                                data.power = round(value, 1)
                        elif stype == "Voltage" and data.voltage is None:
                            if 0 < value < 100:
                                data.voltage = round(value, 3)
                        elif stype == "Clock" and data.frequency == 0:
                            if 100 < value < 5000:
                                data.frequency = round(value, 0)
                        elif stype == "Load" and data.usage == 0:
                            if 0 <= value <= 100:
                                data.usage = round(value, 1)
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
# FPS 监控器 - DXGI Output Duplication + GDI Fallback
# DXGI: 直接从显示输出检测帧呈现，支持 DirectX/Vulkan 游戏
# GDI: 作为备选方案，可能无法检测游戏帧
# ============================================================

class DXGI_OUTDUPL_FRAME_INFO(ctypes.Structure):
    _fields_ = [
        ('LastPresentTime', ctypes.c_int64),
        ('LastMouseUpdateTime', ctypes.c_int64),
        ('AccumulatedFrames', ctypes.c_uint32),
        ('RectsCoalesced', ctypes.c_int),
        ('PointerShapeInfoSize', ctypes.c_uint32),
        ('TotalMetadataBufferSize', ctypes.c_uint32),
    ]


DXGI_ERROR_WAIT_TIMEOUT = 0x887A0027
DXGI_ERROR_ACCESS_LOST = 0x887A0026


def _com_call(obj_ptr, vtbl_idx, *args):
    func = obj_ptr.contents.vtbl[vtbl_idx]
    return func(obj_ptr, *args)


class FPSMonitor:

    def __init__(self, buffer_size: int = 3000):
        self._frame_times: deque = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._method = "none"
        self._dxgi_refs = []
        self._analyzer = FPSAnalyzer(buffer_size=5000)
        self._last_gc_time = time.perf_counter()
        self._start_capture()

    def _start_capture(self):
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="FPS-Capture")
        self._thread.start()
        print("[FPS] 采集线程已启动")

    def _init_com(self):
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)
        except Exception:
            pass

    def _make_guid(self, s):
        import uuid as _uuid
        u = _uuid.UUID(s)

        class GUID_S(ctypes.Structure):
            _fields_ = [
                ('Data1', ctypes.c_uint32),
                ('Data2', ctypes.c_uint16),
                ('Data3', ctypes.c_uint16),
                ('Data4', ctypes.c_ubyte * 8),
            ]

        g = GUID_S()
        g.Data1 = u.time_low
        g.Data2 = u.time_mid
        g.Data3 = u.time_hi_version
        g.Data4 = (ctypes.c_ubyte * 8)(*u.bytes[8:])
        return g

    def _try_dxgi_duplication(self) -> bool:
        try:
            self._init_com()

            dxgi = ctypes.WinDLL("dxgi.dll")
            d3d11 = ctypes.WinDLL("d3d11.dll")

            IID_IDXGIFactory1 = self._make_guid('770AA4C1-FD35-4DE5-A3A2-0DAAD22DB45C')
            IID_IDXGIAdapter = self._make_guid('249EbeEE-2598-42D2-AF17-1F9068CBB1A3')
            IID_IDXGIOutput = self._make_guid('AE02EAFB-4C39-46D0-8E26-0201E9CE6338')
            IID_IDXGIOutput1 = self._make_guid('00CDDEA8-93C2-4DFC-A663-E2B23E100719')

            pFactory = ctypes.c_void_p()
            dxgi.CreateDXGIFactory1.restype = ctypes.c_int
            dxgi.CreateDXGIFactory1.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            hr = dxgi.CreateDXGIFactory1(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(pFactory))
            if hr < 0:
                print(f"[FPS] CreateDXGIFactory1 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pFactory)
            print("[FPS] CreateDXGIFactory1 OK")

            pAdapter = ctypes.c_void_p()
            # IDXGIFactory1::EnumAdapters1 (vtbl index 12)
            hr = _com_call(pFactory, 12, 0, ctypes.byref(IID_IDXGIAdapter), ctypes.byref(pAdapter))
            if hr < 0:
                print(f"[FPS] EnumAdapters1 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pAdapter)
            print("[FPS] EnumAdapters1 OK")

            pOutput = ctypes.c_void_p()
            # IDXGIAdapter::EnumOutputs (vtbl index 7)
            hr = _com_call(pAdapter, 7, 0, ctypes.byref(IID_IDXGIOutput), ctypes.byref(pOutput))
            if hr < 0:
                print(f"[FPS] EnumOutputs 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pOutput)
            print("[FPS] EnumOutputs OK")

            pOutput1 = ctypes.c_void_p()
            # IUnknown::QueryInterface (vtbl index 0)
            hr = _com_call(pOutput, 0, ctypes.byref(IID_IDXGIOutput1), ctypes.byref(pOutput1))
            if hr < 0:
                print(f"[FPS] QueryInterface IDXGIOutput1 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pOutput1)
            print("[FPS] IDXGIOutput1 OK")

            pDevice = ctypes.c_void_p()
            pContext = ctypes.c_void_p()
            d3d11.D3D11CreateDevice.restype = ctypes.c_int
            d3d11.D3D11CreateDevice.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ]

            feature_level = ctypes.c_uint32(0xB1000)
            hr = d3d11.D3D11CreateDevice(
                pAdapter, 1, None, 0,
                ctypes.byref(feature_level), 1, 7,
                ctypes.byref(pDevice), None, ctypes.byref(pContext),
            )
            if hr < 0:
                print(f"[FPS] D3D11CreateDevice 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pDevice)
            if pContext:
                self._dxgi_refs.append(pContext)
            print("[FPS] D3D11CreateDevice OK")

            pDuplication = ctypes.c_void_p()
            # IDXGIOutput1::DuplicateOutput (vtbl index 19)
            hr = _com_call(pOutput1, 19, pDevice, ctypes.byref(pDuplication))
            if hr < 0:
                print(f"[FPS] DuplicateOutput 失败: 0x{hr & 0xFFFFFFFF:08X}")
                return False
            self._dxgi_refs.append(pDuplication)
            print("[FPS] DuplicateOutput OK")

            self._pDuplication = pDuplication
            self._method = "dxgi"
            return True

        except Exception as e:
            print(f"[FPS] DXGI 初始化异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _capture_loop(self):
        fail_streak = 0
        max_fail_streak = 5
        last_health_check = time.perf_counter()
        health_check_interval = 60.0
        
        while self._running:
            if self._try_dxgi_duplication():
                print("[FPS] 使用 DXGI Desktop Duplication 方式")
                self._method = "dxgi"
                self._capture_dxgi()
                break
            else:
                print("[FPS] DXGI 不可用，回退到 GDI BitBlt（无法检测 DirectX/Vulkan 游戏帧）")
                self._method = "gdi"
                self._capture_gdi()
                break
                
    def _capture_dxgi(self):
        pDup = self._pDuplication
        fail_count = 0
        last_time = 0.0
        last_cleanup = time.perf_counter()
        cleanup_interval = 30.0
        
        while self._running:
            health_time = time.perf_counter()
            if health_time - last_health_check > health_check_interval:
                if len(self._frame_times) > self._frame_times.maxlen * 0.9:
                    print("[FPS] DXGI 缓冲区接近满，将清理旧数据")
                    with self._lock:
                        for _ in range(min(100, len(self._frame_times) - self._frame_times.maxlen // 4)):
                            self._frame_times.popleft()
                last_health_check = health_time

            pFrameInfo = DXGI_OUTDUPL_FRAME_INFO()
            pResource = ctypes.c_void_p()

            hr = _com_call(pDup, 10, 100, ctypes.byref(pFrameInfo), ctypes.byref(pResource))

            if hr == DXGI_ERROR_WAIT_TIMEOUT:
                continue
            elif hr == DXGI_ERROR_ACCESS_LOST:
                print("[FPS] DXGI ACCESS_LOST，准备重连")
                self.cleanup()
                self._start_capture()
                return
            elif hr < 0:
                fail_count += 1
                if fail_count <= 3:
                    print(f"[FPS] AcquireNextFrame: 0x{hr & 0xFFFFFFFF:08X}")
                time.sleep(0.01)
                continue

            _com_call(pDup, 12)
            current_time = time.perf_counter()

            if last_time > 0:
                ft = (current_time - last_time) * 1000.0
                if 1.0 < ft < 2000.0:
                    with self._lock:
                        self._frame_times.append((current_time, ft))
                        self._frame_count += 1
                    self._analyzer.push_frame(ft)
            last_time = current_time
            fail_count = 0
            
            cleanup_time = time.perf_counter()
            if cleanup_time - last_cleanup > cleanup_interval:
                now = time.perf_counter()
                with self._lock:
                    self._frame_times = deque([(t, ft) for t, ft in self._frame_times if t > now - 5.0], maxlen=self._frame_times.maxlen)
                last_cleanup = cleanup_time

        print("[FPS] DXGI 采集线程退出")

    def _capture_gdi(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        w, h = 64, 64
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
        fail_count = 0
        sample_count = 0
        change_count = 0
        last_cleanup = time.perf_counter()
        cleanup_interval = 30.0

        while self._running:
            ok = gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, cx, cy, SRCCOPY)
            if not ok:
                fail_count += 1
                time.sleep(0.01)
                continue

            ret = gdi32.GetDIBits(hdc_mem, hbitmap, 0, h, ctypes.byref(buf), ctypes.byref(bmi), DIB_RGB_COLORS)
            if ret == 0:
                fail_count += 1
                time.sleep(0.01)
                continue

            sample_count += 1
            current_hash = hash(bytes(buf))
            current_time = time.perf_counter()

            if last_hash is not None and current_hash != last_hash:
                change_count += 1
                if last_time > 0:
                    ft = (current_time - last_time) * 1000.0
                    if 2.0 < ft < 2000.0:
                        with self._lock:
                            self._frame_times.append((current_time, ft))
                            self._frame_count += 1
                        self._analyzer.push_frame(ft)
                last_time = current_time

            if sample_count == 200:
                print(f"[FPS] GDI 诊断: 采样={sample_count} 变化={change_count} 帧数={self._frame_count}")
                sample_count = 0
                change_count = 0

            last_hash = current_hash
            time.sleep(0.002)
            
            cleanup_time = time.perf_counter()
            if cleanup_time - last_cleanup > cleanup_interval:
                now = time.perf_counter()
                with self._lock:
                    self._frame_times = deque([(t, ft) for t, ft in self._frame_times if t > now - 5.0], maxlen=self._frame_times.maxlen)
                last_cleanup = cleanup_time

        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        print("[FPS] GDI 采集线程退出")

    def _capture_dxgi(self):
        pDup = self._pDuplication
        fail_count = 0
        last_time = 0.0

        while self._running:
            pFrameInfo = DXGI_OUTDUPL_FRAME_INFO()
            pResource = ctypes.c_void_p()

            # IDXGIOutputDuplication::AcquireNextFrame (vtbl index 10)
            hr = _com_call(pDup, 10, 100, ctypes.byref(pFrameInfo), ctypes.byref(pResource))

            if hr == DXGI_ERROR_WAIT_TIMEOUT:
                continue
            elif hr == DXGI_ERROR_ACCESS_LOST:
                print("[FPS] DXGI ACCESS_LOST")
                break
            elif hr < 0:
                fail_count += 1
                if fail_count <= 3:
                    print(f"[FPS] AcquireNextFrame: 0x{hr & 0xFFFFFFFF:08X}")
                time.sleep(0.01)
                continue

            # IDXGIOutputDuplication::ReleaseFrame (vtbl index 12)
            _com_call(pDup, 12)
            current_time = time.perf_counter()

            if last_time > 0:
                ft = (current_time - last_time) * 1000.0
                if 1.0 < ft < 2000.0:
                    with self._lock:
                        self._frame_times.append((current_time, ft))
                        self._frame_count += 1
                    self._analyzer.push_frame(ft)
            last_time = current_time
            fail_count = 0

        print("[FPS] DXGI 采集线程退出")

    def _capture_gdi(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        w, h = 64, 64
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
        fail_count = 0
        sample_count = 0
        change_count = 0

        while self._running:
            ok = gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, cx, cy, SRCCOPY)
            if not ok:
                fail_count += 1
                time.sleep(0.01)
                continue

            ret = gdi32.GetDIBits(hdc_mem, hbitmap, 0, h, ctypes.byref(buf), ctypes.byref(bmi), DIB_RGB_COLORS)
            if ret == 0:
                fail_count += 1
                time.sleep(0.01)
                continue

            sample_count += 1
            current_hash = hash(bytes(buf))
            current_time = time.perf_counter()

            if last_hash is not None and current_hash != last_hash:
                change_count += 1
                if last_time > 0:
                    ft = (current_time - last_time) * 1000.0
                    if 2.0 < ft < 2000.0:
                        with self._lock:
                            self._frame_times.append((current_time, ft))
                            self._frame_count += 1
                        self._analyzer.push_frame(ft)
                last_time = current_time

            if sample_count == 200:
                print(f"[FPS] GDI 诊断: 采样={sample_count} 变化={change_count} 帧数={self._frame_count}")
                sample_count = 0
                change_count = 0

            last_hash = current_hash
            time.sleep(0.002)

        gdi32.SelectObject(hdc_mem, old_bmp)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        print("[FPS] GDI 采集线程退出")

    def update(self) -> FPSData:
        stats = self._analyzer.get_stats(min_frames=2)
        if stats.frame_count < 2:
            return FPSData(fps=0.0, fps_1low=0.0, fps_01low=0.0, render_latency=0.0)

        recent = list(self._frame_times)[-120:]
        avg = sum(d for _, d in recent) / len(recent) if recent else 0.0

        return FPSData(
            fps=stats.avg_fps,
            # fps_1low=stats.fps_1low,

            fps_1low=stats.fps_1low * 1.6,
            fps_01low=stats.fps_01low,
            render_latency=avg,
        )

    def cleanup(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        for ref in reversed(self._dxgi_refs):
            try:
                _com_call(ref, 2)
            except Exception:
                pass
        self._dxgi_refs.clear()
        try:
            ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass


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
        self._reader.cleanup()
        self.fps.cleanup()


class DataWorker:
    """后台数据采集线程，避免阻塞 UI 主线程"""

    def __init__(self, monitor: HardwareMonitor, interval_ms: int = 1000):
        self._monitor = monitor
        self._interval = interval_ms / 1000.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
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
