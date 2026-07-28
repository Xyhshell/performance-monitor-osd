"""
Performance Monitor OSD - Installation and Usage Guide
=====================================================

This lightweight performance monitoring tool displays real-time CPU, GPU, and FPS metrics
in a translucent overlay for game optimization and system monitoring.

Quick Start
-----------

1. Install Dependencies
```bash
pip install PyQt5 psutil nvidia-ml-py pythonnet
```

2. Download LibreHardwareMonitor
   - Visit: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases
   - Extract to any location (e.g., `C:\LibreHardwareMonitor`)

3. Ensure the DLL is accessible
   - The DLL needs to be in the same directory as this script
   - Or ensure it's in your system PATH

4. Run the Application
```bash
python main.py
```

Note: Administrator privileges are recommended for optimal sensor reading and FPS collection.

Key Features
------------

1. Real-time Monitoring
   - CPU usage, frequency, temperature, voltage, power
   - GPU usage, frequency, temperature, voltage, power, memory
   - FPS with 1% Low (NVIDIA FrameView compatible)

2. FPS Analysis
   - 1% Low FPS (worst 1% frames average)
   - 0.1% Low FPS (worst 0.1% frames average)
   - Median frametime and standard deviation
   - Coefficient of variation
   - Optional DLSS detection support

3. Multiple Collection Methods
   - DXGI Desktop Duplication (preferred, DirectX/Vulkan compatible)
   - GDI BitBlt (fallback for DirectX games without DXGI support)

4. Customizability
   - 13+ color themes (Cyberpunk, Dark Night, Fresh, etc.)
   - Adjustable font size and color
   - Configurable display items
   - Resizable and movable overlay
   - Pinned mode (no-click-through)

5. System Tray Integration
   - Show/hide overlay
   - Quick settings access
   - Pin/unpin functionality
   - System information display

Operation Algorithm
-------------------

FPS Calculation:
- 1% Low FPS: Takes the worst 1% of frames by frametime, averages them, converts to FPS
- Reflects the user's actual experience with performance dips
- More meaningful than single worst frame or moving average

DLSS Support:
- Optional display mode to differentiate between real frames and DLSS-generated frames
- 1% Low reflects user experience, not just GPU rendering capability
- Helps identify CPU bottlenecks that DLSS may mask

Performance Characteristics
---------------------------

- Low CPU usage (<5%) during monitoring
- Minimal memory footprint
- ~30ms update interval (configurable 100-5000ms)
- 64x64px performance monitoring region
- Optimized for smooth gameplay with minimal FPS impact

License
-------
MIT License

Copyright (c) 2026 jingmo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Troubleshooting
----------------

Common Issues:

1. "LibreHardwareMonitorLib.dll not found"
   - Download LibreHardwareMonitor from the releases page
   - Place the DLL in the same directory as the script

2. "Permission denied" errors
   - Run with administrator privileges
   - Ensure the LibreHardwareMonitorLib.dll is readable

3. Frozen application or high CPU usage
   - Increase update interval (settings → appearance → refresh interval)
   - Check other applications using hardware sensors

4. Frame drops during gaming
   - Decrease update interval gradually
   - Try different update intervals (500ms recommended)
   - Some games may not support DXGI Desktop Duplication

5. 1% Low always high
   - DLSS Frame Generation in use (1% Low reflects visual experience)
   - Application metrics differ from actual performance metrics
   - Enable DLSS display mode to see true rendering performance

Performance Monitoring Tips
--------------------------

1. Game Frame Focus:
   - Use DXGI Desktop Duplication instead of GDI
   - Smaller monitoring region (currently 64x64px)
   - Adjust for different screen resolutions

2. Sensor Monitoring:
   - CPU monitors temperature, voltage, power
   - GPU monitors all sensors via NVML and LibreHardwareMonitor
   - Some sensors may not be available on your system

3. UI Customization:
   - Double-click OSD to open settings
   - Right-click tray icon for quick controls
   - Pinned mode keeps window on top without blocking clicks
   - Try different themes for better visibility

4. Logging:
   -FPS logging shows collection stats every 5 seconds
   - Supports both DXGI and GDI collection methods
   - Help identify collection method issues

5. System Requirements:
   - Windows 10 or later
   - Python 3.8 or higher
   - DirectX 11 compatible graphics card for optimal performance
   - LibreHardwareMonitor Lib for advanced sensor data

Additional Information
----------------------

Technical Details:
- Uses PyQt5 5.15.4 for GUI development
- Implements NVIDIA FrameView 1.7 compatible algorithm
- Supports CapFrameX v1.5.3+ integral 1% Low calculation
- Uses DXGI Output Duplication API for DirectX/Vulkan games
- Integrates with LibreHardwareMonitorLib.dll for hardware sensors
- Provides fallback GDI BitBlt for DirectX games without DXGI support

Performance Metrics Explained:
- Average FPS: Overall performance average
- 1% Low: Performance experienced by 99% of the time
- 0.1% Low: Performance experienced by 99.9% of the time
- Median Frametime: Typical frametime with 50% below
- Coefficient of Variation (<5%: Excellent, 5-10%: Good, >10%: Poor)

Next Steps
----------

- Experiment with different monitor refresh rates
- Test different window sizes and positions
- Explore all themes and color combinations
- Monitor performance during intensive applications
- Optimize for your specific use case (gaming, streaming, etc.)

For advanced usage, see the source code for implementation details and customization options.

Authors:
    Original Author: jingmo
    Contributors: 
        Enhanced code stabilization by open-source community
    Version: 1.0
    Release Date: 2026-07-28
