"""
fps_monitor.py - 独立 PresentMon FPS 采集器（增强版）
- 自动重启机制
- 进程状态检查
- 强制清理
"""
import os
import sys
import csv
import subprocess
import threading
import time
from collections import deque
from typing import Dict, Any, Optional

class FPSMonitor:
    def __init__(self, exe_path: Optional[str] = None):
        self.exe_path = self._find_executable(exe_path)
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self._frametimes = deque(maxlen=180)
        self._last_app = ""
        self._last_frame_time = 0.0
        self._lock = threading.Lock()
        self._restart_count = 0
        self._max_restarts = 3  # 最大重启次数，防止无限循环

    @staticmethod
    def _find_executable(explicit_path: Optional[str]) -> Optional[str]:
        if explicit_path and os.path.exists(explicit_path):
            return os.path.abspath(explicit_path)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths = [script_dir, os.path.dirname(script_dir), os.path.join(os.path.dirname(script_dir), "bin")]
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            search_paths.append(path_dir.strip('"'))
        for base_dir in search_paths:
            for name in ["PresentMon-x64.exe", "PresentMon.exe"]:
                full = os.path.join(base_dir, name)
                if os.path.isfile(full):
                    return full
        return None

    def open(self) -> bool:
        """启动 PresentMon 进程，返回是否成功"""
        if not self.exe_path:
            print("[FPSMonitor] 错误: PresentMon.exe 未找到")
            return False
        if self._process is not None and self._process.poll() is None:
            # 进程已在运行
            return True

        cmd = [
            self.exe_path,
            "--no_csv", "--output_stdout", "--stop_existing_session",
            "--session_name", "myosd_fps", "--no_console_stats",
            "--exclude", "dwm.exe", "--exclude", "explorer.exe",
            "--exclude", "steamwebhelper.exe", "--exclude", "chrome.exe",
            "--exclude", "msedge.exe", "--exclude", "firefox.exe",
        ]
        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            print(f"[FPSMonitor] PresentMon 启动成功 (PID: {self._process.pid})")
            self._restart_count = 0
            return True
        except Exception as e:
            print(f"[FPSMonitor] 启动失败: {e}")
            return False

    def close(self):
        """终止 PresentMon 进程并清理资源"""
        self._running = False
        if self._process:
            try:
                if self._process.poll() is None:  # 进程还在运行
                    self._process.terminate()
                    self._process.wait(timeout=3)
                    print("[FPSMonitor] PresentMon 已终止")
                else:
                    print("[FPSMonitor] PresentMon 已自行退出")
            except Exception as e:
                try:
                    self._process.kill()
                except:
                    pass
                print(f"[FPSMonitor] 强制结束进程: {e}")
            self._process = None
        # 等待读取线程结束（最多1秒）
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
        self._reader_thread = None

    def is_running(self) -> bool:
        """检查 PresentMon 进程是否仍在运行"""
        if self._process is None:
            return False
        return self._process.poll() is None

    def restart(self) -> bool:
        """重启 PresentMon"""
        print("[FPSMonitor] 尝试重启 PresentMon...")
        self.close()
        time.sleep(0.5)
        self._frametimes.clear()
        self._last_frame_time = 0.0
        return self.open()

    def _read_loop(self):
        if not self._process or not self._process.stdout:
            return
        reader = csv.DictReader(self._process.stdout)
        if not reader.fieldnames:
            print("[FPSMonitor] 警告：未获取到 CSV 列头")
            return
        has_ms = "MsBetweenPresents" in reader.fieldnames
        has_ft = "FrameTime" in reader.fieldnames
        if not has_ms and not has_ft:
            print("[FPSMonitor] 警告：找不到帧时间字段")
            return
        for row in reader:
            if not self._running:
                break
            try:
                if has_ms and row.get("MsBetweenPresents"):
                    ft = float(row["MsBetweenPresents"])
                elif has_ft and row.get("FrameTime"):
                    ft = float(row["FrameTime"])
                else:
                    continue
                if ft <= 0 or ft > 500:
                    continue
                with self._lock:
                    self._frametimes.append(ft)
                    self._last_frame_time = time.time()
                    if row.get("Application"):
                        self._last_app = row["Application"]
            except (ValueError, KeyError):
                continue

    def get_fps_info(self) -> Dict[str, Any]:
        with self._lock:
            # 检查进程是否还在，若不在则尝试重启
            if not self.is_running() and self._running:
                print("[FPSMonitor] PresentMon 进程意外退出，尝试重启")
                self.restart()

            # 如果 5 秒没有新帧，且进程还在，可能游戏未运行或过滤问题，尝试重启
            if self.is_running() and time.time() - self._last_frame_time > 5.0 and len(self._frametimes) > 0:
                print("[FPSMonitor] 长时间无新帧，尝试重启 PresentMon")
                self.restart()

            # 清除超时数据（3秒无帧视为游戏停止）
            if time.time() - self._last_frame_time > 3.0:
                self._frametimes.clear()
                self._last_app = ""

            if len(self._frametimes) < 3:
                return {"available": False, "app": "", "fps": 0.0, "fps_1pct_low": 0.0,
                        "fps_0dot1pct_low": 0.0, "frametime_avg": 0.0, "frame_count": 0}
            ft_list = list(self._frametimes)
            ft_sorted = sorted(ft_list, reverse=True)
            avg_ft = sum(ft_list) / len(ft_list)
            fps_avg = 1000.0 / avg_ft if avg_ft > 0 else 0
            worst_1pct = max(1, len(ft_sorted) // 100)
            avg_1pct = sum(ft_sorted[:worst_1pct]) / worst_1pct
            fps_1pct = 1000.0 / avg_1pct if avg_1pct > 0 else 0
            worst_01pct = max(1, len(ft_sorted) // 1000)
            avg_01pct = sum(ft_sorted[:worst_01pct]) / worst_01pct
            fps_01pct = 1000.0 / avg_01pct if avg_01pct > 0 else 0
            return {
                "available": True,
                "app": self._last_app,
                "fps": round(fps_avg, 1),
                "fps_1pct_low": round(fps_1pct, 1),
                "fps_0dot1pct_low": round(fps_01pct, 1),
                "frametime_avg": round(avg_ft, 2),
                "frame_count": len(ft_list),
            }

    def __del__(self):
        self.close()