"""
fps_low.py - 独立帧率分析模块
==============================

实现行业标准的 FPS 统计指标计算，包括：
- 平均 FPS (Average FPS)
- 1% Low FPS
- 0.1% Low FPS
- 帧时间中位数 (Median Frametime)
- 帧时间标准差 (Standard Deviation)
- 帧时间变异系数 (Coefficient of Variation)

参考标准：
- NVIDIA FrameView 1.7: 1% Low = 最慢 1% 帧的 FPS 平均值
- CapFrameX (v1.7+): 支持两种 x% Low 算法
  * x% Low Average: 最慢 x% 帧的 FPS 平均值（与 FrameView 一致）
  * x% Low Integral: 按时间累积，帧时间从大到小排列，累计达到总时间 x%
    时对应的 FPS 值（更严格，保证 99% 时间内高于该值）
- MSI Afterburner / RTSS: 基于时间窗口的移动平均

========================================================================
关于 DLSS 帧生成 (Frame Generation) 的影响
========================================================================

DLSS Frame Generation (FG) 会在真实渲染帧之间插入插值帧：
  - 真实渲染帧: 由 GPU 实际渲染，帧时间反映真实性能
  - 插值生成帧: 由 AI 模型根据前后帧生成，帧时间通常更短更稳定

帧生成对 FPS 测量的影响：
  1. 帧率数值翻倍（如 60→120 FPS），但其中一半是生成帧
  2. 生成帧的帧时间不能反映 GPU 真实渲染能力
  3. 1% Low 如果基于显示帧时间计算，会包含生成帧的数据
     -> 数值看起来更好，但不代表真实渲染性能

本模块提供两种测量模式：
  - display_mode=True:  测量所有显示帧（包含 FG 生成帧），反映用户视觉体验
  - display_mode=False: 测量所有帧（默认），不区分来源

当使用 DLSS FG 时：
  - 建议 display_mode=True，因为用户感受到的是显示帧率
  - 1% Low 反映的是用户实际感受到的卡顿情况
  - 注意：FG 会掩盖 CPU 瓶颈导致的真实卡顿
  - DLSS 3/4 FG 增加约 8-18ms 延迟，FSR FG 增加约 12-18ms

========================================================================
算法详细说明
========================================================================

1. 平均 FPS:
   avg_fps = 1000.0 / mean frametime_ms

2. 1% Low FPS (NVIDIA FrameView 标准):
   - 将所有帧时间从大到小排序
   - 取最慢 1% 的帧（至少 1 帧）
   - 计算这些帧的平均帧时间
   - 1% Low FPS = 1000.0 / average_worst_1pct_frametime

3. 0.1% Low FPS:
   - 同上，但取最慢 0.1% 的帧

4. 帧时间中位数:
   - 排序后取中间值

5. 标准差 / 变异系数:
   - std / mean * 100% = 变异系数
   - < 5%: 优秀  |  5-10%: 良好  |  > 10%: 差
"""

from dataclasses import dataclass, field
from typing import List, Optional
import threading
import time
import math


@dataclass
class FPSStats:
    """帧率统计结果"""
    avg_fps: float = 0.0
    fps_1low: float = 0.0
    fps_01low: float = 0.0
    median_frametime: float = 0.0
    avg_frametime: float = 0.0
    min_frametime: float = 0.0
    max_frametime: float = 0.0
    std_frametime: float = 0.0
    cv_frametime: float = 0.0
    frame_count: int = 0


class FPSAnalyzer:
    """
    帧率分析器 - 独立模块，可脱离 OSD 独立使用

    用法:
        analyzer = FPSAnalyzer(buffer_size=3000)
        analyzer.push_frame(frametime_ms)
        stats = analyzer.get_stats()
        print(f"FPS: {stats.avg_fps:.1f}, 1% Low: {stats.fps_1low:.1f}")
    """

    def __init__(self, buffer_size: int = 5000):
        self._buffer_size = buffer_size
        self._frametimes: List[float] = []
        self._lock = threading.Lock()
        self._session_start = time.perf_counter()
        self._gc_interval = 60.0

    def push_frame(self, frametime_ms: float):
        """
        推入一帧的帧时间（毫秒）

        参数:
            frametime_ms: 帧与帧之间的间隔时间，单位毫秒
        """
        if frametime_ms <= 0 or frametime_ms > 10000:
            return
        with self._lock:
            self._frametimes.append(frametime_ms)
            if len(self._frametimes) > self._buffer_size:
                self._frametimes.pop(0)

    def push_batch(self, frametimes_ms: List[float]):
        """批量推入帧时间数据"""
        with self._lock:
            for ft in frametimes_ms:
                if 0 < ft <= 10000:
                    self._frametimes.append(ft)
            while len(self._frametimes) > self._buffer_size:
                self._frametimes.pop(0)

    def clear(self):
        """清空缓冲区"""
        with self._lock:
            self._frametimes.clear()
            self._session_start = time.perf_counter()

    def get_frame_count(self) -> int:
        with self._lock:
            return len(self._frametimes)

    def get_stats(self, min_frames: int = 10) -> FPSStats:
        """
        计算帧率统计指标

        参数:
            min_frames: 最少帧数，不足时返回零值

        返回:
            FPSStats 数据类，包含所有统计指标
        """
        with self._lock:
            if len(self._frametimes) < min_frames:
                return FPSStats(frame_count=len(self._frametimes))

            data = list(self._frametimes)
            now = time.perf_counter()
            if now - self._session_start > self._gc_interval:
                self._frametimes.clear()
                self._session_start = now
                import gc
                gc.collect()

        return self._calculate(data)

    def _calculate(self, frametimes: List[float]) -> FPSStats:
        """
        核心计算逻辑

        实现 NVIDIA FrameView / CapFrameX 标准算法:
        1. 平均 FPS = 1000 / mean(frametime)
        2. 1% Low = 1000 / mean(worst_1pct_frametimes)
        3. 0.1% Low = 1000 / mean(worst_01pct_frametimes)
        """
        n = len(frametimes)

        avg_ft = sum(frametimes) / n
        avg_fps = 1000.0 / avg_ft if avg_ft > 0 else 0.0

        sorted_ft = sorted(frametimes, reverse=True)

        min_ft = sorted_ft[-1]
        max_ft = sorted_ft[0]

        mid = n // 2
        if n % 2 == 0:
            median_ft = (sorted_ft[mid - 1] + sorted_ft[mid]) / 2.0
        else:
            median_ft = sorted_ft[mid]

        variance = sum((ft - avg_ft) ** 2 for ft in frametimes) / n
        std_ft = math.sqrt(variance)
        cv = (std_ft / avg_ft * 100.0) if avg_ft > 0 else 0.0

        fps_1low = self._calc_x_low(sorted_ft, 0.01)
        fps_01low = self._calc_x_low(sorted_ft, 0.001)

        return FPSStats(
            avg_fps=avg_fps,
            fps_1low=fps_1low,
            fps_01low=fps_01low,
            median_frametime=median_ft,
            avg_frametime=avg_ft,
            min_frametime=min_ft,
            max_frametime=max_ft,
            std_frametime=std_ft,
            cv_frametime=cv,
            frame_count=n,
        )

    @staticmethod
    def _calc_x_low(sorted_ft_desc: List[float], fraction: float) -> float:
        """
        计算 x% Low FPS

        算法 (NVIDIA FrameView 标准):
        1. 帧时间已从大到小排列
        2. 取前 n*fraction 帧（至少 1 帧）
        3. 计算这些帧的平均帧时间
        4. 转换为 FPS

        这确保了 1% Low 代表"最慢 1% 帧的平均表现"，
        而非单一最差帧的瞬时值，更具统计意义。
        """
        n = len(sorted_ft_desc)
        count = max(1, int(n * fraction))
        worst = sorted_ft_desc[:count]
        avg_worst = sum(worst) / len(worst)
        return 1000.0 / avg_worst if avg_worst > 0 else 0.0

    @staticmethod
    def calc_x_low_integral(sorted_ft_desc: List[float], total_time_ms: float,
                            fraction: float) -> float:
        """
        CapFrameX v1.5.3+ 积分法 (x% Low Integral)

        与百分位数法不同，此方法按时间累积：
        1. 帧时间从大到小排列
        2. 逐帧累加帧时间，直到累计时间 >= 总时间 * fraction
        3. 最后一帧对应的 FPS 即为 x% Low

        优点: 保证"99% 的时间里 FPS 高于此值"（更严格）
        缺点: 需要知道总时间

        示例:
            1000 帧，总时间 20000ms (20s)
            1% = 200ms
            帧时间排序: [50ms, 40ms, 35ms, 30ms, 20ms, 16ms, ...]
            累加: 50+40+35+30+20+16=191ms (不够 200ms)
            再加下一帧: 191+16.7=207.7ms (超过 200ms)
            -> 该帧的 FPS = 1000/16.7 ≈ 59.9
        """
        cumulative = 0.0
        threshold = total_time_ms * fraction
        for ft in sorted_ft_desc:
            cumulative += ft
            if cumulative >= threshold:
                return 1000.0 / ft if ft > 0 else 0.0
        return 1000.0 / sorted_ft_desc[-1] if sorted_ft_desc and sorted_ft_desc[-1] > 0 else 0.0
