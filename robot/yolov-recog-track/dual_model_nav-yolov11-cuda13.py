import cv2
import numpy as np
import time
import serial
import sys
import os
import threading
import datetime
import json
from collections import deque

# Orin Nano 上 TensorRT 以系统包形式安装（包名 tensorrt，非 tensorrt-cu13），
# 禁用 Ultralytics 的自动依赖安装检查，避免无效的 AutoUpdate 警告。
os.environ.setdefault('YOLO_AUTOINSTALL', 'False')

from ultralytics import YOLO

# pip 安装的 OpenCV Qt 版本缺少内置字体目录，指向系统字体避免 QFontDatabase 警告和窗口显示异常。
for _font_dir in ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/truetype', '/usr/share/fonts'):
    if os.path.isdir(_font_dir):
        os.environ.setdefault('QT_QPA_FONTDIR', _font_dir)
        break

# GStreamer support check
GI_AVAILABLE = False
RTSP_SERVER_AVAILABLE = False
try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtspServer', '1.0')
    from gi.repository import Gst, GstRtspServer, GLib
    GI_AVAILABLE = True
    RTSP_SERVER_AVAILABLE = True
except ImportError:
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        GI_AVAILABLE = True
    except ImportError:
        pass

class GStreamerRtspServer(threading.Thread):
    def __init__(self, port="8554", mount_point="/test"):
        super().__init__()
        self.port = port
        self.mount_point = mount_point
        self.context = None
        self.loop = None
        self.server = None
        self.daemon = True 

    def run(self):
        if not RTSP_SERVER_AVAILABLE:
            print("GstRtspServer not available, skipping RTSP server start.")
            return

        if not Gst.is_initialized():
            Gst.init(None)

        self.context = GLib.MainContext.new()
        self.loop = GLib.MainLoop(self.context)

        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(self.port)
        
        mounts = self.server.get_mount_points()
        factory = GstRtspServer.RTSPMediaFactory()
        
        # Internal bridge pipeline: Receive H264 from UDP and pay it to RTSP
        pipeline_str = (
            "( udpsrc port=5400 auto-multicast=false ! "
            "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! "
            "rtph264depay ! rtph264pay name=pay0 pt=96 )"
        )
        
        factory.set_launch(pipeline_str)
        factory.set_shared(True)
        
        mounts.add_factory(self.mount_point, factory)
        
        print(f"[RTSP Server] Server started at rtsp://0.0.0.0:{self.port}{self.mount_point}")
        
        self.server.attach(self.context)
        self.loop.run()
    
    def stop(self):
        if self.loop.is_running():
            self.loop.quit()

class GStreamerCapture:
    def __init__(self, pipeline_str):
        if not GI_AVAILABLE:
            raise RuntimeError("GStreamer python bindings (gi) not available")
        
        if not Gst.is_initialized():
            Gst.init(None)

        print(f"[GStreamerCapture] Launching Pipeline: {pipeline_str}")
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            raise RuntimeError(f"Gst.parse_launch failed: {e}")

        self.appsink = self.pipeline.get_by_name('mysink')
        if not self.appsink:
            raise RuntimeError("Could not find appsink with name 'mysink' in pipeline")

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)
        self.last_error = None

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Failed to set pipeline to PLAYING (FAILURE). Last error: {self.last_error}")

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.last_error = f"Error: {err}, Debug: {debug}"
            print(f"[GStreamerCapture] ERROR: {self.last_error}")
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            print(f"[GStreamerCapture] WARNING: {err}, Debug: {debug}")

    def isOpened(self):
        if self.last_error: return False
        return True # Simplified

    def read(self):
        if self.last_error:
            print(f"[GStreamerCapture] Cannot read, pipeline in error state: {self.last_error}")
            return False, None
            
        sample = self.appsink.emit('pull-sample')
        if not sample:
            return False, None

        buf = sample.get_buffer()
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        h = structure.get_value('height')
        w = structure.get_value('width')
        
        buffer = buf.extract_dup(0, buf.get_size())
        
        try:
            frame = np.ndarray((h, w, 3), buffer=buffer, dtype=np.uint8)
            return True, frame.copy()
        except Exception as e:
            print(f"Frame decode error: {e}")
            return False, None

    def release(self):
        self.pipeline.set_state(Gst.State.NULL)
    
    def set(self, prop, val):
        pass 
    
    def get(self, prop):
        return 0


class AsyncCaptureThread:
    """
    独立线程持续从摄像头读帧，主线程通过 get_latest() 取最新帧。

    解决 USB 摄像头在高帧率下因内核缓冲积压导致的画面卡住问题：
    - USB UVC 驱动默认缓冲 4 帧，帧率过快时旧帧无法及时丢弃
    - 本线程持续消耗缓冲，主线程取帧始终是最新的
    """
    def __init__(self, cap):
        self._cap = cap
        self._frame = None
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    with self._lock:
                        self._frame = frame
                else:
                    time.sleep(0.005)
            except Exception:
                time.sleep(0.01)

    def get_latest(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    # 兼容 cap.read() 接口
    def read(self):
        frame = self.get_latest()
        return (True, frame) if frame is not None else (False, None)

    def isOpened(self):
        return self._cap.isOpened()

    def set(self, prop, val):
        return self._cap.set(prop, val)

    def release(self):
        self._running = False
        self._thread.join(timeout=2.0)
        self._cap.release()


INFER_SIZE = 640  # 推理输入尺寸，需在函数默认参数求值前定义

def preprocess_for_inference(frame, mode=None, infer_size=INFER_SIZE):
    """
    将任意分辨率帧裁剪/缩放为 infer_size×infer_size，供 YOLOv8 推理。
    返回 (infer_frame, crop_rect=(x0, y0, crop_w, crop_h))。

    模式说明：
      letterbox  : 标准等比缩放+黑边，信息无损失，但边缘有填充
      center_crop: 中心正方形裁剪后缩放，消除边缘干扰，适合正面/中央目标
      roi_crop   : 按 ROI_X/Y_MARGIN 裁剪中心感兴趣区，目标在远处时占比更大
    """
    if mode is None:
        mode = PREPROCESS_MODE
    h, w = frame.shape[:2]

    if mode == 'center_crop':
        side = min(h, w)
        x0 = (w - side) // 2
        y0 = (h - side) // 2
        cropped = frame[y0:y0 + side, x0:x0 + side]
        out = cv2.resize(cropped, (infer_size, infer_size), interpolation=cv2.INTER_LINEAR)
        return out, (x0, y0, side, side)

    elif mode == 'roi_crop':
        x0 = int(w * ROI_X_MARGIN)
        y0 = int(h * ROI_Y_MARGIN)
        x1 = int(w * (1.0 - ROI_X_MARGIN))
        y1 = int(h * (1.0 - ROI_Y_MARGIN))
        cropped = frame[y0:y1, x0:x1]
        roi_w, roi_h = x1 - x0, y1 - y0
        out = cv2.resize(cropped, (infer_size, infer_size), interpolation=cv2.INTER_LINEAR)
        return out, (x0, y0, roi_w, roi_h)

    else:  # letterbox
        scale = infer_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pad_l = (infer_size - new_w) // 2
        pad_t = (infer_size - new_h) // 2
        out = np.full((infer_size, infer_size, 3), 114, dtype=np.uint8)
        out[pad_t:pad_t + new_h, pad_l:pad_l + new_w] = resized
        return out, (pad_l, pad_t, new_w, new_h)


# ================= 配置区域 =================
# 串口设置 (请确认端口号，通常是 /dev/ttyUSB0 或 /dev/ttyACM0)
SERIAL_PORT = '/dev/ttyUSB0'  
BAUD_RATE = 115200

# 模型路径 (优先使用 TensorRT Engine 以获得极致速度)
MODEL_DET_PATH = 'yolo11n.engine'      # 检测模型：负责避障 (人, 障碍物)
MODEL_SEG_PATH = 'yolo11n-seg.engine'  # 分割模型：负责寻路 (路面)

# 阈值设置
CONF_THRESHOLD = 0.5
AREA_THRESHOLD = 5000     # 最小路面面积，太小说明前面没路了
CENTER_TOLERANCE = 80     # 中心容差，在这个范围内算直行 (像素)
STOP_DISTANCE_RATIO = 0.3 # 障碍物占画面高度比例超过此值不仅避让，而是停车

# 避障类别ID (COCO数据集: 0=人, 1=自行车, 2=车, ... 可以根据需求添加)
OBSTACLE_CLASSES = [0, 1, 2, 3, 5, 7] 

# 寻路类别ID (假设分割模型能分出路面。如果是通用模型，可以设为 None，即便取最大连通域)
# 如果你是训练过的路面模型，填入路面的 class id
PATH_CLASS_ID = 0 

# USB 摄像头采集分辨率 (720p 以获取更宽视野)
CAPTURE_WIDTH  = 1280
CAPTURE_HEIGHT = 720
CAPTURE_FPS    = 15

# 推理输入预处理模式
#   'letterbox'  - 等比缩放+黑边填充到 INFER_SIZE×INFER_SIZE，标准 YOLO 预处理
#   'center_crop'- 从画面中心裁剪最大正方形后缩放，聚焦画面中央 ROI（推荐）
#   'roi_crop'   - 按 ROI_X/Y_MARGIN 裁剪中心感兴趣区后缩放，远距目标占比更大
#
# TensorRT 是否能做 resize?
#   TRT engine 本身是推理引擎，不能单独执行 resize。YOLOv8 TRT engine 在 Python 层
#   由 Ultralytics 完成 letterbox (CPU/CUDA)，约 0.5~1ms 可忽略。
#   若需纯 GPU resize 可用 cv2.cuda.resize()（需带 CUDA 编译的 OpenCV）。
PREPROCESS_MODE = 'center_crop'
# INFER_SIZE 已在 preprocess_for_inference 函数定义前声明

# ROI 裁剪边距比例（仅 roi_crop 模式）
ROI_X_MARGIN = 0.15   # 水平各裁 15%
ROI_Y_MARGIN = 0.10   # 垂直各裁 10%

# 双模型独立帧率控制
#   检测模型：远距初判，USB 低帧采样即可，1fps 足够且避免 USB 缓冲积压
#   分割模型：路径跟踪，需要更连续的感知
DET_TARGET_FPS = 1.0
SEG_TARGET_FPS = 5.0

# 输入源配置
CONFIG_PATH = 'config.json'
RTSP_INPUT_URL = ''              # 例如: rtsp://127.0.0.1:8554/test
PREFER_RTSP_INPUT = False        # True 时优先拉 RTSP，否则优先 USB
USB_DEVICE = '/dev/video0'
USB_CAMERA_INDEX = 0

# 融合导航参数
AVOID_DANGER_THRESHOLD = 0.55
EMERGENCY_DANGER_THRESHOLD = 0.80
PATH_LOST_TIMEOUT = 1.2          # 秒，超过该时间未找到路径则停
PATH_EMA_ALPHA = 0.35            # 路径中心平滑
BOTTOM_PATH_RATIO = 0.55         # 仅关注下半区域路径

# ── 日志 & 空白画面倒车参数 ──────────────────────────────────────
LOG_ENABLED      = True    # 设为 False 可关闭日志文件
BLANK_VAR_THRESH = 120.0   # 灰度帧方差低于此值判为空白/模糊帧
BACKUP_BLANK_N   = 10      # 连续空白帧 ≥ 此数 → 触发倒车(B)
BACKUP_NOPATH_N  = 60      # 连续无路径帧 ≥ 此数 → 触发倒车(B)（约2s@30fps）
BACKUP_DURATION  = 2.0     # 倒车持续时间（秒）

class RobotNavigator:
    def __init__(self):
        # 0. 状态初始化
        self.last_sent_cmd = None
        self.last_cmd_send_time = 0.0
        self.last_process_time = 0.0
        self.consecutive_count = 0
        self.current_stable_cmd = None
        self.cmd_window = deque(maxlen=5)
        self.path_center_ema = None
        self.last_path_time = 0.0
        self.last_path_center = None
        self.cap_mode = ""

        # 空白帧 / 倒车状态
        self.blank_count  = 0      # 连续空白/模糊帧计数
        self.nopath_count = 0      # 连续无路径帧计数
        self.backup_until  = 0.0    # 倒车截止时间戳
        self.explore_until = 0.0    # 倒车后探索转向截止时间戳
        self.explore_dir   = 'L'    # 探索转向方向

        # 性能统计
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.fps_frame_counter = 0

        # 日志文件（CSV，方便后期分析）
        self._log_file = None
        if LOG_ENABLED:
            _log_path = datetime.datetime.now().strftime("nav_%Y%m%d_%H%M%S.csv")
            try:
                self._log_file = open(_log_path, 'w', buffering=1, encoding='utf-8')
                self._log_file.write("timestamp,frame,raw_cmd,last_sent,reason,danger,path_found,blank\n")
                print(f"[Info] Log file: {_log_path}")
            except Exception as _e:
                print(f"[Warn] Cannot open log file: {_e}")

        # 检测/分割模型独立帧率控制
        self.last_det_time = 0.0
        self.last_seg_time = 0.0
        self.det_interval = 1.0 / DET_TARGET_FPS
        self.seg_interval = 1.0 / SEG_TARGET_FPS
        self.last_det_result = {"has_obstacle": False, "danger": 0.0, "avoid_cmd": None, "emergency": False}
        self.last_seg_result = {"path_found": False, "path_center": None, "score": 0.0}

        # 配置加载
        self.runtime_cfg = self._load_runtime_config()

        # 1. 初始化串口
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
            print(f"[Info] Serial connected on {SERIAL_PORT}")
        except Exception as e:
            print(f"[Error] Serial connection failed: {e}")
            self.ser = None

        # 2. 加载模型
        print("[Info] Loading Models...")
        det_path = MODEL_DET_PATH
        seg_path = MODEL_SEG_PATH

        for engine_path in [det_path, seg_path]:
            if engine_path.endswith('.engine') and not os.path.exists(engine_path):
                pt_path = engine_path.replace('.engine', '.pt')
                print(f"[Init] '{engine_path}' not found. Auto-exporting from '{pt_path}' to TensorRT Engine...")
                print("[Init] This process takes 2-5 minutes on Orin Nano. Please wait...")
                try:
                    model = YOLO(pt_path)
                    model.export(format='engine', device=0, half=True)
                    print(f"[Init] Export success: {engine_path}")
                except Exception as e:
                    print(f"[Error] Failed to export {engine_path}: {e}")
                    print("[Warn] Falling back to slow .pt model...")
                    if engine_path == det_path:
                        det_path = pt_path
                    else:
                        seg_path = pt_path

        def _load_yolo(path):
            try:
                return YOLO(path)
            except Exception as e:
                if '.engine' in path and ('tensorrt' in str(e).lower() or 'ModuleNotFoundError' in str(type(e).__name__)):
                    pt_path = path.replace('.engine', '.pt')
                    print(f"[Warn] TensorRT not available ({e}). Falling back to '{pt_path}'...")
                    return YOLO(pt_path)
                raise

        # CUDA 可用性预检：engine 文件依赖 CUDA，不可用时提前降级到 .pt 避免 segfault
        import torch
        cuda_ok = torch.cuda.is_available()
        if not cuda_ok:
            print("[Warn] CUDA not available (cudaErrorNoDevice or driver issue). "
                  "Engine files will NOT be loaded. Falling back to .pt models.")
            if det_path.endswith('.engine'):
                det_path = det_path.replace('.engine', '.pt')
            if seg_path.endswith('.engine'):
                seg_path = seg_path.replace('.engine', '.pt')

        self.model_det = _load_yolo(det_path)
        self.model_seg = _load_yolo(seg_path)
        print("[Info] Models Loaded.")

        # 3. 初始化视频输入
        self.cap = self._open_video_source()

        # 4. 异步采集线程（解决 USB 高帧率内核缓冲积压导致的画面卡住问题）
        self.cap = AsyncCaptureThread(self.cap)
        print("[Info] Async capture thread started.")

    def _load_runtime_config(self):
        cfg = {
            "camera": {"device": USB_DEVICE, "width": CAPTURE_WIDTH, "height": CAPTURE_HEIGHT, "fps": CAPTURE_FPS},
            "rtsp": {"input_url": RTSP_INPUT_URL, "prefer_input": PREFER_RTSP_INPUT},
        }
        if not os.path.exists(CONFIG_PATH):
            return cfg
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user_cfg = json.load(f)
            if isinstance(user_cfg, dict):
                for section in ("camera", "rtsp"):
                    if isinstance(user_cfg.get(section), dict):
                        cfg[section].update(user_cfg[section])
            print(f"[Info] Loaded runtime config from {CONFIG_PATH}")
        except Exception as e:
            print(f"[Warn] Failed to read {CONFIG_PATH}: {e}. Use defaults.")
        return cfg

    def _open_cv_capture(self, source):
        cap = cv2.VideoCapture(source)
        cam_cfg = self.runtime_cfg.get("camera", {})
        # 优先请求 MJPG 格式：USB 720p 必须用压缩格式，否则 USB2.0 带宽不足
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  int(cam_cfg.get("width",  CAPTURE_WIDTH)))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cam_cfg.get("height", CAPTURE_HEIGHT)))
        cap.set(cv2.CAP_PROP_FPS,          int(cam_cfg.get("fps",    CAPTURE_FPS)))
        # 关键：将驱动缓冲减到 1 帧，避免 USB 缓冲积压导致的旧帧延迟
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if cap.isOpened():
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[Info] Camera opened: {actual_w}x{actual_h} (requested {int(cam_cfg.get('width', CAPTURE_WIDTH))}x{int(cam_cfg.get('height', CAPTURE_HEIGHT))})")
            return cap
        cap.release()
        return None

    def _create_usb_capture_with_rtsp_output(self):
        if not RTSP_SERVER_AVAILABLE:
            return None
        self.rtsp_server = GStreamerRtspServer(
            port=str(self.runtime_cfg.get("rtsp", {}).get("port", "8554")),
            mount_point=str(self.runtime_cfg.get("rtsp", {}).get("mount_point", "/test")),
        )
        self.rtsp_server.start()

        cam_cfg = self.runtime_cfg.get("camera", {})
        cam_dev = str(cam_cfg.get("device", USB_DEVICE))
        cam_w = int(cam_cfg.get("width", 640))
        cam_h = int(cam_cfg.get("height", 480))
        cam_fps = int(cam_cfg.get("fps", 15))
        bridge_host = "127.0.0.1"
        bridge_port = 5400

        # 720p 必须使用 MJPG，否则 USB2.0 带宽不足
        gst_str = (
            f"v4l2src device={cam_dev} ! "
            f"image/jpeg, width={cam_w}, height={cam_h}, framerate={cam_fps}/1 ! jpegdec ! "
            "tee name=t "
            f"t. ! queue leaky=1 max-size-buffers=1 ! videoconvert ! video/x-raw,format=I420 ! "
            f"x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 ! "
            f"rtph264pay config-interval=1 pt=96 ! udpsink host={bridge_host} port={bridge_port} sync=false "
            "t. ! queue leaky=1 max-size-buffers=1 ! videoconvert ! "
            "video/x-raw, format=BGR ! appsink name=mysink emit-signals=true sync=false max-buffers=1 drop=true"
        )
        try:
            return GStreamerCapture(gst_str)
        except Exception as e:
            print(f"[Warn] GStreamer USB+RTSP pipeline failed: {e}")
            return None

    def _open_video_source(self):
        rtsp_cfg = self.runtime_cfg.get("rtsp", {})
        cam_cfg = self.runtime_cfg.get("camera", {})
        rtsp_input = str(rtsp_cfg.get("input_url", RTSP_INPUT_URL)).strip()
        prefer_rtsp = bool(rtsp_cfg.get("prefer_input", PREFER_RTSP_INPUT))

        def try_rtsp():
            if not rtsp_input:
                return None
            print(f"[Info] Trying RTSP input: {rtsp_input}")
            cap = self._open_cv_capture(rtsp_input)
            if cap is not None:
                self.cap_mode = f"RTSP-IN({rtsp_input})"
                return cap
            print("[Warn] RTSP input open failed.")
            return None

        def try_usb():
            cap = self._create_usb_capture_with_rtsp_output()
            if cap is not None:
                self.cap_mode = "USB(GStreamer)+RTSP-OUT"
                return cap
            usb_dev = str(cam_cfg.get("device", USB_DEVICE))
            print(f"[Info] Trying USB camera: {usb_dev}")
            cap = self._open_cv_capture(usb_dev)
            if cap is None:
                cap = self._open_cv_capture(USB_CAMERA_INDEX)
            if cap is not None:
                self.cap_mode = f"USB(OpenCV:{usb_dev})"
                return cap
            return None

        cap = try_rtsp() if prefer_rtsp else try_usb()
        if cap is None:
            cap = try_usb() if prefer_rtsp else try_rtsp()
        if cap is None:
            raise RuntimeError("No available video source (RTSP/USB both failed).")

        print(f"[Info] Video source ready: {self.cap_mode}")
        return cap

    def send_cmd(self, cmd):
        """发送指令到 Arduino"""
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode())
                print(f"[{ts}] --> SENT: {cmd}")
            except Exception as e:
                print(f"[{ts}] [Error] Serial write: {e}")
        else:
            print(f"[{ts}] [Sim] CMD: {cmd}")

    def filter_and_send(self, raw_cmd):
        self.cmd_window.append(raw_cmd)
        counts = {}
        for cmd in self.cmd_window:
            counts[cmd] = counts.get(cmd, 0) + 1
        stable_cmd = max(counts, key=counts.get)

        if stable_cmd == self.current_stable_cmd:
            self.consecutive_count += 1
        else:
            self.current_stable_cmd = stable_cmd
            self.consecutive_count = 1

        threshold = {'L': 2, 'R': 2, 'F': 2, 'P': 1, 'S': 1}.get(stable_cmd, 2)
        now = time.time()
        # 关键/紧急指令快速发送，常规指令保持防抖间隔
        refresh_interval = {'B': 0.25, 'S': 0.25, 'L': 0.6, 'R': 0.6, 'F': 0.9, 'P': 0.9}.get(stable_cmd, 0.9)
        should_send = (
            self.consecutive_count >= threshold and
            (stable_cmd != self.last_sent_cmd or (now - self.last_cmd_send_time) > refresh_interval)
        )

        if should_send:
            self.send_cmd(stable_cmd)
            self.last_sent_cmd = stable_cmd
            self.last_cmd_send_time = now

    def _write_log(self, raw_cmd, reason, danger, path_found, blank):
        if self._log_file is None:
            return
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            self._log_file.write(
                f'{ts},{self.frame_count},{raw_cmd},{self.last_sent_cmd or "-"},'
                f'"{reason}",{danger:.3f},{int(path_found)},{int(blank)}\n'
            )
        except Exception:
            pass

    def _analyze_obstacle(self, frame, w, h):
        results_det = self.model_det(frame, verbose=False, conf=CONF_THRESHOLD)
        center_x = w / 2.0
        best = None

        for r in results_det:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id not in OBSTACLE_CLASSES:
                    continue
                x1, y1, x2, y2 = box.xyxy[0]
                conf = float(box.conf[0]) if box.conf is not None else 1.0
                box_w = max(1.0, float(x2 - x1))
                box_h = max(1.0, float(y2 - y1))
                area_ratio = (box_w * box_h) / float(w * h)
                box_center_x = float((x1 + x2) / 2.0)
                center_bias = min(1.0, abs(box_center_x - center_x) / max(1.0, center_x))
                near_score = min(1.0, box_h / float(h))
                lane_weight = 1.2 if (w * 0.2 < box_center_x < w * 0.8) else 0.65
                danger = conf * lane_weight * (0.45 * min(1.0, area_ratio * 3.2) + 0.35 * near_score + 0.20 * (1.0 - center_bias))

                item = {
                    "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                    "center_x": box_center_x,
                    "height_ratio": box_h / float(h),
                    "danger": float(danger),
                }
                if best is None or item["danger"] > best["danger"]:
                    best = item

        if best is None:
            return {"has_obstacle": False, "danger": 0.0, "avoid_cmd": None, "emergency": False}

        # 高度触发紧急停车需满足最低危险度(0.30)，避免低置信度目标误触发
        emergency = (best["height_ratio"] >= STOP_DISTANCE_RATIO and best["danger"] >= 0.30) or \
                    best["danger"] >= EMERGENCY_DANGER_THRESHOLD
        avoid_cmd = 'R' if best["center_x"] < center_x else 'L'

        color = (0, 0, 255) if emergency else (0, 165, 255)
        cv2.rectangle(frame, (best["x1"], best["y1"]), (best["x2"], best["y2"]), color, 3)
        cv2.putText(frame, f"OBS danger={best['danger']:.2f}", (best["x1"], max(20, best["y1"] - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        return {
            "has_obstacle": True,
            "danger": best["danger"],
            "avoid_cmd": avoid_cmd,
            "emergency": emergency,
        }

    def _analyze_path(self, frame, w, h):
        results_seg = self.model_seg(frame, verbose=False, conf=CONF_THRESHOLD)
        if len(results_seg) == 0 or results_seg[0].masks is None:
            return {"path_found": False, "path_center": None, "score": 0.0}

        masks = results_seg[0].masks.data.cpu().numpy()
        if masks is None or len(masks) == 0:
            return {"path_found": False, "path_center": None, "score": 0.0}

        seg_h, seg_w = masks[0].shape
        bottom_start = int(seg_h * BOTTOM_PATH_RATIO)
        best_center = None
        best_score = -1.0

        seg_classes = None
        if getattr(results_seg[0], 'boxes', None) is not None and results_seg[0].boxes.cls is not None:
            seg_classes = [int(c) for c in results_seg[0].boxes.cls.cpu().numpy().tolist()]

        for idx, mask in enumerate(masks):
            if PATH_CLASS_ID is not None and seg_classes is not None and idx < len(seg_classes):
                if seg_classes[idx] != PATH_CLASS_ID:
                    continue

            mask_bin = (mask > 0.5).astype(np.uint8)
            area = int(mask_bin.sum())
            if area < AREA_THRESHOLD / 8:
                continue

            bottom_mask = mask_bin[bottom_start:, :]
            bottom_area = int(bottom_mask.sum())
            if bottom_area <= 0:
                continue

            moments = cv2.moments(bottom_mask)
            if moments["m00"] <= 1e-6:
                continue

            cx_bottom = float(moments["m10"] / moments["m00"])
            center_x = int(cx_bottom * (w / float(seg_w)))
            score = (0.6 * (bottom_area / float(seg_w * (seg_h - bottom_start))) +
                     0.4 * (area / float(seg_w * seg_h)))

            if score > best_score:
                best_score = score
                best_center = center_x

        if best_center is None:
            return {"path_found": False, "path_center": None, "score": 0.0}

        if self.path_center_ema is None:
            self.path_center_ema = float(best_center)
        else:
            self.path_center_ema = PATH_EMA_ALPHA * float(best_center) + (1.0 - PATH_EMA_ALPHA) * self.path_center_ema

        final_center = int(self.path_center_ema)
        self.last_path_center = final_center
        self.last_path_time = time.time()

        cv2.circle(frame, (final_center, int(h * 0.78)), 9, (0, 255, 0), -1)
        cv2.line(frame, (w // 2, int(h * 0.70)), (final_center, int(h * 0.70)), (255, 255, 0), 2)

        return {"path_found": True, "path_center": final_center, "score": max(0.0, best_score)}

    def _decide_command(self, obstacle_info, path_info, frame_w):
        center_x = frame_w // 2

        if obstacle_info["has_obstacle"] and obstacle_info["emergency"]:
            return 'S', f"Emergency danger={obstacle_info['danger']:.2f}"

        if obstacle_info["has_obstacle"] and obstacle_info["danger"] >= AVOID_DANGER_THRESHOLD:
            return obstacle_info["avoid_cmd"], f"Avoid danger={obstacle_info['danger']:.2f}"

        if path_info["path_found"]:
            diff = path_info["path_center"] - center_x
            if abs(diff) <= CENTER_TOLERANCE:
                return 'F', f"Path center diff={diff:+d}"
            if diff > 0:
                return 'R', f"Path right diff={diff:+d}"
            return 'L', f"Path left diff={diff:+d}"

        if self.last_path_center is not None and (time.time() - self.last_path_time) <= PATH_LOST_TIMEOUT:
            diff = self.last_path_center - center_x
            if abs(diff) <= CENTER_TOLERANCE:
                return 'P', "Path memory hold"
            return ('R', "Path memory adjust") if diff > 0 else ('L', "Path memory adjust")

        # 无路径但有障碍物：利用障碍位置推断可行方向（向避障侧行驶）
        if obstacle_info["has_obstacle"] and obstacle_info["avoid_cmd"] and obstacle_info["danger"] >= 0.20:
            return obstacle_info["avoid_cmd"], f"Steer-by-obs danger={obstacle_info['danger']:.2f}"

        return 'S', "No path"

    def process_frame(self):
        # 从异步线程取最新帧（非阻塞）
        frame = self.cap.get_latest()
        if frame is None:
            time.sleep(0.005)
            return

        current_time = time.time()
        h_orig, w_orig = frame.shape[:2]

        # 画面质量检测：灰度方差极低说明画面空白或严重模糊
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        is_blank = float(np.var(gray)) < BLANK_VAR_THRESH
        if is_blank:
            self.blank_count += 1
        else:
            self.blank_count = 0

        # 预处理：裁剪/缩放到推理分辨率
        infer_frame, crop_rect = preprocess_for_inference(frame)
        ih, iw = infer_frame.shape[:2]

        # 检测模型：1fps，远距障碍物初判
        # USB 摄像头低帧率采样长期稳定，不会因帧率过高导致内核缓冲积压
        if current_time - self.last_det_time >= self.det_interval:
            self.last_det_result = self._analyze_obstacle(infer_frame, iw, ih)
            self.last_det_time = current_time

        # 分割模型：5fps，路径跟踪
        if current_time - self.last_seg_time >= self.seg_interval:
            self.last_seg_result = self._analyze_path(infer_frame, iw, ih)
            self.last_seg_time = current_time

        # 无路径帧计数（用于触发倒车）
        if not self.last_seg_result["path_found"]:
            self.nopath_count += 1
        else:
            self.nopath_count = 0

        current_cmd, reason = self._decide_command(self.last_det_result, self.last_seg_result, iw)

        # 倒车 + 探索逻辑：持续空白/无路径且无障碍时后退，然后转向探索
        has_obs = self.last_det_result["has_obstacle"]
        emergency = self.last_det_result["emergency"]
        path_found_now = self.last_seg_result["path_found"]
        if current_time < self.backup_until:
            # 正在倒车期间：紧急障碍优先停车，否则保持倒车
            if emergency:
                current_cmd, reason = 'S', "Emergency override during backup"
                self.backup_until = 0.0
            elif not has_obs:
                current_cmd = 'B'
                reason = f"Backup({self.backup_until - current_time:.1f}s left)"
        elif current_time < self.explore_until:
            # 倒车结束后探索转向：找到路径/遇到障碍则恢复正常决策
            if not has_obs and not emergency and not path_found_now:
                current_cmd = self.explore_dir
                reason = f"PostBackup-Explore {self.explore_dir}({self.explore_until - current_time:.1f}s left)"
        elif not has_obs and not emergency:
            _bn, _nn = self.blank_count, self.nopath_count
            if _bn >= BACKUP_BLANK_N or _nn >= BACKUP_NOPATH_N:
                # 根据路径记忆或障碍方向决定倒车后的探索转向
                if self.last_path_center is not None:
                    self.explore_dir = 'R' if self.last_path_center > iw // 2 else 'L'
                elif self.last_det_result.get("avoid_cmd"):
                    self.explore_dir = self.last_det_result["avoid_cmd"]
                self.backup_until  = current_time + BACKUP_DURATION
                self.explore_until = current_time + BACKUP_DURATION + 2.0
                self.blank_count  = 0
                self.nopath_count = 0
                current_cmd = 'B'
                reason = f"Backup triggered(blank_cnt={_bn},nopath_cnt={_nn},explore={self.explore_dir})"

        self.filter_and_send(current_cmd)
        self._write_log(current_cmd, reason, self.last_det_result['danger'],
                        self.last_seg_result['path_found'], is_blank)

        # OSD 叠加（在推理帧上，已含检测框）
        status_text = f"RAW: {current_cmd} | SENT: {self.last_sent_cmd} | CNT: {self.consecutive_count}"
        cv2.putText(infer_frame, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(infer_frame, f"Reason: {reason}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(infer_frame, f"Src: {self.cap_mode} [{w_orig}x{h_orig}]  Mode: {PREPROCESS_MODE}->{iw}x{ih}",
                    (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 220, 255), 1)
        cv2.putText(infer_frame, f"Danger: {self.last_det_result['danger']:.2f}  "
                    f"Det@{DET_TARGET_FPS:.0f}fps Seg@{SEG_TARGET_FPS:.0f}fps",
                    (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (50, 180, 255), 1)

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elapsed_time = time.time() - self.start_time

        self.frame_count += 1
        self.fps_frame_counter += 1
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.fps_frame_counter / (now - self.last_fps_time)
            self.fps_frame_counter = 0
            self.last_fps_time = now

        cv2.rectangle(infer_frame, (0, ih - 85), (320, ih), (0, 0, 0), -1)
        cv2.putText(infer_frame, f"Time: {timestamp_str}", (10, ih - 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(infer_frame, f"Frame: {self.frame_count} | FPS: {self.fps:.1f}", (10, ih - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(infer_frame, f"Elapsed: {elapsed_time:.1f}s", (10, ih - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.imshow("Dual Model Guard", infer_frame)

    def run(self):
        try:
            while True:
                self.process_frame()
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.send_cmd('S')
            if hasattr(self, '_log_file') and self._log_file:
                self._log_file.close()
                print("[Info] Log file closed.")
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
            if hasattr(self, 'rtsp_server') and self.rtsp_server is not None:
                self.rtsp_server.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    robot = RobotNavigator()
    robot.run()
