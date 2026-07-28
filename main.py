"""
main.py - 程序入口
"""

import sys
import os
import ctypes
import ctypes.wintypes

try:
    ShellExecuteW = ctypes.windll.shell32.ShellExecuteW
    ShellExecuteW.restype = ctypes.c_int
    ShellExecuteW.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR,
        ctypes.wintypes.LPCWSTR, ctypes.wintypes.INT
    ]
    HAS_WINDOWS_API = True
except Exception:
    HAS_WINDOWS_API = False


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin():
    if not HAS_WINDOWS_API:
        return False
    try:
        script = os.path.abspath(sys.argv[0])
        python = sys.executable
        result = ShellExecuteW(None, "runas", python, f'"{script}"', None, 1)
        return result > 32
    except Exception:
        return False


class PerformanceMonitorApp:

    def __init__(self):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        from settings import Settings
        self._settings = Settings.load()

        from monitor import HardwareMonitor, DataWorker
        self._monitor = HardwareMonitor()
        self._worker = DataWorker(self._monitor, self._settings.window.update_interval)

        from ui import OSDWindow
        self._osd = OSDWindow(self._settings)

        from ui import SystemTray
        self._tray = SystemTray()

        self._settings_dialog = None

        self._osd.settings_requested.connect(self._show_settings)
        self._tray.show_hide_clicked.connect(self._toggle_osd)
        self._tray.settings_clicked.connect(self._show_settings)
        self._tray.quit_clicked.connect(self._quit_app)
        self._tray.pin_toggled.connect(self._on_pin_toggled)

        self._tray.set_pinned_state(self._settings.window.pinned)
        if self._settings.window.pinned:
            self._osd._apply_pinned(True)

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_data)
        self._timer.start(self._settings.window.update_interval)

        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self._log_fps)
        self._log_timer.start(2000)
        self._log_count = 0

        self._osd.show()
        self._tray.show()

    def _update_data(self):
        try:
            cpu, gpu, fps = self._worker.get_latest()
            self._osd.update_data(cpu, gpu, fps)
            self._tray.update_tooltip(cpu.usage, gpu.usage, fps.fps)
        except Exception as e:
            print(f"[App] 更新错误: {e}")

    def _log_fps(self):
        try:
            fps = self._monitor.fps._analyzer.get_stats(min_frames=1)
            method = self._monitor.fps._method
            frame_count = self._monitor.fps._frame_count
            if fps.frame_count > 0:
                self._log_count += 1
                if self._log_count % 5 == 0:
                    print(f"[FPS] {fps.avg_fps:.1f} FPS (1%Low: {fps.fps_1low:.1f}) | "
                          f"帧数: {frame_count} | 采集方式: {method.upper()}")
            else:
                print(f"[FPS] 等待帧数据... (帧数: {frame_count}, 采集方式: {method.upper()})")
        except Exception:
            pass

    def _toggle_osd(self):
        if self._osd.isVisible():
            self._osd.hide()
        else:
            self._osd.show()

    def _show_settings(self):
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        from ui import SettingsDialog
        from PyQt5.QtWidgets import QDialog

        self._settings_dialog = SettingsDialog(self._settings, self._osd)
        self._settings_dialog.settings_changed.connect(self._on_settings_changed)
        self._settings_dialog.finished.connect(self._on_dialog_closed)
        if self._settings_dialog.exec_() == QDialog.Accepted:
            self._save_settings()

    def _on_dialog_closed(self):
        self._settings_dialog = None

    def _on_settings_changed(self, settings):
        self._osd.update_settings(settings)
        self._timer.setInterval(settings.window.update_interval)
        self._worker.set_interval(settings.window.update_interval)
        self._tray.set_pinned_state(settings.window.pinned)
        self._save_settings()

    def _on_pin_toggled(self, checked):
        self._settings.window.pinned = checked
        self._osd._apply_pinned(checked)
        self._save_settings()

    def _save_settings(self):
        self._settings.save()

    def _quit_app(self):
        self._save_settings()
        self._worker.cleanup()
        self._monitor.cleanup()
        self._app.quit()

    def run(self) -> int:
        return self._app.exec_()


def main():
    print("=" * 50)
    print("  Performance Monitor OSD")
    print("=" * 50)

    if not is_admin():
        print("[Main] 非管理员，请求提权...")
        if request_admin():
            sys.exit(0)
        print("[Main] 以普通用户运行（传感器数据可能受限）")
    else:
        print("[Main] 管理员权限 OK")

    try:
        app = PerformanceMonitorApp()
        sys.exit(app.run())
    except Exception as e:
        print(f"[Main] 致命错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
