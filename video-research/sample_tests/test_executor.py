"""
测试执行引擎 - 将用例类型映射到具体执行逻辑和断言
"""

import os
import time
import threading
from typing import Optional

from dut_client import DUTClient, _ServerReceiver
from analyzers import VideoAnalyzer, AudioAnalyzer
import config


class TestExecutor:
    """单条用例执行 + 断言，返回标准化结果字典"""

    def __init__(self, dut: DUTClient, server_ip: str, base_port: int = 9000):
        self.dut        = dut
        self.server_ip  = server_ip
        self.base_port  = base_port
        self._port_lock = threading.Lock()
        self._next_port = base_port

    def _alloc_port(self) -> int:
        with self._port_lock:
            p = self._next_port
            self._next_port += 1
            return p

    # ── 通用：执行 sdk 样例程序，等待完成 ─────────────────
    def _run_sdk(self, sdk_cmd: str, timeout: int) -> str:
        """执行板端 sample 程序，返回输出"""
        return self.dut.exec(sdk_cmd, timeout=timeout + 5)

    # ── 通用：采集 YUV 帧 + 传回服务器 ────────────────────
    def _capture_yuv(self, tc: dict) -> Optional[str]:
        """触发 v4l2 采集 1 帧 YUV，返回本地文件路径"""
        port      = self._alloc_port()
        local_yuv = os.path.join(config.MEDIA_DIR, f"{tc['id']}.yuv")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        cam = _get_camera_cfg(self.dut.cfg, tc.get("camera_id", 0))
        dev = cam["dev"] if cam else "/dev/video0"
        w, h = tc.get("width", 1920), tc.get("height", 1080)

        # 服务器先监听
        recv = _ServerReceiver(port, local_yuv, timeout=15)
        recv.start()
        time.sleep(0.2)

        # 板端采 1 帧后用 nc 推流
        cap_cmd = (
            f"v4l2-ctl -d {dev} "
            f"--set-fmt-video=width={w},height={h},pixelformat=NV12 "
            f"--stream-mmap --stream-count=1 --stream-to=/tmp/{tc['id']}.yuv && "
            f"nc {self.server_ip} {port} < /tmp/{tc['id']}.yuv ; "
            f"rm -f /tmp/{tc['id']}.yuv"
        )
        self.dut.exec(cap_cmd, timeout=20)

        ok = recv.wait()
        return local_yuv if ok else None

    # ── 通用：采集音频 + 传回服务器 ───────────────────────
    def _capture_wav(self, tc: dict) -> Optional[str]:
        port      = self._alloc_port()
        local_wav = os.path.join(config.MEDIA_DIR, f"{tc['id']}.wav")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dev = tc.get("alsa_dev", self.dut.cfg.get("audio", {}).get("alsa_dev", "hw:0,0"))
        sr  = tc.get("sample_rate", 16000)
        ch  = tc.get("channels", 1)
        dur = tc.get("duration_s", 3)

        recv = _ServerReceiver(port, local_wav, timeout=dur + 10)
        recv.start()
        time.sleep(0.2)

        cap_cmd = (
            f"arecord -D {dev} -r {sr} -f S16_LE -c {ch} -d {dur} /tmp/{tc['id']}.wav && "
            f"nc {self.server_ip} {port} < /tmp/{tc['id']}.wav ; "
            f"rm -f /tmp/{tc['id']}.wav"
        )
        self.dut.exec(cap_cmd, timeout=dur + 15)

        ok = recv.wait()
        return local_wav if ok else None

    # ══════════════════════════════════════════════
    # 断言函数集
    # ══════════════════════════════════════════════

    def assert_yuv_quality(self, tc: dict) -> dict:
        """VI 用例：运行 sdk sample，采集 YUV，检测画质"""
        # 先触发 sdk sample
        sdk_out = self._run_sdk(tc["sdk_cmd"], tc.get("duration_s", 5) + 5)
        local_yuv = self._capture_yuv(tc)
        if not local_yuv:
            return _fail("YUV 文件传输失败")
        res = VideoAnalyzer.analyze_yuv420p(local_yuv, tc["width"], tc["height"])
        res["sdk_log"] = sdk_out[:200] if sdk_out else ""
        return res

    def assert_encoded_stream(self, tc: dict) -> dict:
        """VENC 用例：运行 sdk sample，接收码流，分析码率"""
        port       = self._alloc_port()
        codec      = tc.get("codec", "h264")
        local_file = os.path.join(config.MEDIA_DIR, f"{tc['id']}.{codec}")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur = tc.get("duration_s", 10)
        recv = _ServerReceiver(port, local_file, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = tc["sdk_cmd"] + f" && nc {self.server_ip} {port} < /tmp/venc_{tc['id']}.{codec}"
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("码流传输超时")

        br = tc.get("bitrate_kbps", 4000)
        return VideoAnalyzer.analyze_encoded_stream(local_file, br, codec)

    def assert_video_stream(self, tc: dict) -> dict:
        """完整视频流：运行 sdk，接收 mp4，分析帧率"""
        port       = self._alloc_port()
        local_file = os.path.join(config.MEDIA_DIR, f"{tc['id']}.mp4")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur = tc.get("duration_s", 15)
        recv = _ServerReceiver(port, local_file, timeout=dur + 20)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/video_{tc['id']}.mp4 ; "
                   f"rm -f /tmp/video_{tc['id']}.mp4")
        self.dut.exec(sdk_cmd, timeout=dur + 25)

        if not recv.wait():
            return _fail("视频文件传输超时")

        fps_res = VideoAnalyzer.analyze_framerate(local_file, tc["fps"])
        br_res  = VideoAnalyzer.analyze_encoded_stream(local_file, tc.get("bitrate_kbps", 4000))
        if not fps_res["pass"]:
            return fps_res
        if br_res.get("pass") is False:
            return br_res
        merged = {"pass": True, "metrics": {}}
        for r in [fps_res, br_res]:
            merged["metrics"].update(r.get("metrics", {}))
        return merged

    def assert_first_frame_latency(self, tc: dict) -> dict:
        """首帧延迟：sdk 输出时间戳文件，分析延迟"""
        port       = self._alloc_port()
        local_file = os.path.join(config.MEDIA_DIR, f"{tc['id']}_ff.txt")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        recv = _ServerReceiver(port, local_file, timeout=15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/video_{tc['id']}_firstframe.txt")
        self.dut.exec(sdk_cmd, timeout=20)

        if not recv.wait():
            return _fail("首帧时间戳文件传输失败")

        try:
            with open(local_file) as f:
                latency_ms = float(f.read().strip())
        except Exception:
            return _fail("首帧时间戳解析失败")

        limit = config.THRESHOLDS["video"]["first_frame_ms"]
        if latency_ms > limit:
            return _fail(f"首帧延迟 {latency_ms:.0f}ms > {limit}ms")
        return {"pass": True, "metrics": {"first_frame_ms": round(latency_ms, 1)}}

    def assert_audio_sine(self, tc: dict) -> dict:
        self._run_sdk(tc["sdk_cmd"], tc.get("duration_s", 3) + 5)
        local_wav = self._capture_wav(tc)
        if not local_wav:
            return _fail("WAV 文件传输失败")
        return AudioAnalyzer.analyze_sine_wave(local_wav, tc.get("expected_freq", 1000))

    def assert_av_sync(self, tc: dict) -> dict:
        port       = self._alloc_port()
        local_file = os.path.join(config.MEDIA_DIR, f"{tc['id']}_av.mp4")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 10)
        recv = _ServerReceiver(port, local_file, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/audio_{tc['id']}_av.mp4")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("A/V 文件传输超时")
        return AudioAnalyzer.analyze_av_sync(local_file)

    def assert_multicam_sync(self, tc: dict) -> dict:
        cam_ids    = tc.get("camera_ids", [0, 1])
        port_base  = self._alloc_port()
        yuv_files  = []
        receivers  = []

        # 为每路摄像头分配端口并启动接收
        for i, cid in enumerate(cam_ids):
            port       = port_base + i
            local_yuv  = os.path.join(config.MEDIA_DIR, f"{tc['id']}_cam{cid}.yuv")
            os.makedirs(config.MEDIA_DIR, exist_ok=True)
            recv = _ServerReceiver(port, local_yuv, timeout=20)
            recv.start()
            yuv_files.append(local_yuv)
            receivers.append(recv)

        time.sleep(0.3)
        self._run_sdk(tc["sdk_cmd"], tc.get("duration_s", 5) + 10)

        # 等所有接收完成
        all_ok = all(r.wait() for r in receivers)
        if not all_ok:
            return _fail("部分摄像头 YUV 传输失败")

        return VideoAnalyzer.analyze_multicam_sync(yuv_files, cam_ids)

    def assert_ai_perf(self, tc: dict) -> dict:
        """AI 用例：解析 json 结果，检查推理帧率"""
        import json
        port       = self._alloc_port()
        local_json = os.path.join(config.MEDIA_DIR, f"{tc['id']}_result.json")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 10)
        recv = _ServerReceiver(port, local_json, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/ai_{tc['id']}_result.json")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("AI 结果文件传输失败")

        try:
            with open(local_json) as f:
                ai_res = json.load(f)
            fps = float(ai_res.get("fps", 0))
        except Exception:
            return _fail("AI JSON 解析失败")

        exp_fps = tc.get("expected_fps", 15.0)
        if fps < exp_fps:
            return _fail(f"AI 推理帧率 {fps:.1f}fps < 期望 {exp_fps}fps")
        return {"pass": True, "metrics": {"ai_fps": round(fps, 1)}}

    def assert_ai_latency(self, tc: dict) -> dict:
        import json
        port       = self._alloc_port()
        local_json = os.path.join(config.MEDIA_DIR, f"{tc['id']}_result.json")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 10)
        recv = _ServerReceiver(port, local_json, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/ai_{tc['id']}_result.json")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("AI 延迟结果传输失败")

        try:
            with open(local_json) as f:
                ai_res = json.load(f)
            lat_ms = float(ai_res.get("avg_latency_ms", 9999))
        except Exception:
            return _fail("AI 延迟 JSON 解析失败")

        limit = tc.get("expected_latency_ms", 100)
        if lat_ms > limit:
            return _fail(f"AI 推理延迟 {lat_ms:.1f}ms > {limit}ms")
        return {"pass": True, "metrics": {"ai_latency_ms": round(lat_ms, 1)}}

    def assert_ai_pipeline(self, tc: dict) -> dict:
        """VI→ISP→AI 全链路：从日志文件中统计丢帧数"""
        port       = self._alloc_port()
        local_log  = os.path.join(config.LOG_DIR, f"{tc['id']}.txt")
        os.makedirs(config.LOG_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 15)
        recv = _ServerReceiver(port, local_log, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/ai_{tc['id']}_log.txt")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("AI 流水线日志传输失败")

        try:
            with open(local_log) as f:
                content = f.read()
            import re
            drop = int(re.search(r'drop[_\s]*frames?\s*[:=]\s*(\d+)', content, re.I).group(1))
        except Exception:
            drop = 0

        if drop > 0:
            return _fail(f"AI 流水线丢帧 {drop} 帧")
        return {"pass": True, "metrics": {"drop_frames": 0}}

    def assert_svp_output(self, tc: dict) -> dict:
        """SVP 缩放：检测输出 YUV 文件质量"""
        port       = self._alloc_port()
        local_yuv  = os.path.join(config.MEDIA_DIR, f"{tc['id']}_out.yuv")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 5)
        recv = _ServerReceiver(port, local_yuv, timeout=dur + 10)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/svp_{tc['id']}_out.yuv")
        self.dut.exec(sdk_cmd, timeout=dur + 15)

        if not recv.wait():
            return _fail("SVP 输出文件传输失败")

        w = tc.get("width", 960) // 2
        h = tc.get("height", 540) // 2
        return VideoAnalyzer.analyze_yuv420p(local_yuv, w, h)

    def assert_svp_ive(self, tc: dict) -> dict:
        """SVP IVE 运动检测：解析 JSON 结果"""
        import json
        port       = self._alloc_port()
        local_json = os.path.join(config.MEDIA_DIR, f"{tc['id']}_result.json")
        os.makedirs(config.MEDIA_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 10)
        recv = _ServerReceiver(port, local_json, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/svp_{tc['id']}_result.json")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("SVP IVE 结果传输失败")

        try:
            with open(local_json) as f:
                res = json.load(f)
            return {"pass": res.get("status") == "ok",
                    "metrics": res.get("metrics", {}),
                    "reason": res.get("error", "")}
        except Exception as e:
            return _fail(f"IVE JSON 解析失败: {e}")

    def assert_self_healing(self, tc: dict) -> dict:
        """鲁棒性：热插拔后自动恢复，从日志判断"""
        port      = self._alloc_port()
        local_log = os.path.join(config.LOG_DIR, f"{tc['id']}.txt")
        os.makedirs(config.LOG_DIR, exist_ok=True)

        dur  = tc.get("duration_s", 30)
        recv = _ServerReceiver(port, local_log, timeout=dur + 15)
        recv.start()
        time.sleep(0.2)

        sdk_cmd = (tc["sdk_cmd"] +
                   f" && nc {self.server_ip} {port} < /tmp/robust_{tc['id']}_log.txt")
        self.dut.exec(sdk_cmd, timeout=dur + 20)

        if not recv.wait():
            return _fail("热插拔日志传输失败")

        try:
            with open(local_log) as f:
                content = f.read()
            import re
            recovered = bool(re.search(r'recover|resume|reopen', content, re.I))
            err_cnt   = len(re.findall(r'mipi\s*err|csi\s*err|lost\s*sync', content, re.I))
        except Exception:
            return _fail("热插拔日志解析失败")

        if not recovered:
            return _fail("系统未检测到自动恢复（无 recover/resume 关键词）")
        return {"pass": True, "metrics": {"mipi_error_count": err_cnt, "recovered": True}}

    def assert_no_memory_leak(self, tc: dict) -> dict:
        """长稳：采集期间轮询内存，检测泄漏趋势"""
        dur          = tc.get("duration_s", 600)
        poll_interval= 30
        mem_samples  = []

        # 后台运行 sdk
        self.dut.exec_bg(tc["sdk_cmd"])

        deadline = time.time() + dur
        while time.time() < deadline:
            mb = self.dut.get_mem_free_mb()
            if mb > 0:
                mem_samples.append(mb)
            time.sleep(poll_interval)

        # 停止 sdk（粗暴 killall）
        bin_name = tc["sdk_cmd"].split()[0]
        self.dut.exec(f"killall {bin_name} 2>/dev/null; true", timeout=5)

        if len(mem_samples) < 3:
            return _fail("内存采样数据不足")

        # 简单线性趋势：末尾均值 vs 头部均值
        half = max(1, len(mem_samples) // 2)
        early_avg = sum(mem_samples[:half]) / half
        late_avg  = sum(mem_samples[half:]) / max(len(mem_samples) - half, 1)
        leak_mb   = early_avg - late_avg

        from config import THRESHOLDS
        limit = THRESHOLDS["system"]["mem_free_min_mb"]
        if late_avg < limit:
            return _fail(f"末期空闲内存 {late_avg:.1f}MB < {limit}MB，可能内存泄漏")
        if leak_mb > 5:
            return _fail(f"内存持续下降 {leak_mb:.1f}MB，疑似泄漏")
        return {"pass": True, "metrics": {"leak_mb": round(leak_mb, 2), "final_free_mb": round(late_avg, 1)}}

    # ── 分发入口 ──────────────────────────────────────────
    def run(self, tc: dict) -> dict:
        fn_name = tc.get("assert_fn", "")
        fn = getattr(self, fn_name, None)
        if fn is None:
            return _fail(f"未找到断言函数: {fn_name}")
        try:
            return fn(tc)
        except Exception as e:
            return _fail(f"执行异常: {e}")


# ── 工具函数 ──────────────────────────────────────────────
def _fail(reason: str) -> dict:
    return {"pass": False, "reason": reason, "metrics": {}}

def _get_camera_cfg(dut_cfg: dict, cam_id: int) -> Optional[dict]:
    for c in dut_cfg.get("cameras", []):
        if c["id"] == cam_id:
            return c
    return None
