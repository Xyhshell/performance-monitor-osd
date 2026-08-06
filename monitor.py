"""
monitor.py - 硬件数据采集（多线程安全）
扩展：增加多种CPU频率获取方式
"""
import psutil
import socket
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from LibreHardwareMonitor import Hardware

@dataclass
class CPUData:
    name: str = ""
    usage: Optional[float] = None
    temperature: Optional[float] = None
    # ----- 频率字段 -----
    frequency_max: Optional[float] = None      # 所有核心频率最大值（原 frequency）
    frequency_avg: Optional[float] = None      # 所有核心频率平均值
    frequency_p_core_avg: Optional[float] = None  # P-Core平均频率（仅适用于Intel大小核）
    frequency_e_core_avg: Optional[float] = None  # E-Core平均频率
    # 保留旧字段以兼容，实际指向 frequency_max
    frequency: Optional[float] = field(default=None, repr=False)
    voltage: Optional[float] = None
    power: Optional[float] = None

    def __post_init__(self):
        # 如果未显式设置 frequency，则默认使用 frequency_max
        if self.frequency is None and self.frequency_max is not None:
            self.frequency = self.frequency_max
        elif self.frequency is None:
            self.frequency = None

@dataclass
class GPUData:
    name: str = ""
    usage: Optional[float] = None
    temperature: Optional[float] = None
    frequency: Optional[float] = None
    memory_total: Optional[float] = None
    memory_used: Optional[float] = None
    power: Optional[float] = None
    voltage: Optional[float] = None

@dataclass
class NetData:
    name: str = ""
    upload_speed: float = 0.0
    download_speed: float = 0.0

@dataclass
class FPSData:
    available: bool = False
    app: str = ""
    fps: float = 0.0
    fps_1pct_low: float = 0.0
    fps_0dot1pct_low: float = 0.0
    frametime_avg: float = 0.0
    frame_count: int = 0

class HardwareMonitor:
    def __init__(self):
        self.computer = Hardware.Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsNetworkEnabled = True
        self.computer.Open()
        self._old_net_io = psutil.net_io_counters(pernic=True)

    def update(self):
        for hardware in self.computer.Hardware:
            hardware.Update()

    def get_cpu_data(self) -> CPUData:
        cpu_hw = next((hw for hw in self.computer.Hardware if hw.HardwareType == Hardware.HardwareType.Cpu), None)
        if not cpu_hw:
            return CPUData()
        sensors = cpu_hw.Sensors
        def val(stype, sname=None):
            for s in sensors:
                if s.SensorType == stype and (sname is None or s.Name == sname):
                    return s.Value
            return None

        data = CPUData(name=cpu_hw.Name)
        data.usage = val(Hardware.SensorType.Load, "CPU Total")
        data.temperature = val(Hardware.SensorType.Temperature, "CPU Package")
        data.voltage = val(Hardware.SensorType.Voltage, "CPU Core")
        data.power = val(Hardware.SensorType.Power, "CPU Package")

        # ---------- 获取所有核心时钟传感器 ----------
        # 传感器名称通常为 "CPU Core #1"、"CPU Core #2" 等
        # 有些 CPU 可能会带有 "Efficient" 或 "Atom" 标记（Intel大小核），
        # 但不同系统可能不同，这里提供通用方法。
        core_clocks = []
        e_core_clocks = []
        for s in sensors:
            if s.SensorType == Hardware.SensorType.Clock and "Core" in s.Name:
                # 简单判断：名称中包含 "Efficient" 或 "Atom" 视为 E-Core
                if "Efficient" in s.Name or "Atom" in s.Name or "E-Core" in s.Name:
                    e_core_clocks.append(s.Value)
                else:
                    core_clocks.append(s.Value)

        # 如果未能区分，则将所有核心归入 core_clocks
        if not core_clocks and not e_core_clocks:
            core_clocks = [s.Value for s in sensors if s.SensorType == Hardware.SensorType.Clock and "Core" in s.Name]
            e_core_clocks = []

        # 计算频率
        if core_clocks:
            data.frequency_max = max(core_clocks)
            data.frequency_avg = sum(core_clocks) / len(core_clocks)
            # 如果有 E-Core，也计算其平均值
            if e_core_clocks:
                data.frequency_p_core_avg = data.frequency_avg
                data.frequency_e_core_avg = sum(e_core_clocks) / len(e_core_clocks)
            else:
                data.frequency_p_core_avg = data.frequency_avg
                data.frequency_e_core_avg = None
        else:
            data.frequency_max = None
            data.frequency_avg = None
            data.frequency_p_core_avg = None
            data.frequency_e_core_avg = None

        # 兼容旧字段：frequency 指向 frequency_max
        if data.frequency_max is not None:
            data.frequency = data.frequency_max
        else:
            data.frequency = None

        return data

    def get_gpu_data(self) -> GPUData:
        gpu_hw = next((hw for hw in self.computer.Hardware if hw.HardwareType == Hardware.HardwareType.GpuNvidia), None)
        if not gpu_hw:
            gpu_hw = next((hw for hw in self.computer.Hardware if hw.HardwareType == Hardware.HardwareType.GpuIntel), None)
        if not gpu_hw:
            return GPUData()
        sensors = gpu_hw.Sensors
        def val(stype, sname=None):
            for s in sensors:
                if s.SensorType == stype and (sname is None or s.Name == sname):
                    return s.Value
            return None
        data = GPUData(name=gpu_hw.Name)
        data.usage = val(Hardware.SensorType.Load, "GPU Core")
        data.temperature = val(Hardware.SensorType.Temperature, "GPU Core")
        data.frequency = val(Hardware.SensorType.Clock, "GPU Core")
        data.memory_total = val(Hardware.SensorType.SmallData, "GPU Memory Total")
        data.memory_used = val(Hardware.SensorType.SmallData, "GPU Memory Used")
        data.power = val(Hardware.SensorType.Power, "GPU Package")
        data.voltage = val(Hardware.SensorType.Voltage, "GPU Core")
        return data

    def get_net_data(self) -> List[NetData]:
        active = []
        ignore_keywords = ('vmware', 'virtual', 'tap', 'loopback', 'bluetooth', '本地连接')
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for name, stat in stats.items():
            if not stat.isup:
                continue
            has_ipv4 = False
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                        has_ipv4 = True
                        break
            if not has_ipv4:
                continue
            if any(kw in name.lower() for kw in ignore_keywords):
                continue
            active.append(name)
        current = psutil.net_io_counters(pernic=True)
        result = []
        for iface in active:
            if iface not in current or iface not in self._old_net_io:
                self._old_net_io[iface] = current[iface]
                continue
            sent = current[iface].bytes_sent - self._old_net_io[iface].bytes_sent
            recv = current[iface].bytes_recv - self._old_net_io[iface].bytes_recv
            result.append(NetData(name=iface, upload_speed=sent/1024, download_speed=recv/1024))
            self._old_net_io[iface] = current[iface]
        return result

    def close(self):
        self.computer.Close()