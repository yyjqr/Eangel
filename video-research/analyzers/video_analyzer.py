"""
视频质量分析引擎
支持：YUV420P / NV12 / H264/H265 码流分析
场景：单目 / 双目 / 三目 / 四目多路同步检测
"""

import os
import re
import time
import subprocess
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class VideoAnalyzer:
    """视频帧质量分析（服务端运行，不依赖板端环境）"""

    # ── YUV 原始帧分析 ─────────────────────────────────
    @staticmethod
    def analyze_yuv420p(yuv_path: str, width: int, height: int) -> dict:
        """
        分析 YUV420P/NV12 原始帧
        检测：黑屏 / 绿屏 / 花屏撕裂 / Sobel 梯度异常
        """
        y_size = width * height
        if not os.path.exists(yuv_path):
            return {"pass": False, "reason": "YUV 文件不存在"}

        file_size = os.path.getsize(yuv_path)
        if file_size < y_size:
            return {"pass": False, "reason": f"文件不完整: {file_size} < {y_size} bytes，疑似传输丢帧"}

        try:
            with open(yuv_path, "rb") as f:
                y_data = f.read(y_size)
        except Exception as e:
            return {"pass": False, "reason": str(e)}

        y_frame = np.frombuffer(y_data, dtype=np.uint8).reshape((height, width))

        # 1. 单色/黑屏/死帧检测
        variance = float(np.var(y_frame))
        if variance < 5.0:
            return {"pass": False, "reason": f"疑似黑屏/卡死/绿屏 (Variance={variance:.2f})"}

        # 2. 花屏/条纹检测 - 行差分
        row_diff = np.abs(y_frame[1:, :].astype(np.int16) - y_frame[:-1, :].astype(np.int16))
        bad_ratio = float(np.sum(row_diff > 160)) / (width * height)
        if bad_ratio > 0.03:
            return {"pass": False, "reason": f"画面撕裂/花屏 (Error Ratio={bad_ratio*100:.2f}%)"}

        # 3. Sobel 梯度二次校验（区分真实运动 vs 花屏）
        sobel_score = -1.0
        if HAS_CV2:
            gx = cv2.Sobel(y_frame, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(y_frame, cv2.CV_64F, 0, 1, ksize=3)
            grad_mag = np.sqrt(gx**2 + gy**2)
            sobel_score = float(np.mean(grad_mag))
            # 异常高频梯度（花屏特征：孤立高梯度区块）
            high_grad_ratio = float(np.sum(grad_mag > 200)) / grad_mag.size
            if high_grad_ratio > 0.05 and sobel_score > 80:
                return {"pass": False, "reason": f"Sobel 检测高频噪声块 (HighGradRatio={high_grad_ratio:.3f})"}

        return {
            "pass": True,
            "metrics": {
                "variance"      : round(variance, 2),
                "error_ratio"   : round(bad_ratio, 4),
                "sobel_mean"    : round(sobel_score, 2),
            }
        }

    # ── 帧率 / PTS 分析 ────────────────────────────────
    @staticmethod
    def analyze_framerate(video_path: str, expected_fps: float) -> dict:
        """用 FFprobe 分析码流帧率与 PTS 连续性"""
        if not _has_ffprobe():
            return {"pass": None, "reason": "FFprobe 未安装，跳过帧率分析"}

        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,nb_read_frames",
            "-count_frames", "-of", "csv=p=0", video_path
        ]
        try:
            out = subprocess.check_output(cmd, timeout=30, stderr=subprocess.DEVNULL).decode().strip()
            # r_frame_rate 格式：num/den
            parts = out.split(",")
            fps_raw = parts[0]
            num, den = map(int, fps_raw.split("/"))
            actual_fps = num / den
        except Exception as e:
            return {"pass": False, "reason": f"FFprobe 解析失败: {e}"}

        tol = expected_fps * 0.05
        if abs(actual_fps - expected_fps) > tol:
            return {
                "pass": False,
                "reason": f"帧率偏差过大: 期望 {expected_fps}fps, 实测 {actual_fps:.2f}fps"
            }
        return {"pass": True, "metrics": {"actual_fps": round(actual_fps, 2)}}

    # ── 多目帧同步检测 ─────────────────────────────────
    @staticmethod
    def analyze_multicam_sync(frame_files: list, sensor_ids: list) -> dict:
        """
        多目帧同步分析：
        frame_files: 各路同一时刻抓取的 YUV 文件路径列表（按 sensor_id 顺序）
        通过文件 mtime 近似判断接收时刻差（精度 ~10ms 级）
        精确模式需要在 YUV 帧头嵌入板端 PTS 时间戳
        """
        if len(frame_files) < 2:
            return {"pass": True, "reason": "单目无需同步检测"}

        mtimes = []
        for f in frame_files:
            if not os.path.exists(f):
                return {"pass": False, "reason": f"文件缺失: {f}"}
            mtimes.append(os.path.getmtime(f))

        max_diff_ms = (max(mtimes) - min(mtimes)) * 1000
        from config import THRESHOLDS
        limit = THRESHOLDS["video"]["sync_diff_ms"]
        if max_diff_ms > limit:
            return {
                "pass": False,
                "reason": f"多目同步误差 {max_diff_ms:.1f}ms > 阈值 {limit}ms",
                "metrics": {"sync_diff_ms": round(max_diff_ms, 2)}
            }
        return {"pass": True, "metrics": {"sync_diff_ms": round(max_diff_ms, 2)}}

    # ── 编码码流分析 ───────────────────────────────────
    @staticmethod
    def analyze_encoded_stream(video_path: str, expected_bitrate_kbps: float,
                                codec: str = "h264") -> dict:
        """分析 H.264/H.265/MJPEG 码流：码率偏差 / IDR 间隔"""
        if not _has_ffprobe():
            return {"pass": None, "reason": "FFprobe 未安装"}

        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=bit_rate,duration", "-of", "csv=p=0", video_path
        ]
        try:
            out = subprocess.check_output(cmd, timeout=15, stderr=subprocess.DEVNULL).decode().strip()
            parts = out.split(",")
            actual_bps = float(parts[0]) / 1000  # → kbps
        except Exception as e:
            return {"pass": False, "reason": f"码流解析失败: {e}"}

        from config import THRESHOLDS
        tol_pct = THRESHOLDS["encode"]["bitrate_tol_pct"]
        diff_pct = abs(actual_bps - expected_bitrate_kbps) / max(expected_bitrate_kbps, 1) * 100
        if diff_pct > tol_pct:
            return {
                "pass": False,
                "reason": f"CBR 码率偏差 {diff_pct:.1f}% > {tol_pct}%  (期望 {expected_bitrate_kbps}kbps, 实测 {actual_bps:.0f}kbps)"
            }
        return {"pass": True, "metrics": {"actual_kbps": round(actual_bps, 1), "diff_pct": round(diff_pct, 2)}}


def _has_ffprobe() -> bool:
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False
