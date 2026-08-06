import sys
import os
import ctypes
import logging
import argparse
import atexit
import config
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from ui import OSDWindow, SettingsDialog, SystemTray
from settings import Settings
from monitor import HardwareMonitor, FPSData
from fps_monitor import FPSMonitor

# ---------- 日志配置 ----------
def setup_logging(debug=False):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # 根级别设为 DEBUG，通过 handler 控制输出

    # 移除可能已存在的 handler（避免重复）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 控制台 handler（根据 debug 决定级别）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(console)

    # 文件 handler（仅当 debug 时启用）
    if debug:
        try:
            file_handler = logging.FileHandler('osd_debug.log', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'))
            logger.addHandler(file_handler)
            logger.info("调试日志已写入 osd_debug.log")
        except Exception as e:
            logger.error(f"创建日志文件失败: {e}")

    # 抑制第三方库的日志
    logging.getLogger('PyQt5').setLevel(logging.WARNING)
    logging.getLogger('clr').setLevel(logging.WARNING)
    return logger

# ---------- 管理员权限检查与提权 ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]])
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1
        )
        return True
    except Exception as e:
        print(f"申请管理员权限失败: {e}")
        return False

# ---------- 监控线程类 ----------
class MonitorThread(QThread):
    data_updated = pyqtSignal(object, object, object, object)

    def __init__(self, interval=800, logger=None):
        super().__init__()
        self.interval = interval
        self._running = True
        self.logger = logger or logging.getLogger(__name__)
        self.hw_monitor = HardwareMonitor()
        self.fps_monitor = FPSMonitor()
        if not self.fps_monitor.open():
            self.logger.warning("PresentMon 启动失败，FPS 将不可用")
        else:
            self.logger.info("PresentMon 已启动")
        atexit.register(self.cleanup)

    def run(self):
        self.logger.debug("监控线程开始运行")
        while self._running:
            try:
                self.hw_monitor.update()
                cpu = self.hw_monitor.get_cpu_data()
                gpu = self.hw_monitor.get_gpu_data()
                nets = self.hw_monitor.get_net_data()
                net = nets[0] if nets else None
                fps_dict = self.fps_monitor.get_fps_info()
                fps = FPSData(
                    available=fps_dict.get("available", False),
                    app=fps_dict.get("app", ""),
                    fps=fps_dict.get("fps", 0.0),
                    fps_1pct_low=fps_dict.get("fps_1pct_low", 0.0),
                    fps_0dot1pct_low=fps_dict.get("fps_0dot1pct_low", 0.0),
                    frametime_avg=fps_dict.get("frametime_avg", 0.0),
                    frame_count=fps_dict.get("frame_count", 0)
                )
                self.data_updated.emit(cpu, gpu, net, fps)
            except Exception as e:
                self.logger.error(f"监控数据更新异常: {e}", exc_info=True)
            self.msleep(self.interval)
        self.logger.debug("监控线程结束")

    def stop(self):
        self._running = False
        self.wait()
        self.cleanup()

    def cleanup(self):
        self.hw_monitor.close()
        self.fps_monitor.close()
        self.logger.info("硬件监控与PresentMon已关闭")


# ---------- 主程序 ----------
def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Performance Monitor OSD')
    parser.add_argument('--debug', action='store_true', help='启用调试日志')
    args, unknown = parser.parse_known_args()

    # 配置日志（此时还未获得 logger，先创建一个临时 logger 用于早期信息）
    logger = setup_logging(args.debug)

    # 检查管理员权限
    if sys.platform == 'win32':
        if not is_admin():
            logger.warning("当前未以管理员身份运行，正在申请提权...")
            if run_as_admin():
                logger.info("已请求管理员权限，原程序退出。")
                sys.exit(0)
            else:
                logger.error("无法获取管理员权限，部分传感器可能无法读取。")
        else:
            logger.info("已获得管理员权限。")

    logger.info("Performance Monitor OSD 启动")
    logger.debug(f"命令行参数: {sys.argv}")

    # 加载配置
    try:
        settings = Settings.load()
        logger.debug("配置加载成功")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        settings = Settings()

    # 初始化 Qt 应用
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon.fromTheme("utilities-system-monitor", QIcon()))

    # 创建 OSD 窗口
    osd = OSDWindow(settings)
    tray = SystemTray()
    monitor_thread = MonitorThread(settings.window.update_interval, logger=logger)
    monitor_thread.data_updated.connect(osd.update_data)
    monitor_thread.start()

    # ---------- 定义交互函数（在连接信号之前） ----------
    def toggle_osd():
        if osd.isVisible():
            osd.hide()
        else:
            osd.show()

    def toggle_pin(pinned):
        settings.window.pinned = pinned
        osd.update_settings(settings)
        settings.save()

    def on_settings_changed(new_settings):
        nonlocal settings
        settings = new_settings
        osd.update_settings(settings)
        monitor_thread.interval = settings.window.update_interval

    def show_settings():
        dlg = SettingsDialog(settings, parent=osd)
        dlg.settings_changed.connect(on_settings_changed)
        dlg.exec_()

    def quit_app():
        monitor_thread.stop()
        app.quit()

    # 连接信号
    osd.settings_requested.connect(show_settings)
    tray.show_hide_clicked.connect(toggle_osd)
    tray.settings_clicked.connect(show_settings)
    tray.quit_clicked.connect(quit_app)
    tray.pin_toggled.connect(toggle_pin)
    tray.set_pinned_state(settings.window.pinned)

    # 显示界面
    tray.show()
    osd.show()

    # 注册退出清理
    atexit.register(lambda: monitor_thread.cleanup())

    # 运行
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()