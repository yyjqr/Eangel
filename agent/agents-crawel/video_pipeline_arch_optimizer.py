#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
video_pipeline_arch_optimizer.py
================================
ISP 视频数据流架构分析与运行时优化工具

覆盖内容:
  - CIS -> ISP -> DMA -> DDR -> CPU -> APP 全链路数据流梳理
  - SMP / AMP / ARMv5 架构设计建议
  - 带宽、缓冲区、变分辨率峰值内存估算
  - DMA / Stride / Cache / IRQ / VB Pool 风险识别
  - 导出 Markdown / JSON，方便 Hermes 等运行时系统接入
"""

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Dict, List

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    _RICH = True
except ImportError:
    _RICH = False

console = Console() if _RICH else None


def _print(text: str, style: str = ""):
    if _RICH and console:
        console.print(text, style=style)
    else:
        print(text)


def align_up(value: int, align: int) -> int:
    return ((value + align - 1) // align) * align


def mib(value: float) -> float:
    return value / 1024 / 1024


@dataclass
class ResolutionSpec:
    name: str
    width: int
    height: int
    bpp_raw: int = 12
    bpp_yuv: int = 12


@dataclass
class PlatformProfile:
    key: str
    title: str
    runtime_model: str
    ddr_budget_mb_s: float
    cache_coherent: bool
    design_points: List[str]
    focus_points: List[str]


@dataclass
class BranchProfile:
    key: str
    title: str
    ddr_read_factor: float
    ddr_write_factor: float
    buffer_factor: float
    cpu_touch: bool
    notes: List[str]


@dataclass
class RiskItem:
    severity: str
    area: str
    symptom: str
    reason: str
    action: str


@dataclass
class ActionItem:
    priority: str
    category: str
    title: str
    detail: str


COMMON_RESOLUTIONS: List[ResolutionSpec] = [
    ResolutionSpec("4MP-W", 2560, 1600, 12, 12),
    ResolutionSpec("4MP", 2592, 1520, 12, 12),
    ResolutionSpec("4MP-SQ", 2048, 2048, 12, 12),
    ResolutionSpec("3MP", 2304, 1296, 10, 12),
    ResolutionSpec("3MP-VGA", 2048, 1536, 10, 12),
    ResolutionSpec("2MP-FHD", 1920, 1080, 10, 12),
    ResolutionSpec("2MP-UXGA", 1600, 1200, 10, 12),
    ResolutionSpec("1.3MP", 1280, 1024, 10, 12),
    ResolutionSpec("1MP-720P", 1280, 720, 10, 12),
    ResolutionSpec("1MP-960P", 1280, 960, 10, 12),
]

PLATFORM_PROFILES: Dict[str, PlatformProfile] = {
    "smp": PlatformProfile(
        key="smp",
        title="SMP 多核 Cortex-A",
        runtime_model="Linux / POSIX Threads / IRQ Affinity",
        ddr_budget_mb_s=1800.0,
        cache_coherent=True,
        design_points=[
            "收帧线程、DQBUF/QBUF 线程与 ISP 下半部尽量绑同核",
            "使用 cpuset/isolcpus 为视频热路径保留 CPU",
            "中断与工作线程减少跨核迁移，降低 cache miss",
        ],
        focus_points=[
            "线程亲和性",
            "上下文切换削减",
            "VENC/AI/网络线程拆分",
        ],
    ),
    "amp": PlatformProfile(
        key="amp",
        title="AMP 异构多核",
        runtime_model="Cortex-A Linux + Cortex-M/DSP RTOS/FW",
        ddr_budget_mb_s=1200.0,
        cache_coherent=False,
        design_points=[
            "逐帧 3A 留在 M 核/DSP/FW 侧，A 核只做策略控制",
            "Mailbox 只传命令与事件，共享内存只传 metadata/buffer handle",
            "共享内存必须定义所有权、序号和 cache policy",
        ],
        focus_points=[
            "Mailbox 极简非阻塞",
            "共享内存一致性",
            "A/M 核职责边界",
        ],
    ),
    "armv5": PlatformProfile(
        key="armv5",
        title="ARMv5 精简平台",
        runtime_model="Bare-Metal / RTOS / 单核 Linux",
        ddr_budget_mb_s=480.0,
        cache_coherent=False,
        design_points=[
            "热路径定点数计算，避免浮点",
            "固定大小静态对象池，避免运行时频繁分配",
            "先在 ISP/VPSS 降分辨率，再给 CPU/APP",
        ],
        focus_points=[
            "定点运算",
            "静态内存",
            "低分辨率低帧率优先",
        ],
    ),
}

BRANCH_PROFILES: Dict[str, BranchProfile] = {
    "venc": BranchProfile(
        key="venc",
        title="VENC 编码",
        ddr_read_factor=1.0,
        ddr_write_factor=0.02,
        buffer_factor=0.15,
        cpu_touch=False,
        notes=[
            "编码器需要稳定码流输入，切分辨率必须重建通道并发 IDR",
            "码流缓冲建议至少覆盖 2 秒目标码率",
        ],
    ),
    "preview": BranchProfile(
        key="preview",
        title="Preview/Display 预览",
        ddr_read_factor=1.0,
        ddr_write_factor=0.35,
        buffer_factor=0.35,
        cpu_touch=False,
        notes=[
            "优先在 VPSS 做缩放后直出 display，避免 APP 侧二次缩放",
            "显示支路不应拖慢主码流路由",
        ],
    ),
    "ai": BranchProfile(
        key="ai",
        title="AI/NPU 分支",
        ddr_read_factor=0.8,
        ddr_write_factor=0.15,
        buffer_factor=0.25,
        cpu_touch=True,
        notes=[
            "优先从 VPSS 输出低分辨率 AI 路，避免主路全分辨率进 CPU",
            "如果 AI 前处理在 CPU 侧，Cache 与 DDR 压力会上升",
        ],
    ),
    "app": BranchProfile(
        key="app",
        title="APP 取流",
        ddr_read_factor=1.0,
        ddr_write_factor=0.05,
        buffer_factor=0.00,
        cpu_touch=True,
        notes=[
            "如果 APP 只关心元数据，应避免逐帧触碰整帧像素",
            "优先传 DMABUF FD、Buffer ID、Metadata，避免 memcpy",
        ],
    ),
}

SEVERITY_RANK = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MED": 2,
    "LOW": 1,
}


def list_resolution_text() -> str:
    return "\n".join(
        f"  - {item.name:<8} {item.width}x{item.height} RAW{item.bpp_raw}"
        for item in COMMON_RESOLUTIONS
    )


def parse_resolution(spec: str, raw_bpp: int, yuv_bpp: int) -> ResolutionSpec:
    normalized = spec.strip().lower()
    for item in COMMON_RESOLUTIONS:
        if item.name.lower() == normalized:
            return ResolutionSpec(item.name, item.width, item.height, raw_bpp or item.bpp_raw, yuv_bpp)

    if "x" in normalized:
        width_str, height_str = normalized.split("x", 1)
        width = int(width_str)
        height = int(height_str)
        return ResolutionSpec(f"{width}x{height}", width, height, raw_bpp, yuv_bpp)

    raise ValueError(f"未知分辨率: {spec}")


def yuv_bpp_for(fmt: str) -> int:
    if fmt.lower() in {"nv12", "nv21"}:
        return 12
    if fmt.lower() in {"yuyv", "uyvy"}:
        return 16
    raise ValueError(f"不支持的 YUV 格式: {fmt}")


def calc_bandwidth(resolution: ResolutionSpec, fps: int, cameras: int) -> Dict[str, float]:
    pixels = resolution.width * resolution.height
    raw_bw_mb_s = pixels * fps * resolution.bpp_raw / 8 / 1024 / 1024 * cameras
    yuv_bw_mb_s = pixels * fps * resolution.bpp_yuv / 8 / 1024 / 1024 * cameras
    h265_mbps = pixels * fps * 0.07 / 1_000_000 * cameras
    frame_buf_mb = pixels * (resolution.bpp_yuv / 8) / 1024 / 1024
    return {
        "pixels": pixels,
        "pixels_mp": round(pixels / 1_000_000, 2),
        "raw_bw_mb_s": raw_bw_mb_s,
        "yuv_bw_mb_s": yuv_bw_mb_s,
        "h265_mbps": h265_mbps,
        "h265_mb_s": h265_mbps / 8,
        "frame_buf_mb": frame_buf_mb * cameras,
    }


def calc_layout(resolution: ResolutionSpec, align: int, yuv_format: str) -> Dict[str, float]:
    raw_line_bytes_exact = math.ceil(resolution.width * resolution.bpp_raw / 8)
    raw_stride_bytes = align_up(raw_line_bytes_exact, align)
    raw_frame_bytes = raw_stride_bytes * resolution.height

    if yuv_format.lower() in {"nv12", "nv21"}:
        y_line_bytes_exact = resolution.width
        y_stride_bytes = align_up(y_line_bytes_exact, align)
        uv_height = math.ceil(resolution.height / 2)
        yuv_frame_bytes = y_stride_bytes * resolution.height + y_stride_bytes * uv_height
    else:
        y_line_bytes_exact = resolution.width * 2
        y_stride_bytes = align_up(y_line_bytes_exact, align)
        yuv_frame_bytes = y_stride_bytes * resolution.height

    return {
        "raw_line_bytes_exact": raw_line_bytes_exact,
        "raw_stride_bytes": raw_stride_bytes,
        "raw_frame_mb": mib(raw_frame_bytes),
        "y_line_bytes_exact": y_line_bytes_exact,
        "y_stride_bytes": y_stride_bytes,
        "yuv_frame_mb": mib(yuv_frame_bytes),
    }


def build_branch_loads(base_yuv_bw_mb_s: float, bitstream_mb_s: float, branches: List[str]) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for key in branches:
        profile = BRANCH_PROFILES[key]
        write_mb_s = bitstream_mb_s if key == "venc" else base_yuv_bw_mb_s * profile.ddr_write_factor
        rows.append({
            "key": key,
            "title": profile.title,
            "read_mb_s": base_yuv_bw_mb_s * profile.ddr_read_factor,
            "write_mb_s": write_mb_s,
            "buffer_factor": profile.buffer_factor,
        })
    return rows


def build_trace_points(fps: int, branches: List[str]) -> List[Dict[str, str]]:
    frame_period_ms = 1000.0 / fps
    points = [
        {
            "name": "t0 Sensor Frame Start",
            "owner": "CIS/FSYNC",
            "metric": "sensor_irq_hz",
            "budget": f"{frame_period_ms:.2f}ms 周期内稳定触发",
        },
        {
            "name": "t1 CSI SOF/EOF",
            "owner": "MIPI CSI-2",
            "metric": "csi_frame_done_hz",
            "budget": "不应低于目标 fps",
        },
        {
            "name": "t2 ISP DMA Done",
            "owner": "ISP/DMA",
            "metric": "dma_done_hz",
            "budget": "应与目标 fps 对齐",
        },
        {
            "name": "t3 IRQ Ack Complete",
            "owner": "ISR/Bottom Half",
            "metric": "irq_service_ms",
            "budget": "< 0.20ms",
        },
        {
            "name": "t4 VB Pool Route",
            "owner": "SDK Core",
            "metric": "dma_done_to_route_ms",
            "budget": "< 0.50ms",
        },
        {
            "name": "t5 DQBUF/App Consume",
            "owner": "APP Thread",
            "metric": "dqbuf_latency_ms",
            "budget": f"< {frame_period_ms:.2f}ms",
        },
    ]
    if "venc" in branches:
        points.append({
            "name": "t6 VENC Stream Ready",
            "owner": "VENC",
            "metric": "venc_out_latency_ms",
            "budget": f"< {frame_period_ms * 1.5:.2f}ms",
        })
    return points


def detect_risks(
    profile: PlatformProfile,
    resolution: ResolutionSpec,
    fps: int,
    cameras: int,
    align: int,
    buffer_depth: int,
    branches: List[str],
    layout: Dict[str, float],
    total_ddr_mb_s: float,
    noncoherent: bool,
    dynamic_resolution: bool,
) -> List[RiskItem]:
    risks: List[RiskItem] = []
    pixels = resolution.width * resolution.height
    ddr_ratio = total_ddr_mb_s / profile.ddr_budget_mb_s if profile.ddr_budget_mb_s else 0.0
    cpu_touch = any(BRANCH_PROFILES[key].cpu_touch for key in branches)

    if layout["raw_stride_bytes"] != layout["raw_line_bytes_exact"]:
        risks.append(RiskItem(
            severity="HIGH",
            area="DMA/Stride",
            symptom="RAW 画面绿条、斜纹、行错位",
            reason=f"RAW 行宽 {layout['raw_line_bytes_exact']:.0f}B 不是 {align}B 对齐，DMA stride 必须单独配置为 {layout['raw_stride_bytes']:.0f}B",
            action="把 sensor 输出宽度、RAW 打包格式与 DMA stride 参数统一到同一公式上",
        ))

    if layout["y_stride_bytes"] != layout["y_line_bytes_exact"]:
        risks.append(RiskItem(
            severity="MED",
            area="VPSS/VENC",
            symptom="YUV 图像偏移、绿边或尾行脏数据",
            reason=f"Y 面行宽 {layout['y_line_bytes_exact']:.0f}B 不是 {align}B 对齐，YUV stride 需要配置为 {layout['y_stride_bytes']:.0f}B",
            action="统一在 HAL 中封装 stride 计算，禁止模块各自手写公式",
        ))

    if ddr_ratio >= 1.0:
        risks.append(RiskItem(
            severity="CRITICAL",
            area="DDR 带宽",
            symptom="掉帧、DQBUF 卡死、VENC 队列持续积压",
            reason=f"估算总 DDR 吞吐 {total_ddr_mb_s:.1f}MB/s 已超过平台预算 {profile.ddr_budget_mb_s:.1f}MB/s",
            action="先在 VPSS 做缩放或降帧，再进入 AI/APP；必要时降低分辨率或减少分支",
        ))
    elif ddr_ratio >= 0.85:
        risks.append(RiskItem(
            severity="HIGH",
            area="DDR 带宽",
            symptom="高负载时偶发丢帧或帧间抖动",
            reason=f"估算总 DDR 吞吐 {total_ddr_mb_s:.1f}MB/s 已接近平台预算的 {ddr_ratio * 100:.0f}%",
            action="提高 ISP/VENC QoS，隔离 AI/APP 分支，并给 Hermes 建立高水位告警",
        ))

    if buffer_depth < 3:
        risks.append(RiskItem(
            severity="HIGH",
            area="VB Pool",
            symptom="QBUF 耗尽、帧覆盖、突发抖动",
            reason="主路缓冲深度低于三缓冲下限，DMA 写入与用户消费不能充分解耦",
            action="主路缓冲至少 3，双目或高帧率场景建议 4",
        ))

    if noncoherent and cpu_touch:
        risks.append(RiskItem(
            severity="CRITICAL",
            area="Cache 一致性",
            symptom="局部马赛克、色彩错乱、偶发旧帧残留",
            reason="当前平台按非一致性内存建模，且 APP/AI 分支会触碰像素数据，必须显式 clean/invalidate cache",
            action="优先使用 coherent/non-cacheable 视频内存；否则在 DMA 前后严格做 cache maintenance",
        ))

    if profile.key == "armv5" and (pixels > 2_000_000 or fps > 20):
        risks.append(RiskItem(
            severity="CRITICAL",
            area="CPU 算力",
            symptom="帧率不稳、系统响应差、用户态处理拖慢回收",
            reason="ARMv5 单核平台难以稳定承载 2MP+ 或 20fps+ 的应用侧处理",
            action="把主路限制在 1MP~2MP，逐帧业务迁移到 ISP/VPSS 或简化为定点算法",
        ))

    if profile.key == "amp" and "app" in branches:
        risks.append(RiskItem(
            severity="MED",
            area="核间职责",
            symptom="A 核被逐帧数据拖慢，影响控制链路稳定性",
            reason="AMP 模式更适合 A 核做控制与路由，不适合逐帧深度参与 3A 或大分辨率处理",
            action="APP 仅消费 metadata 或低分辨率支路，把逐帧实时算法留在 M 核/DSP/FW",
        ))

    if cameras >= 2 and fps >= 25 and "app" in branches:
        risks.append(RiskItem(
            severity="HIGH",
            area="用户态取流",
            symptom="双目左右帧延迟不一致或回收不及时",
            reason="双路高帧率直接给 APP 取整帧，极易造成 DQBUF/QBUF 不平衡",
            action="APP 只取一条低分辨率分析支路，主码流直接给 VENC/网络/存储",
        ))

    if dynamic_resolution:
        risks.append(RiskItem(
            severity="HIGH",
            area="变分辨率",
            symptom="切换阶段花屏、内存峰值翻倍、解码端花屏",
            reason="变分辨率会同时涉及 sensor、MIPI、VI/VPSS/VENC 和缓冲区重建，若顺序错误会留下旧 stride 和旧 SPS/PPS",
            action="执行 stop -> rebuild -> start 状态机，并在 VENC 重建后强制 IDR",
        ))

    risks.sort(key=lambda item: SEVERITY_RANK[item.severity], reverse=True)
    return risks


def build_actions(
    profile: PlatformProfile,
    branches: List[str],
    cameras: int,
    dynamic_resolution: bool,
    noncoherent: bool,
) -> List[ActionItem]:
    actions: List[ActionItem] = [
        ActionItem(
            priority="P0",
            category="内存模型",
            title="统一 VB Pool + Zero-Copy",
            detail="所有视频帧仅通过 Buffer ID / DMABUF FD / Physical Address 流转，禁止在 APP、SDK Core、VENC 之间发生 memcpy。",
        ),
        ActionItem(
            priority="P0",
            category="观测性",
            title="建立 t0~t6 时间戳链路",
            detail="至少记录 Sensor FS、DMA Done、VB Route、DQBUF、VENC Stream Ready，后续 Hermes 才能定位卡点。",
        ),
        ActionItem(
            priority="P0",
            category="缓冲策略",
            title="主路三缓冲起步，双目建议四缓冲",
            detail="DMA 写、用户消费、空闲回收必须并发；双目或多分支时缓冲深度过浅会直接导致覆盖和丢帧。",
        ),
    ]

    if dynamic_resolution:
        actions.append(ActionItem(
            priority="P0",
            category="状态机",
            title="分辨率切换采用 stop-rebuild-start",
            detail="先停 VENC/VPSS/VI，再切 sensor 寄存器组和 DPHY，重建缓冲后再启动，并强制发送 IDR。",
        ))

    if noncoherent or not profile.cache_coherent:
        actions.append(ActionItem(
            priority="P0",
            category="Cache",
            title="把 DMA/CPU Cache 同步收口到 HAL",
            detail="DMA 写前后、CPU 改参数前后统一封装 clean/invalidate，避免业务代码遗漏。",
        ))

    if profile.key == "smp":
        actions.append(ActionItem(
            priority="P1",
            category="调度",
            title="收帧线程与 IRQ 做绑核",
            detail="DQBUF/QBUF、ISP 下半部、中断 affinity 放同核，减少跨核迁移和 cache miss。",
        ))

    if profile.key == "amp":
        actions.append(ActionItem(
            priority="P1",
            category="核间通信",
            title="Mailbox 只传控制，共享内存只传元数据",
            detail="逐帧 3A 和硬实时逻辑保持在 M 核/DSP/FW，A 核不要参与每帧实时运算。",
        ))

    if profile.key == "armv5":
        actions.append(ActionItem(
            priority="P1",
            category="算力约束",
            title="全链路优先硬件降载",
            detail="用 VPSS 先做缩放和裁剪，CPU 侧只看低分辨率支路；算法全部定点化，结构静态化。",
        ))

    if "ai" in branches:
        actions.append(ActionItem(
            priority="P1",
            category="AI 分支",
            title="AI 走低分辨率专用支路",
            detail="优先从 VPSS 输出 AI 尺寸，避免 APP/CPU 对主路整帧做前处理。",
        ))

    if cameras >= 2:
        actions.append(ActionItem(
            priority="P1",
            category="双目同步",
            title="双目统一时钟与统一状态机",
            detail="两路 sensor 采用 FSYNC 或主从同步，分辨率切换必须双路同时 stop / switch / start。",
        ))

    return actions


def build_data_flow(profile: PlatformProfile, branches: List[str]) -> List[str]:
    flow = [
        "CIS/Sensor",
        "MIPI CSI-2",
        "ISP + 3A Stats",
        "DMA Writeback",
        "VB Pool / CMA / MMZ",
        "SDK SYS Router",
        "VPSS / Scale / Crop",
    ]
    for key in branches:
        flow.append(BRANCH_PROFILES[key].title)
    if profile.key == "amp":
        flow.append("Mailbox / Shared Memory / Cortex-M-DSP FW")
    return flow


def build_report(args: argparse.Namespace) -> Dict[str, object]:
    yuv_bpp = yuv_bpp_for(args.yuv_format)
    resolution = parse_resolution(args.resolution, args.raw_bpp, yuv_bpp)
    profile = PLATFORM_PROFILES[args.platform]
    base = calc_bandwidth(resolution, args.fps, args.cameras)
    layout = calc_layout(resolution, args.align, args.yuv_format)
    branch_loads = build_branch_loads(base["yuv_bw_mb_s"], base["h265_mb_s"], args.branches)

    isp_dma_write_mb_s = base["yuv_bw_mb_s"]
    total_ddr_mb_s = isp_dma_write_mb_s
    for item in branch_loads:
        total_ddr_mb_s += item["read_mb_s"] + item["write_mb_s"]

    vb_capture_mb = layout["yuv_frame_mb"] * args.buffer_depth * args.cameras
    branch_buffer_mb = 0.0
    for item in branch_loads:
        branch_buffer_mb += layout["yuv_frame_mb"] * item["buffer_factor"] * 2 * args.cameras
    bitstream_buffer_mb = max(4.0, base["h265_mb_s"] * 2) if "venc" in args.branches else 0.0
    metadata_pool_mb = 0.064 * args.buffer_depth * args.cameras
    vb_total_mb = vb_capture_mb + branch_buffer_mb + bitstream_buffer_mb + metadata_pool_mb
    peak_switch_mb = vb_total_mb * 2 if args.dynamic_resolution else vb_total_mb

    risks = detect_risks(
        profile=profile,
        resolution=resolution,
        fps=args.fps,
        cameras=args.cameras,
        align=args.align,
        buffer_depth=args.buffer_depth,
        branches=args.branches,
        layout=layout,
        total_ddr_mb_s=total_ddr_mb_s,
        noncoherent=args.noncoherent,
        dynamic_resolution=args.dynamic_resolution,
    )

    actions = build_actions(
        profile=profile,
        branches=args.branches,
        cameras=args.cameras,
        dynamic_resolution=args.dynamic_resolution,
        noncoherent=args.noncoherent,
    )

    trace_points = build_trace_points(args.fps, args.branches)

    hermes_metrics = [
        {"name": "sensor_irq_hz", "target": f">= {args.fps}", "desc": "Sensor/CSI 中断频率"},
        {"name": "dma_done_hz", "target": f">= {args.fps}", "desc": "DMA 帧完成频率"},
        {"name": "vb_pool_used_pct", "target": "< 75%", "desc": "VB Pool 使用率"},
        {"name": "dqbuf_latency_ms", "target": f"< {1000.0 / args.fps:.2f}", "desc": "DMA 完成到 APP 取帧时延"},
        {"name": "qbuf_return_ms", "target": f"< {(1000.0 / args.fps) / 2:.2f}", "desc": "APP 返还缓冲耗时"},
        {"name": "ddr_total_mb_s", "target": f"< {profile.ddr_budget_mb_s * 0.8:.1f}", "desc": "视频相关总 DDR 吞吐"},
        {"name": "venc_queue_depth", "target": "稳态不增长", "desc": "编码队列深度"},
        {"name": "cache_sync_fail_cnt", "target": "= 0", "desc": "Cache 同步异常计数"},
    ]

    return {
        "profile": asdict(profile),
        "resolution": asdict(resolution),
        "args": {
            "fps": args.fps,
            "cameras": args.cameras,
            "branches": args.branches,
            "buffer_depth": args.buffer_depth,
            "align": args.align,
            "yuv_format": args.yuv_format,
            "noncoherent": args.noncoherent,
            "dynamic_resolution": args.dynamic_resolution,
        },
        "base": {
            "pixels_mp": round(base["pixels_mp"], 2),
            "raw_bw_mb_s": round(base["raw_bw_mb_s"], 1),
            "yuv_bw_mb_s": round(base["yuv_bw_mb_s"], 1),
            "h265_mbps": round(base["h265_mbps"], 1),
            "isp_dma_write_mb_s": round(isp_dma_write_mb_s, 1),
            "total_ddr_mb_s": round(total_ddr_mb_s, 1),
            "ddr_budget_mb_s": round(profile.ddr_budget_mb_s, 1),
            "ddr_utilization_pct": round(total_ddr_mb_s / profile.ddr_budget_mb_s * 100, 1),
        },
        "layout": {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in layout.items()
        },
        "buffers": {
            "capture_pool_mb": round(vb_capture_mb, 2),
            "branch_pool_mb": round(branch_buffer_mb, 2),
            "bitstream_pool_mb": round(bitstream_buffer_mb, 2),
            "metadata_pool_mb": round(metadata_pool_mb, 2),
            "vb_total_mb": round(vb_total_mb, 2),
            "peak_switch_mb": round(peak_switch_mb, 2),
        },
        "branch_loads": [
            {
                "key": item["key"],
                "title": item["title"],
                "read_mb_s": round(item["read_mb_s"], 1),
                "write_mb_s": round(item["write_mb_s"], 1),
            }
            for item in branch_loads
        ],
        "flow": build_data_flow(profile, args.branches),
        "trace_points": trace_points,
        "risks": [asdict(item) for item in risks],
        "actions": [asdict(item) for item in actions],
        "hermes_metrics": hermes_metrics,
    }


def render_console(report: Dict[str, object]):
    profile = report["profile"]
    resolution = report["resolution"]
    args_cfg = report["args"]
    base = report["base"]
    layout = report["layout"]
    buffers = report["buffers"]
    branch_loads = report["branch_loads"]

    if _RICH:
        console.print(Panel.fit(
            f"[bold cyan]ISP 视频数据流架构分析[/bold cyan]\n"
            f"[dim]{profile['title']} | {resolution['name']} | {args_cfg['fps']}fps | {args_cfg['cameras']} 路[/dim]",
            border_style="bright_blue",
        ))
    else:
        print("\n" + "#" * 72)
        print("# ISP 视频数据流架构分析")
        print("#" * 72)

    if _RICH:
        info = Table(title="平台与输入配置", box=box.SIMPLE_HEAVY)
        info.add_column("项目", style="cyan")
        info.add_column("值", style="white")
        info.add_row("平台", profile["title"])
        info.add_row("运行模型", profile["runtime_model"])
        info.add_row("分辨率", f"{resolution['width']}x{resolution['height']} ({resolution['name']})")
        info.add_row("格式", f"RAW{resolution['bpp_raw']} -> {args_cfg['yuv_format'].upper()}")
        info.add_row("路数 / 帧率", f"{args_cfg['cameras']} / {args_cfg['fps']}fps")
        info.add_row("分支", ", ".join(args_cfg['branches']))
        info.add_row("变分辨率", "是" if args_cfg['dynamic_resolution'] else "否")
        console.print(info)
    else:
        print(f"平台: {profile['title']}")
        print(f"运行模型: {profile['runtime_model']}")
        print(f"输入: {resolution['width']}x{resolution['height']} {args_cfg['fps']}fps {args_cfg['cameras']}路")
        print(f"分支: {', '.join(args_cfg['branches'])}")

    flow_text = " -> ".join(report["flow"])
    _print(f"\n数据流:\n  {flow_text}")

    if _RICH:
        bw = Table(title="带宽预算", box=box.DOUBLE)
        bw.add_column("项", style="cyan")
        bw.add_column("值", justify="right")
        bw.add_row("RAW 入口带宽", f"{base['raw_bw_mb_s']:.1f} MB/s")
        bw.add_row("YUV 主路写 DDR", f"{base['isp_dma_write_mb_s']:.1f} MB/s")
        bw.add_row("VENC 参考码率", f"{base['h265_mbps']:.1f} Mbps")
        bw.add_row("总 DDR 估算", f"{base['total_ddr_mb_s']:.1f} MB/s")
        bw.add_row("平台 DDR 预算", f"{base['ddr_budget_mb_s']:.1f} MB/s")
        bw.add_row("预算占用", f"{base['ddr_utilization_pct']:.1f}%")
        console.print(bw)

        branch_table = Table(title="分支 DDR 负载", box=box.SIMPLE)
        branch_table.add_column("分支", style="cyan")
        branch_table.add_column("读 DDR(MB/s)", justify="right")
        branch_table.add_column("写 DDR(MB/s)", justify="right")
        for item in branch_loads:
            branch_table.add_row(item["title"], f"{item['read_mb_s']:.1f}", f"{item['write_mb_s']:.1f}")
        console.print(branch_table)

        mem = Table(title="缓冲与对齐", box=box.SIMPLE_HEAVY)
        mem.add_column("项", style="cyan")
        mem.add_column("值", justify="right")
        mem.add_row("RAW 行宽 / stride", f"{layout['raw_line_bytes_exact']:.0f} / {layout['raw_stride_bytes']:.0f} B")
        mem.add_row("Y 行宽 / stride", f"{layout['y_line_bytes_exact']:.0f} / {layout['y_stride_bytes']:.0f} B")
        mem.add_row("单帧 RAW", f"{layout['raw_frame_mb']:.2f} MB")
        mem.add_row("单帧 YUV", f"{layout['yuv_frame_mb']:.2f} MB")
        mem.add_row("主路捕获池", f"{buffers['capture_pool_mb']:.2f} MB")
        mem.add_row("分支缓冲池", f"{buffers['branch_pool_mb']:.2f} MB")
        mem.add_row("总 VB Pool", f"{buffers['vb_total_mb']:.2f} MB")
        mem.add_row("切分辨率峰值", f"{buffers['peak_switch_mb']:.2f} MB")
        console.print(mem)
    else:
        print("\n带宽预算:")
        print(f"  RAW 入口带宽: {base['raw_bw_mb_s']:.1f} MB/s")
        print(f"  YUV 主路写 DDR: {base['isp_dma_write_mb_s']:.1f} MB/s")
        print(f"  总 DDR 估算: {base['total_ddr_mb_s']:.1f} MB/s")
        print(f"  平台 DDR 预算: {base['ddr_budget_mb_s']:.1f} MB/s")

    if report["risks"]:
        if _RICH:
            risk_table = Table(title="风险识别", box=box.SIMPLE_HEAVY)
            risk_table.add_column("级别", style="red")
            risk_table.add_column("区域", style="cyan")
            risk_table.add_column("现象")
            risk_table.add_column("建议")
            for item in report["risks"]:
                risk_table.add_row(item["severity"], item["area"], item["symptom"], item["action"])
            console.print(risk_table)
        else:
            print("\n风险识别:")
            for item in report["risks"]:
                print(f"  [{item['severity']}] {item['area']}: {item['symptom']}")
                print(f"    建议: {item['action']}")

    if _RICH:
        act_table = Table(title="优化动作", box=box.SIMPLE)
        act_table.add_column("优先级", style="yellow")
        act_table.add_column("类别", style="cyan")
        act_table.add_column("动作")
        act_table.add_column("说明")
        for item in report["actions"]:
            act_table.add_row(item["priority"], item["category"], item["title"], item["detail"])
        console.print(act_table)
    else:
        print("\n优化动作:")
        for item in report["actions"]:
            print(f"  {item['priority']} {item['category']}: {item['title']}")
            print(f"    {item['detail']}")

    _print("\nTrace Points:")
    for item in report["trace_points"]:
        _print(f"  - {item['name']} | {item['owner']} | {item['metric']} | 预算 {item['budget']}")

    _print("\nHermes Metrics:")
    for item in report["hermes_metrics"]:
        _print(f"  - {item['name']}: {item['desc']} (目标 {item['target']})")


def build_mermaid(report: Dict[str, object]) -> str:
    branches = report["args"]["branches"]
    lines = [
        "flowchart LR",
        "    CIS[CIS / Sensor] --> CSI[MIPI CSI-2]",
        "    CSI --> ISP[ISP + 3A Stats]",
        "    ISP --> DMA[DMA Writeback]",
        "    DMA --> VB[VB Pool / CMA / MMZ]",
        "    VB --> SYS[SDK SYS Router]",
        "    SYS --> VPSS[VPSS / Scale / Crop]",
    ]
    if "venc" in branches:
        lines.append("    VPSS --> VENC[VENC / Stream]")
    if "preview" in branches:
        lines.append("    VPSS --> PREVIEW[Preview / Display]")
    if "app" in branches:
        lines.append("    VPSS --> APP[APP / DQBUF]")
    if "ai" in branches:
        lines.append("    VPSS --> AI[AI / NPU]")
    if report["profile"]["key"] == "amp":
        lines.append("    APPCTRL[Linux Cortex-A] --> MAIL[Mailbox / Shared Memory]")
        lines.append("    MAIL --> FW[Cortex-M / DSP 3A FW]")
        lines.append("    FW -. control .-> ISP")
    return "\n".join(lines)


def render_markdown(report: Dict[str, object]) -> str:
    profile = report["profile"]
    resolution = report["resolution"]
    args_cfg = report["args"]
    base = report["base"]
    layout = report["layout"]
    buffers = report["buffers"]

    lines = [
        "# ISP 视频数据流架构分析报告",
        "",
        "## 配置摘要",
        "",
        f"- 平台: {profile['title']}",
        f"- 运行模型: {profile['runtime_model']}",
        f"- 分辨率: {resolution['width']}x{resolution['height']} ({resolution['name']})",
        f"- 格式: RAW{resolution['bpp_raw']} -> {args_cfg['yuv_format'].upper()}",
        f"- 路数 / 帧率: {args_cfg['cameras']} / {args_cfg['fps']}fps",
        f"- 分支: {', '.join(args_cfg['branches'])}",
        f"- 变分辨率: {'是' if args_cfg['dynamic_resolution'] else '否'}",
        "",
        "## 数据流",
        "",
        "```mermaid",
        build_mermaid(report),
        "```",
        "",
        "## 带宽预算",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| RAW 入口带宽 | {base['raw_bw_mb_s']:.1f} MB/s |",
        f"| YUV 主路写 DDR | {base['isp_dma_write_mb_s']:.1f} MB/s |",
        f"| VENC 参考码率 | {base['h265_mbps']:.1f} Mbps |",
        f"| 总 DDR 估算 | {base['total_ddr_mb_s']:.1f} MB/s |",
        f"| 平台 DDR 预算 | {base['ddr_budget_mb_s']:.1f} MB/s |",
        f"| 预算占用 | {base['ddr_utilization_pct']:.1f}% |",
        "",
        "## 对齐与缓冲",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| RAW 行宽 / stride | {layout['raw_line_bytes_exact']:.0f} / {layout['raw_stride_bytes']:.0f} B |",
        f"| Y 行宽 / stride | {layout['y_line_bytes_exact']:.0f} / {layout['y_stride_bytes']:.0f} B |",
        f"| 单帧 RAW | {layout['raw_frame_mb']:.2f} MB |",
        f"| 单帧 YUV | {layout['yuv_frame_mb']:.2f} MB |",
        f"| 主路捕获池 | {buffers['capture_pool_mb']:.2f} MB |",
        f"| 分支缓冲池 | {buffers['branch_pool_mb']:.2f} MB |",
        f"| 总 VB Pool | {buffers['vb_total_mb']:.2f} MB |",
        f"| 切分辨率峰值 | {buffers['peak_switch_mb']:.2f} MB |",
        "",
        "## 分支 DDR 负载",
        "",
        "| 分支 | 读 DDR (MB/s) | 写 DDR (MB/s) |",
        "|---|---|---|",
    ]
    for item in report["branch_loads"]:
        lines.append(f"| {item['title']} | {item['read_mb_s']:.1f} | {item['write_mb_s']:.1f} |")

    lines.extend([
        "",
        "## 风险识别",
        "",
        "| 级别 | 区域 | 现象 | 根因 | 建议 |",
        "|---|---|---|---|---|",
    ])
    for item in report["risks"]:
        lines.append(
            f"| {item['severity']} | {item['area']} | {item['symptom']} | {item['reason']} | {item['action']} |"
        )

    lines.extend([
        "",
        "## 优化动作",
        "",
        "| 优先级 | 类别 | 动作 | 说明 |",
        "|---|---|---|---|",
    ])
    for item in report["actions"]:
        lines.append(f"| {item['priority']} | {item['category']} | {item['title']} | {item['detail']} |")

    lines.extend([
        "",
        "## Trace Points",
        "",
    ])
    for item in report["trace_points"]:
        lines.append(f"- {item['name']} | {item['owner']} | {item['metric']} | 预算 {item['budget']}")

    lines.extend([
        "",
        "## Hermes 指标",
        "",
    ])
    for item in report["hermes_metrics"]:
        lines.append(f"- {item['name']}: {item['desc']}，目标 {item['target']}")

    return "\n".join(lines) + "\n"


def save_file(path: str, content: str):
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="ISP 视频数据流架构分析与运行时优化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 video_pipeline_arch_optimizer.py --platform smp --resolution 4MP --fps 30 --cameras 2 --branches venc ai app
  python3 video_pipeline_arch_optimizer.py --platform amp --resolution 2592x1520 --fps 25 --branches venc preview --dynamic-resolution
  python3 video_pipeline_arch_optimizer.py --platform armv5 --resolution 1MP-720P --fps 15 --branches app --noncoherent
  python3 video_pipeline_arch_optimizer.py --export-md /tmp/video_pipeline_report.md --export-json /tmp/video_pipeline_report.json
""",
    )
    parser.add_argument("--platform", choices=sorted(PLATFORM_PROFILES.keys()), default="smp",
                        help="架构平台: smp / amp / armv5")
    parser.add_argument("--resolution", default="4MP",
                        help="分辨率名称或自定义宽高，例如 4MP 或 2592x1520")
    parser.add_argument("--fps", type=int, default=30, help="目标帧率")
    parser.add_argument("--cameras", type=int, default=2, help="摄像头路数")
    parser.add_argument("--raw-bpp", type=int, default=12, help="RAW bits per pixel")
    parser.add_argument("--yuv-format", choices=["nv12", "nv21", "yuyv", "uyvy"], default="nv12",
                        help="主路输出格式")
    parser.add_argument("--branches", nargs="+", choices=sorted(BRANCH_PROFILES.keys()),
                        default=["venc", "app"], help="使能的视频输出分支")
    parser.add_argument("--buffer-depth", type=int, default=4, help="主路缓冲深度")
    parser.add_argument("--align", type=int, default=64, help="DMA/YUV 对齐字节数")
    parser.add_argument("--dynamic-resolution", action="store_true",
                        help="按变分辨率场景估算峰值内存并增加相关风险提示")
    parser.add_argument("--noncoherent", action="store_true",
                        help="按无 I/O Coherency 平台建模，增加 Cache 同步风险提示")
    parser.add_argument("--list-resolutions", action="store_true",
                        help="列出内置分辨率并退出")
    parser.add_argument("--export-md", default="", help="导出 Markdown 报告")
    parser.add_argument("--export-json", default="", help="导出 JSON 报告")

    args = parser.parse_args()

    if args.list_resolutions:
        _print("内置分辨率:\n" + list_resolution_text())
        return

    report = build_report(args)
    render_console(report)

    if args.export_md:
        save_file(args.export_md, render_markdown(report))
        _print(f"\nMarkdown 已导出: {args.export_md}", style="green")

    if args.export_json:
        save_file(args.export_json, json.dumps(report, ensure_ascii=False, indent=2))
        _print(f"JSON 已导出: {args.export_json}", style="green")


if __name__ == "__main__":
    main()
