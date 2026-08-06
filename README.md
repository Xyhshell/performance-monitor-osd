# Performance Monitor OSD - 版本更新说明

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()

![OSD 预览](IMG/1.png) ![实测](IMG/2.png)

### 🚀 新增功能

- **CPU 频率增强显示**：支持显示所有核心的平均频率，以及 Intel 大小核架构的 P-Core 和 E-Core 平均频率（自动识别并分别显示）
- **双布局模式**：新增横向布局，与原有纵向布局自由切换，适应不同屏幕空间和用户习惯
- **模块顺序自定义**：可自由调整 CPU、GPU、网络、FPS 四个模块的显示顺序，满足个性化需求
- **智能 FPS 隐藏**：新增选项，当帧率 ≤ 60 时自动隐藏 FPS 监控区域，避免非游戏场景下的干扰
- **自动管理员提权**：启动时自动申请 UAC 管理员权限，确保传感器数据完整读取（无需手动以管理员身份运行）
- **网络累计传输量**：新增上行/下行累计流量显示（MB），方便统计会话总流量
- **N/A 值智能隐藏**：当传感器数据不可用（如 GPU 电压）时，自动隐藏对应显示项，界面更干净

### 🔧 优化与改进

- **日志系统重构**：支持 `--debug` 参数启动，仅调试模式生成 `osd_debug.log` 文件，便于问题排查
- **鼠标交互优化**：取消固定模式后，必须按住左键才能拖动窗口，避免误触导致窗口漂移
- **窗口置顶增强**：确保 OSD 始终显示在所有窗口最上层，不被游戏或应用遮挡
- **PresentMon 进程管理**：长时间无新帧时自动重启 PresentMon，提高 FPS 采集稳定性；程序退出时自动清理残留进程
- **配置加载兼容性**：旧配置文件自动补全缺失字段（如 `module_order`），避免启动失败
- **代码健壮性**：增加大量空值检查和异常捕获，避免线程崩溃导致 OSD 停止响应

### 🐛 修复问题

- 修复纵向布局在某些环境下显示纯黑的问题
- 修复 CPU 频率传感器存在 `None` 值时导致比较运算崩溃的错误
- 修复显存格式化时 `None` 值导致程序崩溃的错误
- 修复取消固定后鼠标悬停即触发卡顿移动的问题
- 修复 FPS 区域大号数值被遮挡的问题（增加垂直间距）
- 修复 PresentMon 进程意外退出后未自动重启的问题
- 修复退出程序后 PresentMon 进程残留的问题

### 📚 技术改进

- **硬件传感器读取**：扩展 LibreHardwareMonitor 传感器解析，支持区分 P-Core 和 E-Core 频率
- **FPS 采集算法**：基于 PresentMon 的 ETW 事件，计算 1% Low、0.1% Low 及帧时间中位数
- **网络监控**：自动过滤虚拟/未连接网卡，速率自动换算 KB/s / MB/s，简化显示

---

**此次更新旨在提供更准确、更灵活的监控体验，同时提升稳定性和易用性。** 感谢您的使用与反馈！
---

**版本**：1.1 
**发布日期**：2026-07-28  ->  2026-08-06
**作者**：[jingmo](https://github.com/Xyhshell)  
**项目地址**：[GitHub](https://github.com/Xyhshell/performance-monitor-osd)
