#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
dual_cam_soc_diag.py
====================
SOC 双目摄像头嵌入式流水线异常排查工具
  - VI / ISP / VPSS / VENC 各环节异常分析
  - 双目摄像头变分辨率风险评估
  - 400万 → 100万 分辨率/帧率/内存用量计算表

Author: JACK YANG
"""

import argparse
import sys
import math
from dataclasses import dataclass, field
from typing import List, Optional

# ──────────────────────────────────────────────
# 可选 rich 美化输出
# ──────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False

console = Console() if _RICH else None


def _print(msg: str, style: str = ""):
    if _RICH and console:
        console.print(msg, style=style)
    else:
        print(msg)


# ══════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════

@dataclass
class Resolution:
    """摄像头分辨率规格"""
    name: str        # e.g. "4MP"
    width: int
    height: int
    bpp_raw: int = 12   # RAW bits per pixel (e.g. RAW12)
    bpp_yuv: int = 12   # YUV NV12 = 12 bpp


@dataclass
class PipelineStage:
    """VI/VENC 流水线环节描述"""
    name: str
    zh_name: str
    risk_level: str   # LOW / MED / HIGH / CRITICAL
    anomalies: List[str]
    root_causes: List[str]
    diag_cmds: List[str]
    fixes: List[str]
    dyn_res_risks: List[str] = field(default_factory=list)   # 变分辨率特有风险


# ══════════════════════════════════════════════
# 常见分辨率规格表（400万 → 100万）
# ══════════════════════════════════════════════

RESOLUTIONS: List[Resolution] = [
    Resolution("4MP-W",   2560, 1600, bpp_raw=12),
    Resolution("4MP",     2592, 1520, bpp_raw=12),
    Resolution("4MP-SQ",  2048, 2048, bpp_raw=12),
    Resolution("3MP",     2304, 1296, bpp_raw=10),
    Resolution("3MP-VGA", 2048, 1536, bpp_raw=10),
    Resolution("2MP-FHD", 1920, 1080, bpp_raw=10),
    Resolution("2MP-UXGA",1600, 1200, bpp_raw=10),
    Resolution("1.3MP",   1280, 1024, bpp_raw=10),
    Resolution("1MP-720P",1280,  720, bpp_raw=10),
    Resolution("1MP-960P",1280,  960, bpp_raw=10),
]

FRAME_RATES = [10, 15, 20, 25, 30]  # fps


def calc_bandwidth(r: Resolution, fps: int) -> dict:
    """计算单路摄像头各阶段带宽与内存"""
    pixels = r.width * r.height

    # RAW 输入带宽 (MB/s)
    raw_bw_mbps  = pixels * fps * r.bpp_raw / 8 / 1024 / 1024

    # YUV NV12 带宽 (MB/s)
    yuv_bw_mbps  = pixels * fps * r.bpp_yuv / 8 / 1024 / 1024

    # 单帧 YUV NV12 帧缓冲 (MB)  NV12 = W*H*1.5
    frame_buf_mb = pixels * 1.5 / 1024 / 1024

    # VENC 编码估算 (H.265 参考码率, Mbps)
    # 经验公式: bitrate = W*H*fps * 0.07 / 1000000 (中等质量)
    h265_mbps    = pixels * fps * 0.07 / 1_000_000

    # 双目总带宽 (两路叠加)
    dual_raw_bw  = raw_bw_mbps * 2
    dual_yuv_bw  = yuv_bw_mbps * 2

    # 推荐帧缓冲数 (3 缓冲) × 双路
    dual_buf_mb  = frame_buf_mb * 3 * 2

    # DDR 带宽压力（RAW写 + YUV读写 + VENC读）
    ddr_pressure = raw_bw_mbps + yuv_bw_mbps * 2 + h265_mbps / 8

    return {
        "pixels_mp":    round(pixels / 1_000_000, 2),
        "raw_bw_mbps":  round(raw_bw_mbps, 1),
        "yuv_bw_mbps":  round(yuv_bw_mbps, 1),
        "h265_mbps":    round(h265_mbps, 1),
        "frame_buf_mb": round(frame_buf_mb, 2),
        "dual_raw_bw":  round(dual_raw_bw, 1),
        "dual_yuv_bw":  round(dual_yuv_bw, 1),
        "dual_buf_mb":  round(dual_buf_mb, 2),
        "ddr_pressure": round(ddr_pressure, 1),   # 单路 DDR 压力
    }


# ══════════════════════════════════════════════
# 流水线各环节异常分析
# ══════════════════════════════════════════════

PIPELINE_STAGES: List[PipelineStage] = [

    PipelineStage(
        name="SENSOR_INIT",
        zh_name="Sensor 初始化 (I2C/SPI 配置)",
        risk_level="HIGH",
        anomalies=[
            "Sensor ID 读取失败 / I2C NACK",
            "时钟配置错误导致 MCLK 频率偏差",
            "供电时序不满足 tPUP 要求",
            "固件版本不兼容 (OTP/EEPROM)",
        ],
        root_causes=[
            "I2C 地址冲突（双目两路地址相同，未做 PWDN 互斥）",
            "MCLK 频率超出 Sensor 规格范围",
            "RESET 信号宽度不够（< 1ms）",
            "Sensor DOVDD/AVDD/DVDD 上电顺序错误",
        ],
        diag_cmds=[
            "i2cdetect -y 1                         # 扫描 I2C 总线",
            "i2cget -y 1 0x36 0x0000 w              # 读 Sensor ID 寄存器",
            "cat /sys/kernel/debug/clk/mclk/clk_rate # 验证 MCLK",
            "dmesg | grep -i 'sensor\\|i2c\\|mclk'   # 内核日志过滤",
        ],
        fixes=[
            "双目使用不同 I2C 总线或 PWDN 引脚分时上电",
            "核查 DTS 中 clock-frequency 与 Sensor datasheet 对齐",
            "延长 RESET 低有效时间到 ≥ 5ms",
            "依照 Sensor EVK 板级参考设计调整上电时序",
        ],
        dyn_res_risks=[
            "变分辨率时 Sensor 需重新执行寄存器组切换(group hold)，若 I2C 吞吐不足会漏帧",
            "切换分辨率后 MCLK/PLL 改变需等待锁定（通常 5~30ms），期间不得触发 CSI 采集",
        ],
    ),

    PipelineStage(
        name="MIPI_CSI",
        zh_name="MIPI CSI-2 接口层",
        risk_level="HIGH",
        anomalies=[
            "CRC/ECC 错误频发 (dphy_err_cnt 持续增长)",
            "Lane 失同步 / FIFO 溢出",
            "帧头/行头解析失败 (FSD/FED 丢失)",
            "Pixel 数据错位 (Lane skew 过大)",
        ],
        root_causes=[
            "MIPI D-PHY Lane 数或速率配置与 Sensor 不一致",
            "PCB 走线 Lane 间 skew > 允许值 (通常 < 150ps)",
            "过长电缆或 FPC 造成信号反射/损耗",
            "双目两路 MIPI 使用同一 DPHY，VC（Virtual Channel）未分离",
        ],
        diag_cmds=[
            "cat /proc/media-devices                   # 查看媒体设备",
            "media-ctl -d /dev/media0 -p               # 查看 pipeline 拓扑",
            "cat /sys/bus/platform/drivers/mipi-csi/*/statistics  # CSI 统计",
            "dmesg | grep -iE 'dphy|crc|lane|mipi'    # MIPI 错误日志",
            "v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=10 2>&1 | grep 'Frame#'",
        ],
        fixes=[
            "检查 DTS link-frequencies 与 Sensor datasheet 的 MIPI 速率匹配",
            "双目需配置两个独立 DPHY 控制器，或使用 VC0/VC1 分离",
            "过布线检查：差分对等长、层间换层需加过孔电容补偿",
            "排查 FPC cable: 换短线或增加终端电阻",
        ],
        dyn_res_risks=[
            "变分辨率时 MIPI bit rate 变化，需重新训练 D-PHY (LP → HS 重建)",
            "若不停流直接切换，可能出现 FSD 错位导致宽高参数被错误解析",
            "双目同步变分辨率时须保证两路 MIPI 同步切换，避免帧 ID 错位",
        ],
    ),

    PipelineStage(
        name="VI",
        zh_name="VI 视频输入模块 (Video Input)",
        risk_level="CRITICAL",
        anomalies=[
            "VI 通道无数据输出 / 帧计数不增加",
            "图像花屏 / 绿屏 / 滚屏",
            "VI DROP 帧计数持续增长",
            "VI Buffer 超时等待",
            "宽高参数不匹配导致 crop 越界",
        ],
        root_causes=[
            "VI 绑定的 MIPI Dev 通道号配置错误",
            "VI 输入属性（宽高/帧率/像素格式）与 Sensor 实际输出不一致",
            "VI 帧缓冲数量不足（< 3），高帧率时出现覆盖",
            "VI→ISP/VPSS 绑定未建立或 Pipe 未使能",
            "变分辨率时 VI 属性未同步更新（旧宽高残留）",
        ],
        diag_cmds=[
            "# HiSilicon/海思示例",
            "cat /proc/umap/vi                          # VI 通道状态",
            "cat /proc/umap/vi | grep -E 'drop|lost'    # 丢帧统计",
            "# Rockchip 示例",
            "cat /proc/rkcif-mipi-lvds0/mipi_id0        # RKCIF 统计",
            "v4l2-ctl -d /dev/video0 --get-fmt-video    # 当前格式",
            "v4l2-ctl -d /dev/video0 --stream-mmap --stream-count=30 --stream-skip=0 2>&1 | tail -5",
        ],
        fixes=[
            "对齐 VI 通道宽高与 Sensor 寄存器组输出宽高（包括消隐区）",
            "变分辨率前必须先 VI_StopPipe → 修改属性 → VI_StartPipe",
            "帧缓冲数量设置为 ≥ 4（特别是 30fps 以上）",
            "双目分配独立 VI Pipe，避免通道 ID 冲突",
            "使能 VI 溢出中断，记录 overflow_cnt 超阈值告警",
        ],
        dyn_res_risks=[
            "直接修改 VI 宽高而不重启 Pipe，可能导致 DMA 写地址越界（内存踩踏）",
            "双目同步切换分辨率时，若两路时序不同步，会出现左右帧错位",
            "变分辨率后 VI 输出 stride 变化，需通知下游 VPSS 同步更新 stride",
        ],
    ),

    PipelineStage(
        name="ISP",
        zh_name="ISP 图像信号处理",
        risk_level="MED",
        anomalies=[
            "3A (AE/AWB/AF) 收敛失败或振荡",
            "图像色偏 / 过曝 / 欠曝",
            "噪点异常 (NR 参数与分辨率不匹配)",
            "ISP Pipeline 吞吐瓶颈导致帧率下降",
        ],
        root_causes=[
            "AE 统计区域配置未按新分辨率缩放",
            "LSC/CCM/Gamma 标定表针对旧分辨率，新分辨率未重新标定",
            "ISP 时钟频率不够支撑高分辨率帧率",
            "双目两路共用一套 ISP 参数，但两路 Sensor 特性不同",
        ],
        diag_cmds=[
            "# 查看 ISP 统计",
            "cat /proc/umap/isp                         # 海思 ISP 状态",
            "v4l2-ctl -d /dev/v4l-subdev0 -l            # ISP 控件列表",
            "v4l2-ctl -d /dev/v4l-subdev0 --get-ctrl=exposure,gain  # AE 状态",
            "dmesg | grep -i 'isp\\|3a\\|awb\\|aec'",
        ],
        fixes=[
            "变分辨率后重新计算 3A 统计区域坐标（按比例缩放）",
            "针对不同分辨率档位准备独立 ISP Tuning 参数文件，动态切换",
            "双目各路 ISP 独立 Tuning，避免互相干扰",
            "确保 ISP 时钟 ≥ 像素时钟（W × H × FPS × 1.1）",
        ],
        dyn_res_risks=[
            "切换分辨率时 ISP pipeline 需 flush，未 flush 的旧分辨率帧会污染输出",
            "统计 ROI 坐标若不随分辨率缩放，AE 区域越界会引发 ISP 卡死",
        ],
    ),

    PipelineStage(
        name="VPSS",
        zh_name="VPSS 视频处理子系统 (缩放/裁剪)",
        risk_level="HIGH",
        anomalies=[
            "VPSS 缩放输出图像拉伸/压缩失真",
            "VPSS 通道输出黑帧",
            "VPSS 处理延迟增大，端到端时延超标",
            "缩放比超出硬件限制（如超过 1/16 缩小）",
            "Stride 对齐错误导致图像偏移",
        ],
        root_causes=[
            "VPSS Group 输入宽高未随 VI 分辨率变化同步更新",
            "缩放比超过芯片允许的最大/最小比例",
            "VPSS 输出通道 Stride 未按 64/128 字节对齐",
            "VPSS 时钟分频配置在低分辨率时过高，浪费功耗；高分辨率时过低，吞吐不足",
        ],
        diag_cmds=[
            "cat /proc/umap/vpss                       # 海思 VPSS 状态",
            "cat /proc/umap/vpss | grep -E 'drop|fail' # 异常帧",
            "# 检查输出 stride 对齐",
            "python3 -c \"w=1920; align=64; print('stride=', (w*2+align-1)//align*align)\"",
        ],
        fixes=[
            "变分辨率前 VPSS_StopGrp → 更新 GrpAttr → VPSS_StartGrp",
            "验证缩放比：输出宽 ≥ 输入宽/16，输出高 ≥ 输入高/16",
            "输出 Stride 强制按 align=64 字节对齐",
            "双目各路 VPSS Group 独立，互不绑定",
        ],
        dyn_res_risks=[
            "同一 VPSS Group 挂多个输出通道，变分辨率时需全部通道同步停止再重启",
            "变分辨率产生的临时分辨率（如切换中间帧）可能超出 VPSS 硬件缩放范围",
        ],
    ),

    PipelineStage(
        name="VENC",
        zh_name="VENC 视频编码模块",
        risk_level="HIGH",
        anomalies=[
            "VENC 通道编码失败 / 返回 ERR_BUSY",
            "码流 BitRate 超标 / 帧率异常",
            "编码帧延迟增大，P/B 帧队列堆积",
            "VENC Buffer 满丢帧 (stream_buf_full)",
            "变分辨率后出现绿线/花屏 I 帧",
        ],
        root_causes=[
            "VENC 通道创建时设定的宽高与实际输入不一致",
            "GOP 结构在变分辨率时未强制插入 IDR 帧",
            "码率控制参数（maxQP/minQP）在低分辨率时配置过高导致码率虚高",
            "VENC 输出码流 buffer size 按最大分辨率分配，切换后未缩小，内存浪费",
            "双目共用一个 VENC 码流缓冲区，写竞争",
        ],
        diag_cmds=[
            "cat /proc/umap/venc                        # 海思 VENC 状态",
            "cat /proc/umap/venc | grep -E 'buf|drop|stream_lost'",
            "# 抓取码流验证",
            "dd if=/dev/venc0 of=/tmp/test.h265 bs=4096 count=300",
            "ffprobe -v quiet -show_streams /tmp/test.h265 | grep -E 'width|height|r_frame'",
        ],
        fixes=[
            "变分辨率必须执行：VENC_StopRecvPic → 销毁通道 → 重建通道（新宽高）→ VENC_StartRecvPic",
            "切换分辨率时强制发送 Request IDR，保证解码器正确刷新",
            "双目使用独立 VENC 通道，各自独立 buffer",
            "码流 buffer size = 目标码率(bps) / 8 * 2（至少 2 秒缓冲）",
            "低分辨率档位调低 maxBitrate，避免 QP 饱和",
        ],
        dyn_res_risks=[
            "H.265/H.264 编码器状态机在切换宽高时需完整重置，否则 SPS/PPS 参数错误",
            "ROI 编码区域坐标需按新分辨率重新设置，否则 ROI 越界触发编码器异常",
            "双目不同分辨率编码时，若时间戳不同步，播放端会出现左右画面不对齐",
        ],
    ),

    PipelineStage(
        name="MEM_DDR",
        zh_name="内存/DDR 带宽管理",
        risk_level="CRITICAL",
        anomalies=[
            "内存分配失败 (ENOMEM / MMZ 耗尽)",
            "DDR 带宽饱和，导致 VI/VPSS/VENC 全线 DROP 帧",
            "Cache 一致性问题导致数据错乱",
            "物理地址不连续导致 DMA 失败",
        ],
        root_causes=[
            "双目 4MP@30fps 原始数据带宽超过 DDR 理论带宽",
            "多个模块使用同一 DDR 端口，优先级未配置",
            "MMZ（Media Memory Zone）分配过小，不足以容纳所有帧缓冲",
            "用户态 malloc 与 MMZ 混用，导致物理连续性失效",
        ],
        diag_cmds=[
            "free -m                                    # 系统内存",
            "cat /proc/umap/mmz                        # MMZ 使用情况（海思）",
            "cat /proc/buddyinfo                       # 内存碎片",
            "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq  # CPU 频率",
            "# DDR 带宽监控（平台相关）",
            "perf stat -e cache-misses -a sleep 1",
        ],
        fixes=[
            "预先计算双目各分辨率所需 MMZ 大小（见下方计算表），启动时静态预留",
            "配置 QoS：VI/VENC 设为高优先级，AI 推理设为低优先级",
            "帧缓冲统一使用 MMZ/ION/CMA 分配，禁止 kmalloc 大块连续内存",
            "开启 IOMMU（如平台支持），缓解物理连续内存压力",
        ],
        dyn_res_risks=[
            "变分辨率时若先分配新缓冲再释放旧缓冲，峰值内存 = 新 + 旧，可能爆 MMZ",
            "应先停止所有通道、完整释放旧缓冲，再按新分辨率分配",
        ],
    ),

    PipelineStage(
        name="SYNC_DUAL",
        zh_name="双目同步时序",
        risk_level="HIGH",
        anomalies=[
            "左右帧时间戳不同步（差值 > 1 frame 周期）",
            "双目左右画面相差 N 帧（视差匹配错误）",
            "一路正常另一路 DROP 帧，导致帧 ID 持续偏移",
        ],
        root_causes=[
            "两路 Sensor 未使用硬件 FSYNC 同步信号，依靠软件 trigger 误差大",
            "主从模式下，从 Sensor 的 FSYNC 极性/时序配置错误",
            "双目中断处理在多核 SMP 上不均衡，时间戳打刻时机不一致",
        ],
        diag_cmds=[
            "# 检查 Sensor FSYNC GPIO",
            "cat /sys/kernel/debug/gpio | grep fsync",
            "# 打印双路时间戳差",
            "v4l2-ctl -d /dev/video0 --stream-mmap -c 30 2>&1 | grep timestamp",
            "v4l2-ctl -d /dev/video2 --stream-mmap -c 30 2>&1 | grep timestamp",
        ],
        fixes=[
            "Sensor 配置为 Master/Slave FSYNC 硬件同步，确保曝光时刻对齐",
            "时间戳在 VI 中断 ISR 内打刻（不在用户态），减少 OS 调度抖动",
            "双目 VI 通道绑定到同一 VPSS Group，利用硬件帧对齐功能",
            "增加帧同步检测逻辑：若双路时戳差 > 2×帧周期，主动丢帧重同步",
        ],
        dyn_res_risks=[
            "双目变分辨率时两路切换时序不一致，会产生单路先切换、对应帧已错位的问题",
            "建议使用状态机：STOP_ALL → SWITCH_BOTH → START_ALL，不允许单路切换",
        ],
    ),
]


# ══════════════════════════════════════════════
# 输出函数
# ══════════════════════════════════════════════

RISK_COLOR = {
    "LOW":      "green",
    "MED":      "yellow",
    "HIGH":     "red",
    "CRITICAL": "bold red",
}

RISK_ICON = {
    "LOW":      "[ OK ]",
    "MED":      "[WARN]",
    "HIGH":     "[HIGH]",
    "CRITICAL": "[CRIT]",
}


def print_pipeline_analysis(stage: PipelineStage, detail: bool = False):
    risk_icon = RISK_ICON[stage.risk_level]
    header = f"{risk_icon} [{stage.name}] {stage.zh_name}  风险等级: {stage.risk_level}"

    if _RICH:
        color = RISK_COLOR[stage.risk_level]
        console.rule(f"[{color}]{header}[/{color}]")
    else:
        print("\n" + "=" * 70)
        print(header)
        print("=" * 70)

    sections = [
        ("常见异常现象", stage.anomalies),
        ("根因分析",     stage.root_causes),
        ("诊断命令",     stage.diag_cmds),
        ("修复建议",     stage.fixes),
    ]
    if stage.dyn_res_risks:
        sections.append(("变分辨率特有风险", stage.dyn_res_risks))

    for title, items in sections:
        if not detail and title in ("诊断命令",):
            continue
        if _RICH:
            console.print(f"  [bold cyan]{title}[/bold cyan]")
            for item in items:
                console.print(f"    • {item}")
        else:
            print(f"\n  {title}:")
            for item in items:
                print(f"    • {item}")


def print_resolution_table(fps_list: List[int], cameras: int = 2):
    header_note = f"分辨率/帧率/内存 计算表（{cameras} 路双目摄像头）"

    if _RICH:
        table = Table(
            title=header_note,
            box=box.DOUBLE_EDGE,
            show_lines=True,
            header_style="bold magenta",
        )
        cols = [
            ("分辨率",      "cyan"),
            ("像素(W×H)",   "white"),
            ("MP",         "white"),
        ]
        for fps in fps_list:
            cols += [
                (f"RAW带宽\n{fps}fps(MB/s)",  "yellow"),
                (f"YUV带宽\n{fps}fps(MB/s)",  "green"),
                (f"H265码率\n{fps}fps(Mbps)", "blue"),
                (f"帧缓冲×3×{cameras}路(MB)", "red"),
            ]
        for name, style in cols:
            table.add_column(name, style=style, justify="right")

        for r in RESOLUTIONS:
            row = [r.name, f"{r.width}×{r.height}", ""]
            # 取第一个 fps 算 MP（固定值）
            bw0 = calc_bandwidth(r, fps_list[0])
            row[2] = str(bw0["pixels_mp"])
            for fps in fps_list:
                bw = calc_bandwidth(r, fps)
                row += [
                    str(bw["raw_bw_mbps"] * cameras),
                    str(bw["yuv_bw_mbps"] * cameras),
                    str(bw["h265_mbps"]   * cameras),
                    str(bw["dual_buf_mb"]),
                ]
            table.add_row(*row)

        console.print(table)
    else:
        print(f"\n{'='*90}")
        print(f"  {header_note}")
        print(f"{'='*90}")
        hdr = f"{'分辨率':<12} {'W×H':<14} {'MP':>4}"
        for fps in fps_list:
            hdr += f"  {'RAW(MB/s)':>10} {'YUV(MB/s)':>10} {'H265(Mbps)':>11} {'帧buf(MB)':>9}"
        print(hdr)
        print("-" * len(hdr))
        for r in RESOLUTIONS:
            bw0 = calc_bandwidth(r, fps_list[0])
            row = f"{r.name:<12} {r.width}×{r.height:<8} {bw0['pixels_mp']:>4}"
            for fps in fps_list:
                bw = calc_bandwidth(r, fps)
                row += (
                    f"  {bw['raw_bw_mbps']*cameras:>10.1f}"
                    f"  {bw['yuv_bw_mbps']*cameras:>10.1f}"
                    f"  {bw['h265_mbps']*cameras:>11.1f}"
                    f"  {bw['dual_buf_mb']:>9.1f}"
                )
            print(row)


def print_ddr_risk_summary(fps: int = 30, cameras: int = 2):
    """DDR 带宽红线预警"""
    title = f"DDR 带宽风险预警 ({cameras}路, {fps}fps)"
    if _RICH:
        console.rule(f"[bold red]{title}[/bold red]")
    else:
        print(f"\n{'='*60}\n  {title}\n{'='*60}")

    # 常见 SOC DDR 参考带宽 (实测可用约 50%)
    ddr_ref = {
        "HI3519DV500 (LPDDR4X-4266)": 4266 * 4 / 8 * 0.5,   # ~1066 MB/s 可用
        "RV1126 (DDR4-1600)":          1600 * 2 / 8 * 0.5,
        "RK3588 (LPDDR5-6400)":        6400 * 4 / 8 * 0.5,
        "CV5 (LPDDR4X-4266)":          4266 * 4 / 8 * 0.5,
    }

    rows = []
    for r in RESOLUTIONS:
        bw = calc_bandwidth(r, fps)
        total = bw["raw_bw_mbps"] * cameras + bw["yuv_bw_mbps"] * cameras + bw["h265_mbps"] * cameras / 8
        rows.append((r.name, f"{r.width}×{r.height}", total))

    for soc, avail in ddr_ref.items():
        if _RICH:
            t2 = Table(title=f"SOC: {soc}  可用DDR≈{avail:.0f}MB/s",
                       box=box.SIMPLE, show_header=True, header_style="bold")
            t2.add_column("分辨率", style="cyan")
            t2.add_column("W×H", style="white")
            t2.add_column(f"总带宽需求(MB/s,{cameras}路)", style="yellow")
            t2.add_column("余量(MB/s)", style="green")
            t2.add_column("风险", style="red")
            for rname, res, need in rows:
                margin = avail - need
                risk = "OK" if margin > 100 else ("警告" if margin > 0 else "超标!")
                t2.add_row(rname, res, f"{need:.1f}", f"{margin:.1f}", risk)
            console.print(t2)
        else:
            print(f"\n  SOC: {soc}  可用DDR≈{avail:.0f}MB/s")
            print(f"    {'分辨率':<12} {'W×H':<14} {'需求(MB/s)':>12} {'余量(MB/s)':>12} {'风险':>6}")
            for rname, res, need in rows:
                margin = avail - need
                risk = "OK" if margin > 100 else ("警告" if margin > 0 else "超标!")
                print(f"    {rname:<12} {res:<14} {need:>12.1f} {margin:>12.1f} {risk:>6}")


def print_dyn_res_checklist():
    """变分辨率操作安全流程"""
    title = "变分辨率安全操作流程 (State Machine)"
    checklist = [
        "1. [应用层] 发送分辨率切换请求，进入 SWITCHING 状态，拒绝新的取流请求",
        "2. [VENC]  VENC_StopRecvPic(all channels)",
        "3. [VENC]  等待 VENC flush 完成（轮询 stream_buf_empty 或超时 200ms）",
        "4. [VENC]  销毁所有 VENC 通道",
        "5. [VPSS]  VPSS_StopGrp → VPSS_DisableChn（所有输出通道）",
        "6. [VI]    VI_StopPipe → VI_DisableChn → VI_DestroyPipe",
        "7. [Sensor] 通过 I2C 写入新分辨率寄存器组（Group Hold 方式）",
        "8. [Sensor] 等待 Sensor PLL 锁定稳定（≥ 2 帧时间，约 60ms @30fps）",
        "9. [MIPI]  重新配置 DPHY：更新 bit_rate / lane_num",
        "10.[VI]    按新宽高重建 VI Pipe 及通道，VI_StartPipe",
        "11.[ISP]   更新 3A 统计区域，重载 Tuning 参数文件",
        "12.[VPSS]  按新尺寸重建 VPSS Group 及所有输出通道",
        "13.[VENC]  按新尺寸重建 VENC 通道，发送 IDR 请求，VENC_StartRecvPic",
        "14.[同步检查] 双目帧时间戳差值 < 1 frame，恢复 RUNNING 状态",
        "15.[内存]  释放旧分辨率帧缓冲（步骤 6 后即可，不要提前释放）",
    ]
    if _RICH:
        console.rule(f"[bold green]{title}[/bold green]")
        for item in checklist:
            style = "red" if "超标" in item or "销毁" in item or "停止" in item else "white"
            console.print(f"  {item}", style=style)
    else:
        print(f"\n{'='*70}\n  {title}\n{'='*70}")
        for item in checklist:
            print(f"  {item}")


# ══════════════════════════════════════════════
# 主程序
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="SOC 双目摄像头 VI/VENC 流水线异常排查 + 分辨率/帧率/内存计算",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 dual_cam_soc_diag.py                  # 全部分析
  python3 dual_cam_soc_diag.py --stage vi venc  # 仅分析 VI/VENC
  python3 dual_cam_soc_diag.py --table-only     # 仅显示计算表
  python3 dual_cam_soc_diag.py --fps 15 25 30   # 自定义帧率
  python3 dual_cam_soc_diag.py --cameras 1      # 单路模式
  python3 dual_cam_soc_diag.py --detail         # 包含诊断命令
""",
    )
    parser.add_argument("--stage",       nargs="*", default=None,
                        help="仅分析指定环节(vi/venc/isp/mipi/mem/sync/sensor/vpss)")
    parser.add_argument("--fps",         nargs="+",  type=int,
                        default=[15, 25, 30], help="帧率列表（默认 15 25 30）")
    parser.add_argument("--cameras",     type=int,   default=2,
                        help="摄像头路数（1 单目 / 2 双目），默认 2")
    parser.add_argument("--table-only",  action="store_true",
                        help="仅显示分辨率计算表")
    parser.add_argument("--detail",      action="store_true",
                        help="显示诊断命令")
    parser.add_argument("--no-ddr",      action="store_true",
                        help="跳过 DDR 风险预警")
    parser.add_argument("--no-checklist",action="store_true",
                        help="跳过变分辨率安全操作流程")

    args = parser.parse_args()

    # ── 标题 ──
    if _RICH:
        console.print(Panel.fit(
            "[bold cyan]SOC 双目摄像头 嵌入式流水线 异常排查工具[/bold cyan]\n"
            "[dim]VI → ISP → VPSS → VENC | 变分辨率安全分析 | 内存带宽计算[/dim]",
            border_style="bright_blue",
        ))
    else:
        print("\n" + "#"*70)
        print("#  SOC 双目摄像头 嵌入式流水线 异常排查工具")
        print("#  VI -> ISP -> VPSS -> VENC | 变分辨率 | 内存带宽计算")
        print("#"*70)

    # ── 流水线分析 ──
    if not args.table_only:
        stage_filter = [s.upper() for s in args.stage] if args.stage else None
        shown = 0
        for stage in PIPELINE_STAGES:
            key = stage.name.split("_")[0]
            if stage_filter is None or stage.name in stage_filter or key in stage_filter:
                print_pipeline_analysis(stage, detail=args.detail)
                shown += 1
        if shown == 0:
            _print(f"[yellow]未找到匹配的环节: {args.stage}[/yellow]")

        # ── 变分辨率安全流程 ──
        if not args.no_checklist:
            print_dyn_res_checklist()

    # ── 分辨率/帧率/内存计算表 ──
    print_resolution_table(args.fps, cameras=args.cameras)

    # ── DDR 风险预警 ──
    if not args.no_ddr and not args.table_only:
        # 取帧率最大值做压力测试
        print_ddr_risk_summary(fps=max(args.fps), cameras=args.cameras)

    if _RICH:
        console.rule("[dim]分析完毕[/dim]")
    else:
        print("\n" + "="*70 + "\n  分析完毕\n" + "="*70)


if __name__ == "__main__":
    main()
