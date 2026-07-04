import json
import math
import os

# 格式换算系数 (Bytes per pixel)
FORMAT_BPP = {
    "RAW8": 1.0,
    "RAW10": 1.25,
    "RAW12": 1.5,
    "YUV420": 1.5,   # NV12/NV21 (ISP/PP输出，VENC输入最常用)
    "YUV422": 2.0,
    "RGB888": 3.0,
    "ARGB": 4.0
}

def calc_frame_size(width, height, fmt):
    bpp = FORMAT_BPP.get(fmt.upper(), 1.5)
    return width * height * bpp

def bytes_to_mb(b):
    return b / (1024 * 1024)

def calculate_soc_memory(config_file):
    if not os.path.exists(config_file):
        print(f"配置文件 {config_file} 不存在。")
        return

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    report = []
    total_memory_bytes = 0

    report.append("=" * 65)
    report.append("  Embedded SOC Video Linux Memory Analysis (DDR2/3 | PP Scaler)")
    report.append("=" * 65)

    # 1. System & RAM specs
    sys_cfg = config.get("system", {})
    ddr_cfg = config.get("ddr_config", {})

    os_mb = sys_cfg.get("os_baseline_mb", 24)
    linux_ver = sys_cfg.get("linux_version", "Linux 4x/5x")
    ddr_type = ddr_cfg.get("type", "DDR3")
    target_ddr_mb = ddr_cfg.get("capacity_mb", 64)

    report.append(f"[系统级参数]: {linux_ver} | 静态与动态内核内存约: {os_mb} MB")
    report.append(f"[硬件级配置]: 物理内存 {ddr_type} | 目标容量限制: {target_ddr_mb} MB")
    report.append("-" * 65)
    total_memory_bytes += os_mb * 1024 * 1024

    # 2. VI (Video Input) Raw memory
    vi_mb = 0
    report.append("[Video Input (VI) 前端传感器内存消耗]:")
    for sensor in config.get("sensors", []):
        w, h = sensor.get("width"), sensor.get("height")
        fmt, count = sensor.get("format", "RAW10"), sensor.get("count", 1)
        # 为小内存设备，通常采用Ping-Pong双缓冲
        buffers = sensor.get("vi_buffers", 2)

        mem_b = calc_frame_size(w, h, fmt) * buffers * count
        vi_mb += bytes_to_mb(mem_b)
        report.append(f"  -> {sensor.get('name')}: {w}x{h}({fmt}) x{count} | Ping-Pong Buf:{buffers} | 消耗: {bytes_to_mb(mem_b):.2f} MB")
    total_memory_bytes += vi_mb * 1024 * 1024
    report.append("-" * 65)

    # 3. Post Processing (PP) 多通道硬件缩放拆分
    pp_mb = 0
    pp_list = config.get("post_processing", [])
    if pp_list:
        report.append("[Post-Processing (PP) 硬件多通道缩放消耗]:")
        for pp in pp_list:
            report.append(f"  -> 处理来源节点: {pp.get('input_source')}")
            for ch in pp.get("channels", []):
                w, h = ch.get("width"), ch.get("height")
                fmt = ch.get("format", "YUV420")
                buffers = ch.get("buffers", 2)
                mem_b = calc_frame_size(w, h, fmt) * buffers
                pp_mb += bytes_to_mb(mem_b)
                report.append(f"     * [通道] {ch.get('name')}: {w}x{h}({fmt}) | Buf:{buffers} | {ch.get('usage', '')} | 消耗: {bytes_to_mb(mem_b):.2f} MB")
    total_memory_bytes += pp_mb * 1024 * 1024
    report.append("-" * 65)

    # 4. VENC 视频编码参考帧缓冲
    venc_mb = 0
    venc_list = config.get("venc", [])
    if venc_list:
        report.append("[Video Encode (VENC) 硬件编码参考帧及缓冲]:")
        for enc in venc_list:
            w, h = enc.get("width"), enc.get("height")
            fmt, count = enc.get("format", "YUV420"), enc.get("count", 1)
            buffers = enc.get("buffers", 3)
            mem_b = calc_frame_size(w, h, fmt) * buffers * count
            venc_mb += bytes_to_mb(mem_b)
            report.append(f"  -> {enc.get('name')}: {w}x{h} | H.264/265 Ref Buf:{buffers} | 消耗: {bytes_to_mb(mem_b):.2f} MB")
    total_memory_bytes += venc_mb * 1024 * 1024
    report.append("=" * 65)

    # 5. 汇总诊断建议
    total_mb = bytes_to_mb(total_memory_bytes)
    video_sum_mb = vi_mb + pp_mb + venc_mb

    report.append(f"多媒体多通道视频缓冲总计 (CMA池)    : {video_sum_mb:.2f} MB")
    report.append(f"系统运行总需求 (OS + Video CMA池)    : {total_mb:.2f} MB")

    ratio = (total_mb / target_ddr_mb) * 100
    report.append(f"\n[硬件匹配评估] 目标DDR方案: {target_ddr_mb} MB | 预期占用率: {ratio:.1f}%")

    if total_mb > target_ddr_mb * 0.90:  # 留存10%的紧急页面缓存和不可预期分配余量
        report.append(f"  [!! 告警 !!] 内存告急或者溢出！配置 {total_mb:.2f} 已经超过(或极度逼近)硬件容量 {target_ddr_mb}MB。")
        report.append("  ==> 拯救和优化措施推荐:")
        report.append("      1. 在 Linux config 内禁用无用驱动，开启 CONFIG_SLUB_TINY，裁减 RAM Disk/INITRAMFS 进一步压缩 OS (目标极简 12MB~18MB)")
        report.append("      2. 前端 ISP 采样从 RAW12 下调为 RAW10 或 RAW8。")
        report.append("      3. 牺牲抗抖动和抗撕裂，PP通道缓冲缩至 1 (Line-buffer模式) 如果硬件支持。")
        report.append("      4. 减少或者关闭第三个纯算法通道 (Third stream)，直接使用子通道进行算法分析。")
        report.append("      5. 换用 128MB 的 DDR 配置。")
    else:
        report.append(f"  [PASS] 恭喜，该定制配置可以在硬件 {target_ddr_mb} MB 内顺利跑通，留有 {(target_ddr_mb - total_mb):.2f} MB 富余系统页面缓存！")

    report.append("=" * 65)

    for line in report:
        print(line)

if __name__ == "__main__":
    calculate_soc_memory("soc_camera_config.json")
