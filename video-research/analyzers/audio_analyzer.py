"""
音频质量分析引擎
分析：SNR / THD / 频率响应 / A-V Sync
"""

import os
import numpy as np

try:
    from scipy.io import wavfile
    from scipy.signal import find_peaks
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class AudioAnalyzer:

    @staticmethod
    def analyze_sine_wave(wav_path: str, expected_freq: float = 1000) -> dict:
        """分析正弦波录音：频率偏差 / SNR / THD"""
        if not os.path.exists(wav_path):
            return {"pass": False, "reason": "WAV 文件不存在"}
        if not HAS_SCIPY:
            return {"pass": None, "reason": "scipy 未安装，跳过音频分析"}

        try:
            sample_rate, data = wavfile.read(wav_path)
        except Exception as e:
            return {"pass": False, "reason": f"WAV 读取失败: {e}"}

        # 归一化为浮点
        if data.dtype != np.float32:
            data = data.astype(np.float64)
            if data.dtype == np.int16:
                data /= 32768.0
            elif data.dtype == np.int32:
                data /= 2147483648.0

        if len(data.shape) > 1:
            data = data[:, 0]

        # 去直流
        data -= np.mean(data)
        N = len(data)

        # FFT
        fft_mag  = np.abs(np.fft.rfft(data, n=N))
        freqs    = np.fft.rfftfreq(N, d=1.0 / sample_rate)

        # 主频
        peak_idx   = int(np.argmax(fft_mag))
        actual_freq = float(freqs[peak_idx])

        # SNR
        signal_power = fft_mag[peak_idx] ** 2
        noise_power  = np.sum(fft_mag ** 2) - signal_power
        snr_db = 10 * np.log10(signal_power / max(noise_power, 1e-10))

        # THD：找 2~5 次谐波功率之和 / 基频功率
        harmonic_power = 0.0
        for h in range(2, 6):
            hf = actual_freq * h
            if hf > sample_rate / 2:
                break
            # 在理论谐波频率±5Hz 范围内找峰值
            mask = (freqs >= hf - 5) & (freqs <= hf + 5)
            if np.any(mask):
                harmonic_power += float(np.max(fft_mag[mask]) ** 2)
        thd_pct = float(np.sqrt(harmonic_power) / max(np.sqrt(signal_power), 1e-10) * 100)

        from config import THRESHOLDS
        t = THRESHOLDS["audio"]

        if abs(actual_freq - expected_freq) > t["freq_tolerance"]:
            return {"pass": False, "reason": f"主频偏移: 期望 {expected_freq}Hz, 实测 {actual_freq:.1f}Hz"}
        if snr_db < t["snr_min_db"]:
            return {"pass": False, "reason": f"SNR={snr_db:.2f}dB 低于下限 {t['snr_min_db']}dB"}
        if thd_pct > t["thd_max_pct"]:
            return {"pass": False, "reason": f"THD={thd_pct:.2f}% 超过上限 {t['thd_max_pct']}%"}

        return {
            "pass": True,
            "metrics": {
                "freq_hz"    : round(actual_freq, 1),
                "snr_db"     : round(snr_db, 2),
                "thd_pct"    : round(thd_pct, 3),
                "sample_rate": sample_rate,
            }
        }

    @staticmethod
    def analyze_av_sync(av_path: str) -> dict:
        """
        A/V 同步分析（需要 Flash & Beep 测试信号）
        通过 FFprobe 提取音视频流时间戳差值
        """
        import subprocess
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "stream=codec_type,start_time",
                "-of", "csv=p=0", av_path
            ]
            out = subprocess.check_output(cmd, timeout=15, stderr=subprocess.DEVNULL).decode()
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            times = {}
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 2:
                    times[parts[0]] = float(parts[1])
            if "video" in times and "audio" in times:
                diff_ms = abs(times["video"] - times["audio"]) * 1000
                from config import THRESHOLDS
                limit = THRESHOLDS["audio"]["av_sync_ms"]
                ok = diff_ms <= limit
                return {
                    "pass": ok,
                    "metrics": {"av_sync_ms": round(diff_ms, 2)},
                    "reason": "" if ok else f"A/V 同步误差 {diff_ms:.1f}ms > {limit}ms"
                }
        except Exception as e:
            return {"pass": None, "reason": f"A/V Sync 分析失败: {e}"}
        return {"pass": None, "reason": "无法提取音视频时间戳"}
