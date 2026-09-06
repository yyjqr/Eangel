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
