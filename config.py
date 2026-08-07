import os
import sys
from pathlib import Path

def _load_dll():
    current_dir = Path(__file__).parent
    dll_path = current_dir / "LibreHardwareMonitorLib.dll"
    if not dll_path.exists():
        dll_path = current_dir / "dll" / "LibreHardwareMonitorLib.dll"
    if not dll_path.exists():
        print("[Config] 错误: LibreHardwareMonitorLib.dll 未找到。")
        sys.exit(1)
    os.environ["PATH"] = str(current_dir) + ";" + os.environ.get("PATH", "")
    try:
        import clr
        clr.AddReference(str(dll_path))
        from LibreHardwareMonitor.Hardware import Computer
        global Computer
        Computer = Computer
        print("[Config] .NET 运行时库加载成功")
    except ImportError:
        print("[Config] 错误: 请先安装pythonnet: pip install pythonnet")
        sys.exit(1)
    except Exception as e:
        print(f"[Config] 错误: {e}")
        sys.exit(1)

_load_dll()

def setup_environment():
    pass