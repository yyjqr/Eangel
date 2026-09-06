"""
SoC 自动化测试框架 - 全局配置
支持：单目/双目/三目/四目 | 1-60fps | 64-256MB 内存 | 单核/多核 ARM
"""

# ─── 服务器配置 ───────────────────────────────────────────
SERVER_IP   = "192.168.1.200"   # 服务端 IP（本机）
BASE_PORT   = 9000              # nc 文件传输起始端口（每路+1）

# ─── DUT 板端配置列表（支持多 DUT 并行） ─────────────────
DUTS = [
    {
        "name"    : "DUT-A",
        "ip"      : "192.168.1.100",
        "user"    : "root",
        "password": "",
        "port"    : 23,          # Telnet 端口
        "protocol": "telnet",    # telnet | ssh | serial
        "serial"  : "/dev/ttyUSB0",
        "baud"    : 115200,
        # 硬件特性
        "memory_mb"  : 128,
        "cores"      : 2,
        "chip"       : "Hi3516DV300",
        "sdk"        : "HiMPP",   # HiMPP | RK_MPP | AmbaSDK | Generic
        # 摄像头接口（最多 4 路）
        "cameras": [
            {"id": 0, "dev": "/dev/video0", "sensor": "IMX307",  "width": 1920, "height": 1080, "max_fps": 30},
            {"id": 1, "dev": "/dev/video1", "sensor": "OV2710",  "width": 1920, "height": 1080, "max_fps": 30},
        ],
        # 音频接口
        "audio": {"alsa_dev": "hw:0,0", "sample_rate": 16000, "channels": 1},
    },
]

# ─── 测试全局阈值 ─────────────────────────────────────────
THRESHOLDS = {
    "video": {
        "variance_min"    : 5.0,    # 低于此值为黑屏/死帧
        "bad_pixel_ratio" : 0.03,   # 花屏坏像素比例上限
        "fps_tolerance"   : 0.05,   # 帧率偏差容忍 ±5%
        "frame_drop_max"  : 0.01,   # 最大丢帧率 1%
        "first_frame_ms"  : 3000,   # 首帧延迟上限 3s
        "psnr_min"        : 30.0,   # 最低 PSNR (dB)
        "sync_diff_ms"    : 2.0,    # 多目帧同步误差上限 (ms)
    },
    "audio": {
        "snr_min_db"      : 30.0,   # 信噪比下限
        "thd_max_pct"     : 1.0,    # 总谐波失真上限 1%
        "freq_tolerance"  : 50,     # 频率偏差容忍 ±50Hz
        "av_sync_ms"      : 100,    # 音视频同步误差上限 ms
    },
    "encode": {
        "bitrate_tol_pct" : 10.0,   # CBR 码率偏差容忍 ±10%
        "idr_interval_max": 2.5,    # IDR 间隔上限 (秒)
    },
    "system": {
        "cpu_max_pct"     : 90.0,   # CPU 占用报警阈值
        "mem_free_min_mb" : 10,     # 最小空闲内存 (MB)
        "temp_max_celsius": 85,     # 最高核心温度 °C
    },
}

# ─── 报告路径 ──────────────────────────────────────────────
REPORT_DIR  = "./reports"
LOG_DIR     = "./reports/logs"
MEDIA_DIR   = "./reports/media"   # 存储 YUV/WAV/截图

# ─── AI 诊断配置（可选） ──────────────────────────────────
AI_DIAG = {
    "enabled" : False,            # 设为 True 后自动调用 LLM 诊断 FAIL 用例
    "provider": "claude",         # claude | openai | hermes_local
    "model"   : "claude-3-5-sonnet-20241022",
    "api_key_env": "ANTHROPIC_API_KEY",
}
