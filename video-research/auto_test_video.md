nt** 以及**具体功能测试逻辑**。

## 一、 系统整体架构设计

整个自动化测试体系采用 **中央控制服务器（Linux Server） + 硬件控制总线/矩阵 + 边缘板端 Agent** 的主从分布式架构。

```
                    ┌──────────────────────────────────────────────┐
                    │            Linux Central Server              │
                    │   (PyTest / Jenkins / Test Manager)          │
                    └──────┬──────────────────────┬────────────────┘
                           │ (SSH / REST / ADB)   │ (USB-Relay / Power / I2C / CAN)
                           ▼                      ▼
           ┌──────────────────────────────┐  ┌──────────────────────────────┐
           │     Device Under Test (DUT)  │  │   Control & Fixture Board    │
           │  (Multi-SoC Board: ISP/Codec)│  │ (Programmable Power / Matrix)│
           └──────────────┬───────────────┘  └──────────────┬───────────────┘
                          │ (MIPI-CSI / Line-in)            │ (Control Signal)
                          ▼                                 ▼
           ┌──────────────────────────────┐  ┌──────────────────────────────┐
           │ CIS Sensors (1-4 Cameras) /  │  │ Pattern Generator / Audio    │
           │ Audio Input (Line-in / Mic)  │◄─┤ Generator (Signal Source)   │
           └──────────────────────────────┘  └──────────────────────────────┘
```

## 二、 硬件层与测试环境搭建

要测试多芯片、不同 CIS，必须在硬件层面实现**传感器信号可切换**、**板端电源与复位可控制**以及**音视频信号源自动注入**。

### 1. 图像信号注入（CIS 自动化测试）

- **真实 Camera 场景：** 将 DUT（待测板）固定在标准测试暗箱中，面对可编程调光的 LED 标板（如 ISO12233 解析力卡、24 色彩卡）。控制服务器通过 RS232/USB 控制暗箱光源亮度和色温，测试 ISP 在不同照度下的 2-5MP / 1-30fps 表现。

- **虚拟 Sensor 注入（MIPI Emulator / Frame Grabber）：** 为了测试极限帧率（如 30fps 满载）或特定的 MIPI Error 恢复能力，使用 **FPGA 模拟 MIPI CSI-2 发射端**。服务器将测试图片发送给 FPGA，FPGA 模拟真实 CIS（如 IMX307/OV2710 等）向 SoC 注入 Raw/YUV 数据，脱离物理摄像头限制。


### 2. 音频信号注入与采集

- **输入注入：** 服务器通过声卡（Line-out）或标准音频信号发生器（如 USB DAC），将标准正弦波（1kHz）、扫频信号或语音样本输入到板端的 Line-in / Mic 接口。

- **输出采集：** 若待测板有音频播放功能，通过服务器的 Line-in 录制板端输出，用于失真度（THD）和延迟比对。


### 3. 上电与接口控制硬件

- **可编程直流电源 / 继电器板（USB Relay）：** 服务器通过 Python 控制 USB 继电器切断/通断 DUT 的电源（VCC）及 GPIO（如 Reset、PWDN 线），实现自动冷重启和异常上电测试。

- **串口服务器（Serial-to-Ethernet Converter）：** 针对多芯片板，将各 SoC 的 Debug UART 连接到多口串口服务器（如 Moxa），Linux 服务器通过 TCP/IP 统一抓取底层 Log。


## 三、 Linux 服务器与软件测试框架

系统采用 **PyTest** 作为核心测试框架，结合 **Jenkins / Gitlab CI** 实现定时与触发式自动化运行。

### 1. 分层软件架构

- **测试编排层 (Framework & Test Cases):** 基于 PyTest 编写测试用例，负责测试逻辑组织、断言（Assert）与测试报告生成（Allure Report）。

- **设备通讯与控制层 (Device Abstraction Layer - DAL):** 封装 SSH (Paramiko)、ADB、Serial (pyserial) 及 REST API。将不同 SoC（如海思、瑞芯微、安霸、Rockchip 等）的底层指令差异抽象成统一接口（例如：`dut.start_capture(sensor_id, resolution, fps)`）。

- **分析与指标比对库 (Analysis Engine):** 集成 OpenCV、FFmpeg、PyAV、Librosa 等开源库，在服务器端对采集到的音视频文件进行质量分析。


### 2. 板端客户端（DUT Agent）设计

在 DUT 运行轻量级的测试 Agent（支持 C/C++ 或 Python/Shell）：

- 通过 Linux 标准 **V4L2 接口** 采集摄像头 Raw/YUV 数据。

- 通过 **ALSA (aplay / arecord)** 采集或播放音频。

- 通过硬件编码器（如 VENC API、VAAPI 或 Vendor SDK）导出 H.264/H.265/AAC 码流。

- 暴露 Socket 或 TCP 控制端口，接收服务器发来的抓帧/编码指令，并将音视频码流回传给服务器。


## 四、 核心测试功能模块设计

自动化测试需覆盖采集、编码、多目同步以及各种异常恢复场景：

1

视频采集与 ISP 基础测试

覆盖 2-5MP, 1-30fps

**1.视频采集与 ISP 基础测试：**覆盖 2-5MP, 1-30fps。

- **分辨率与帧率校验：** 驱动 Agent 切换不同的 CIS 模式（如 1080p@30fps, 5MP@15fps），将 Stream 导出至服务器，使用 FFmpeg / OpenCV 校验视频流的时间戳（PTS），检查实际帧率偏差、丢帧率（Frame Drop Rate）与首帧出图时间（First Frame Latency）。

- **图像质量（IQ）自动判定：** 服务器分析录制的图像，检测是否存在黑屏、绿屏、花屏（撕裂）、条纹噪声。计算图像的 PSNR/SSIM 以及均方差（Variance）判断图像模糊度。


2

视频编码（VENC）与码流分析

H.264 / H.265 / MJPEG

**2.视频编码（VENC）与码流分析：**H.264 / H.265 / MJPEG。

- **编码合规性：** 检查输出码流的 GOP 结构、I/P 帧比例、Bitrate（CBR/VBR 控制精度）。

- **画质与码率平衡：** 在不同运动场景下测试编码器的 PSNR 与 VMAF 指标。


3

多目（Multi-Camera）同步测试

双目/四目 ISP SoC

**3.多目（Multi-Camera）同步测试：**双目/四目 ISP SoC。

- **帧同步测试（Frame Synchronization）：** 多个 CIS 面对高精度毫秒级 LED 计时器。服务器抓取多路同步视频帧，利用 OCR 识别图像中的时间戳，比对不同通道间的曝光与帧到达时间差（要求通常在 < 1-2ms 内）。

- **带宽高负载测试：** 同时开启 4 路 5MP@30fps 采集与编码，监控 SoC 内部 AXI 总线拥堵情况、CPU 占用率以及 DDR 内存带宽上限。


4

音频采集与编解码测试

Audio / Video 协同

**4.音频采集与编解码测试：**Audio / Video 协同。

- **音频基础指标分析：** 服务器播放 1kHz 正弦波音频，DUT 通过 ALSA `arecord` 录制为 WAV 文件回传。服务器利用 `scipy.fft` / `librosa` 分析录音数据的信噪比（SNR）、总谐波失真（THD）及频率响应。

- **音视频同步（A/V Sync）：** 播放带有“Flash & Beep”（闪光加响铃）的测试视频信号。分析录制文件中光亮突变点与音频峰值点的时间差，得出 A/V Sync 延迟（单位：ms）。


5

容错与鲁棒性测试（Robustness & Self-Healing）

异常恢复与物理注入

**5.容错与鲁棒性测试（Robustness & Self-Healing）：**异常恢复与物理注入。

- **动态热插拔与复位：** 测试过程中，服务器控制继电器断开 CIS 供电或拉低 PWDN 引脚，制造 MIPI Error，触发底层 VICAP/ISP 复位机制，校验软件系统是否能自动恢复视频流（Self-Healing）。

- **长稳测试：** 连续进行 72 小时高低温环境下的 2-5MP@30fps 满载采集与编码，监控系统是否有 Memory Leak（内存泄漏）、Temperature Throttling（高温降频）或 Sensor 掉线问题。


## 五、 测试自动化与数据持久化

1. **任务调度（CI/CD Integration）：** 每次固件（Kernel/Driver/SDK）提交时，Gitlab CI 触发 Linux 服务器运行自动化测试脚本，执行 Regression（回归）测试。

2. **数据采集与可视化（Dashboard）：**

    - **测试日志：** 保存 Dmesg、V4L2 调试日志、ISP 统计信息（3A 数据）。

    - **音视频文件归档：** 异常测试帧自动截图（PNG）并存入 服务器 S3/MinIO 存储。

    - **结果大盘：** 测试结果导入 InfluxDB / MySQL，通过 Grafana 绘制不同芯片/Sensor 组合下的首帧延迟趋势图、丢帧率折线图以及音视频品质评分。
yes ,给出脚本和显示测试进度和测试结果框架，可结合claude或其它智能体进行迭代优化。

这是一个针对资源受限（仅 Telnet/串口、64~128MB 内存）嵌入式 ARM 板端设计的**完整自动化测试框架**。

框架采用了“胖服务器/瘦板端”架构：

- **板端（DUT）**：仅需运行 `telnetd`、`v4l2-ctl`、`arecord` 和 `nc`（BusyBox 自带），无需安装 Python/SSH。

- **服务端（Linux Server）**：负责控制板端、接收音视频文件、利用 OpenCV/SciPy 进行算法断言，并生成**丰富进度条**与**美化报告**。

- **Agent / AI 友好的设计**：代码采用模块化面向对象结构，并内置 JSON 结构化测试结果导出，非常方便未来接入 **Claude Code CLI** 或 **Hermes Agent** 进行自动分析、Bug 诊断与用例迭代优化。


### 项目代码结构

你可以将项目整理为如下结构：

```
test_framework/
├── config.py           # 环境变量与DUT配置
├── dut_client.py       # Pexpect Telnet 交互封装
├── test_runner.py      # 主入口：Rich 进度条与测试调度
├── analyzers/
│   ├── video_analyzer.py # YUV/帧率/花屏检测算法
│   └── audio_analyzer.py # WAV/SNR/THD 音频算法
└── reports/            # 存放 JSON 结果与 Allure/HTML 报告
```

### 1. 板端交互模块 (`dut_client.py`)

利用 `pexpect` 封装稳健的 Telnet 控制管道，并内置高效的文件传输逻辑（使用 `nc` 避开串口慢速和 64MB 内存写入瓶颈）。

Python

```
import pexpect
import sys
import time

class TelnetDUT:
    """资源受限板端的轻量级控制客户端"""
    def __init__(self, ip, user='root', password='', port=23, timeout=10):
        self.ip = ip
        self.user = user
        self.password = password
        self.port = port
        self.timeout = timeout
        self.session = None

    def connect(self):
        """建立 Telnet 会话"""
        cmd = f"telnet {self.ip} {self.port}"
        self.session = pexpect.spawn(cmd, timeout=self.timeout, encoding='utf-8')

        idx = self.session.expect(['login:', 'Login:', '# ', pexpect.TIMEOUT])
        if idx in [0, 1]:
            self.session.sendline(self.user)
            p_idx = self.session.expect(['Password:', '# ', pexpect.TIMEOUT])
            if p_idx == 0:
                self.session.sendline(self.password)
                self.session.expect('# ')
        elif idx == 3:
            raise ConnectionError(f"无法连接到板端 Telnet: {self.ip}")

    def exec_cmd(self, command, timeout=15):
        """发送命令并返回 Shell 输出结果"""
        if not self.session:
            self.connect()
        self.session.sendline(command)
        self.session.expect('# ', timeout=timeout)
        return self.session.before.strip()

    def fetch_file_via_nc(self, remote_file, local_file, server_ip, server_port=9000):
        """
        利用 Busybox 极轻量的 netcat(nc) 将板端 RAM (/tmp) 中的数据零落盘推送到服务器
        防止爆板端 64MB 内存
        """
        # 在板端触发后台推流命令
        cmd = f"nc {server_ip} {server_port} < {remote_file} &"
        self.exec_cmd(cmd)

    def close(self):
        if self.session:
            self.session.sendline('exit')
            self.session.close()
```

### 2. 音视频数据算法分析模块

不需要在板端装任何库，数据流回传到 Server 后由以下算法库直接分析。

#### 视频分析 (`analyzers/video_analyzer.py`)

Python

```
import cv2
import numpy as np

class VideoAnalyzer:
    @staticmethod
    def analyze_yuv420p(yuv_path, width, height):
        """分析 YUV 帧：检测黑屏、绿屏、梯度剧烈跳变（花屏）"""
        y_size = width * height
        try:
            with open(yuv_path, 'rb') as f:
                y_data = f.read(y_size)
                if len(y_data) < y_size:
                    return {"pass": False, "reason": "文件损坏或传输丢帧"}
        except Exception as e:
            return {"pass": False, "reason": str(e)}

        # 转为 OpenCV 可处理的 Y 分量矩阵
        y_frame = np.frombuffer(y_data, dtype=np.uint8).reshape((height, width))

        # 1. 黑屏/卡死检测 (方差小于 5.0 判定为单色/死帧)
        variance = np.var(y_frame)
        if variance < 5.0:
            return {"pass": False, "reason": f"疑似黑屏/卡死/绿屏 (Variance={variance:.2f})"}

        # 2. 花屏/条纹检测 (行间差分梯度突变)
        row_diff = np.abs(y_frame[1:, :] - y_frame[:-1, :])
        bad_lines = np.sum(row_diff > 160)
        bad_ratio = bad_lines / (width * height)

        if bad_ratio > 0.03: # 超过3%像素跳变
            return {"pass": False, "reason": f"检测到画面撕裂/花屏 (Error Ratio={bad_ratio*100:.2f}%)"}

        return {"pass": True, "metrics": {"variance": round(variance, 2), "error_ratio": round(bad_ratio, 4)}}
```

#### 音频分析 (`analyzers/audio_analyzer.py`)

Python

```
import numpy as np
from scipy.io import wavfile

class AudioAnalyzer:
    @staticmethod
    def analyze_sine_wave(wav_path, expected_freq=1000):
        """分析板端采集到的正弦波音频：检测频偏、信噪比 (SNR)"""
        try:
            sample_rate, data = wavfile.read(wav_path)
            if len(data.shape) > 1:
                data = data[:, 0] # 单通道
        except Exception as e:
            return {"pass": False, "reason": f"WAV读取失败: {str(e)}"}

        # 执行 FFT 傅里叶变换
        fft_spectrum = np.abs(np.fft.rfft(data))
        freqs = np.fft.rfftfreq(len(data), d=1.0/sample_rate)

        # 捕获主频
        peak_idx = np.argmax(fft_spectrum)
        detected_freq = freqs[peak_idx]

        # 计算信噪比 (SNR)
        signal_power = fft_spectrum[peak_idx] ** 2
        total_power = np.sum(fft_spectrum ** 2)
        noise_power = total_power - signal_power
        snr = 10 * np.log10(signal_power / (noise_power + 1e-10))

        # 断言
        if abs(detected_freq - expected_freq) > 50:
            return {"pass": False, "reason": f"主频偏移严重: 期望 {expected_freq}Hz, 实际 {detected_freq:.1f}Hz"}

        if snr < 30.0:
            return {"pass": False, "reason": f"音频底噪过高/有干涉: SNR={snr:.2f}dB (<30dB)"}

        return {"pass": True, "metrics": {"freq": round(detected_freq, 1), "snr_db": round(snr, 2)}}
```

### 3. 测试调度与终端进度显示 (`test_runner.py`)

使用 Python 优雅的 **`rich` 库** 提供直观的进度条、格式化表格和状态输出。同时导出结构化 JSON 报告，**支持后续使用 Agent (如 Claude) 进行 LLM 智能化诊断**。

Python

```
import time
import socket
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from dut_client import TelnetDUT
from analyzers.video_analyzer import VideoAnalyzer
from analyzers.audio_analyzer import AudioAnalyzer

console = Console()

# 配置待测硬件与服务器 IP
DUT_IP = "192.168.1.100"
SERVER_IP = "192.168.1.200"

def listen_and_receive_file(port, save_path, buffer_size=4096):
    """服务器端建立 Socket 监听，接收板端 nc 推送的文件"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(1)
        s.settimeout(10.0)
        try:
            conn, _ = s.accept()
            with open(save_path, 'wb') as f:
                while True:
                    data = conn.recv(buffer_size)
                    if not data:
                        break
                    f.write(data)
            conn.close()
            return True
        except socket.timeout:
            return False

def run_test_suite():
    dut = TelnetDUT(ip=DUT_IP)
    results = []

    console.print("\n[bold cyan]🚀 启动 SoC 音视频自动化硬件在环 (HIL) 测试平台[/bold cyan]\n")

    # 定义测试用例列表
    test_cases = [
        {"id": "TC_01", "name": "2MP@30fps CIS1 采集与花屏校验", "type": "video", "dev": "/dev/video0", "w": 1920, "h": 1080},
        {"id": "TC_02", "name": "5MP@15fps CIS2 高清采集校验", "type": "video", "dev": "/dev/video1", "w": 2592, "h": 1944},
        {"id": "TC_03", "name": "Line-in 音频正弦波采样与底噪测试", "type": "audio", "dev": "hw:0,0", "freq": 1000},
    ]

    try:
        dut.connect()
        console.print(f"[bold green]✓ 成功建立 Telnet 链路到板端: {DUT_IP}[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]✗ 无法连接板端: {e}[/bold red]")
        return

    # Rich 动态渲染测试进度
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:

        main_task = progress.add_task("[yellow]总体测试进度...", total=len(test_cases))

        for tc in test_cases:
            progress.set_description(f"[cyan]执行: {tc['name']}")
            status = "FAIL"
            metrics_str = ""
            reason = ""

            if tc["type"] == "video":
                # 1. 板端抓图
                remote_yuv = "/tmp/test.yuv"
                local_yuv = f"./reports/{tc['id']}.yuv"

                cmd = f"v4l2-ctl -d {tc['dev']} --set-fmt-video=width={tc['w']},height={tc['h']},pixelformat=NV12 --stream-mmap --stream-count=1 --stream-to={remote_yuv}"
                dut.exec_cmd(cmd)

                # 2. 板端推流，服务器接收
                dut.fetch_file_via_nc(remote_yuv, SERVER_IP, 9000)
                recv_ok = listen_and_receive_file(9000, local_yuv)

                if recv_ok:
                    # 3. 算法断言
                    res = VideoAnalyzer.analyze_yuv420p(local_yuv, tc['w'], tc['h'])
                    status = "PASS" if res["pass"] else "FAIL"
                    reason = res.get("reason", "")
                    metrics_str = str(res.get("metrics", ""))
                else:
                    reason = "数据回传超时 (Netcat Error)"

            elif tc["type"] == "audio":
                # 1. 板端录音 2 秒
                remote_wav = "/tmp/test.wav"
                local_wav = f"./reports/{tc['id']}.wav"

                cmd = f"arecord -D {tc['dev']} -r 16000 -f S16_LE -c 1 -d 2 {remote_wav}"
                dut.exec_cmd(cmd)

                # 2. 回传与接收
                dut.fetch_file_via_nc(remote_wav, SERVER_IP, 9001)
                recv_ok = listen_and_receive_file(9001, local_wav)

                if recv_ok:
                    res = AudioAnalyzer.analyze_sine_wave(local_wav, tc['freq'])
                    status = "PASS" if res["pass"] else "FAIL"
                    reason = res.get("reason", "")
                    metrics_str = str(res.get("metrics", ""))
                else:
                    reason = "音频回传超时"

            # 记录结果
            results.append({
                "id": tc["id"], "name": tc["name"], "status": status,
                "metrics": metrics_str, "reason": reason
            })

            # 清理板端 /tmp 临时文件（防止挤爆内存）
            dut.exec_cmd("rm -f /tmp/test.*")
            progress.advance(main_task)
            time.sleep(0.5)

    dut.close()

    # 4. 打印格式化终端结果大盘
    render_results_table(results)

    # 5. 保存 JSON 报告（供 Agent / Claude 分析）
    with open("./reports/test_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    console.print("\n[bold green]📊 JSON 格式测试报告已成功导出至 ./reports/test_summary.json[/bold green]")

def render_results_table(results):
    table = Table(title="📊 SoC 自动化测试最终结果汇总")
    table.add_column("用例 ID", style="cyan", no_wrap=True)
    table.add_column("测试项名称", style="magenta")
    table.add_column("结果", justify="center")
    table.add_column("算法测量数据/指标", style="green")
    table.add_column("失败原因 / 备注", style="red")

    for r in results:
        status_fmt = "[bold green]PASS[/bold green]" if r["status"] == "PASS" else "[bold red]FAIL[/bold red]"
        table.add_row(r["id"], r["name"], status_fmt, r["metrics"], r["reason"])

    console.print("\n")
    console.print(table)

if __name__ == "__main__":
    run_test_suite()
```

### 4. 终端测试进度与结果渲染效果 preview

当执行 `python test_runner.py` 时，终端会呈现如下漂亮的 Rich 界面：

#### 终端进度条

Plaintext

```
🚀 启动 SoC 音视频自动化硬件在环 (HIL) 测试平台

✓ 成功建立 Telnet 链路到板端: 192.168.1.100

执行: 5MP@15fps CIS2 高清采集校验 ━━━━━━━━━━━━━━━━━━━━━━━╸━━━━━━━━  66%
```

#### 最终汇总表格输出

Plaintext

```
                          📊 SoC 自动化测试最终结果汇总
┌─────────┬──────────────────────────────────┬──────┬───────────────────────────────┬────────────────────────────┐
│ 用例 ID │ 测试项名称                       │ 结果 │ 算法测量数据/指标             │ 失败原因 / 备注            │
├─────────┼──────────────────────────────────┼──────┼───────────────────────────────┼────────────────────────────┤
│ TC_01   │ 2MP@30fps CIS1 采集与花屏校验   │ PASS │ {'variance': 142.5, 'error... │                            │
│ TC_02   │ 5MP@15fps CIS2 高清采集校验     │ FAIL │                               │ 检测到画面撕裂/花屏 (Er... │
│ TC_03   │ Line-in 音频正弦波采样测试      │ PASS │ {'freq': 1000.2, 'snr_db':... │                            │
└─────────┴──────────────────────────────────┴──────┴───────────────────────────────┴────────────────────────────┘

📊 JSON 格式测试报告已成功导出至 ./reports/test_summary.json
```

### 5. 与 Claude Code / Hermes Agent 结合迭代的闭环

导出的 `test_summary.json` 文件是专为 AI 智能体设计的结构化上下文。你可以直接将 JSON 报告与 Dmesg 日志扔给 Claude 或 Hermes Agent，输入如下 Prompt 进行自动化迭代：

Plaintext

```
Prompt 示例:
"这是我的 SoC 自动化测试运行生成的 test_summary.json 和 dmesg.log。
用例 TC_02 提示存在画面撕裂（Error Ratio 超过 threshold）。
请分析:
1. 这是 MIPI 丢包还是 VICAP AXI 带宽撞墙导致的？
2. 请修改 `analyzers/video_analyzer.py`，增加对 YUV 图像边缘 Sobel 梯度的二次校验算法，以区分真实运动与花屏。"
```

智能体可以直接读取本脚本框架的代码，自动微调分析阈值、扩充新的 `v4l2` 脚本用例，甚至自动生成 Bug 修复补丁。
