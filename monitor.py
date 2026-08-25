"""
monitor.py - 硬件数据采集（多线程安全）
支持多 GPU 检测
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
    frequency_max: Optional[float] = None
    frequency_avg: Optional[float] = None
    frequency: Optional[float] = field(default=None, repr=False)
    voltage: Optional[float] = None
    power: Optional[float] = None

    def __post_init__(self):
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

        core_clocks = [s.Value for s in sensors if s.SensorType == Hardware.SensorType.Clock and "Core" in s.Name and s.Value is not None]
        if core_clocks:
            data.frequency_max = max(core_clocks)
            data.frequency_avg = sum(core_clocks) / len(core_clocks)
            data.frequency = data.frequency_max
        else:
            data.frequency_max = None
            data.frequency_avg = None
            data.frequency = None

        return data

    def get_all_gpu_data(self) -> List[GPUData]:
        gpu_list = []
        nvidia_hw = [hw for hw in self.computer.Hardware if hw.HardwareType == Hardware.HardwareType.GpuNvidia]
        if nvidia_hw:
            gpu_list.extend(nvidia_hw)
        intel_hw = [hw for hw in self.computer.Hardware if hw.HardwareType == Hardware.HardwareType.GpuIntel]
        if intel_hw:
            gpu_list.extend(intel_hw)

        result = []
        for gpu_hw in gpu_list:
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
            result.append(data)
        return result

    def get_gpu_data(self) -> GPUData:
        gpus = self.get_all_gpu_data()
        return gpus[0] if gpus else GPUData()

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