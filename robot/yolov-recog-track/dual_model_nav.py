import cv2
import numpy as np
import time
import serial
import sys
import os
import threading
import datetime
from ultralytics import YOLO

# GStreamer support check
GI_AVAILABLE = False
RTSP_SERVER_AVAILABLE = False
try:
    import gi

    gi.require_version("Gst", "1.0")
    gi.require_version("GstRtspServer", "1.0")
    from gi.repository import Gst, GstRtspServer, GLib

    GI_AVAILABLE = True
    RTSP_SERVER_AVAILABLE = True
except ImportError:
    try:
        import gi

        gi.require_version("Gst", "1.0")
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

        print(
            f"[RTSP Server] Server started at rtsp://0.0.0.0:{self.port}{self.mount_point}"
        )

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

        self.appsink = self.pipeline.get_by_name("mysink")
        if not self.appsink:
            raise RuntimeError("Could not find appsink with name 'mysink' in pipeline")

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)
        self.last_error = None

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(
                f"Failed to set pipeline to PLAYING (FAILURE). Last error: {self.last_error}"
            )

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
        if self.last_error:
            return False
        return True  # Simplified

    def read(self):
        if self.last_error:
            print(
                f"[GStreamerCapture] Cannot read, pipeline in error state: {self.last_error}"
            )
            return False, None

        sample = self.appsink.emit("pull-sample")
        if not sample:
            return False, None

        buf = sample.get_buffer()
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        h = structure.get_value("height")
        w = structure.get_value("width")

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


# ================= 配置区域 =================
# 串口设置 (请确认端口号，通常是 /dev/ttyUSB0 或 /dev/ttyACM0)
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

# 模型路径 (优先使用 TensorRT Engine 以获得极致速度)
MODEL_DET_PATH = "yolov8n.engine"  # 检测模型：负责避障 (人, 障碍物)
MODEL_SEG_PATH = "yolov8m-seg.engine"  # 分割模型：负责寻路 (路面)

# 阈值设置
CONF_THRESHOLD = 0.5
AREA_THRESHOLD = 5000  # 最小路面面积，太小说明前面没路了
CENTER_TOLERANCE = 80  # 中心容差，在这个范围内算直行 (像素)
STOP_DISTANCE_RATIO = 0.3  # 障碍物占画面高度比例超过此值不仅避让，而是停车

# 避障类别ID (COCO数据集: 0=人, 1=自行车, 2=车, ... 可以根据需求添加)
OBSTACLE_CLASSES = [0, 1, 2, 3, 5, 7]

# 寻路类别ID (假设分割模型能分出路面。如果是通用模型，可以设为 None，即便取最大连通域)
# 如果你是训练过的路面模型，填入路面的 class id
PATH_CLASS_ID = 0

# FPS 控制
TARGET_FPS = 5  # 目标帧率 (3-5 之间)
PROCESS_INTERVAL = 1.0 / TARGET_FPS


class RobotNavigator:
    def __init__(self):
        # 0. 状态初始化
        self.cmd_history = []  # 指令缓存
        self.last_sent_cmd = None  # 上次发送给 UNO 的指令
        self.last_process_time = 0
        self.consecutive_count = 0  # 连续计数
        self.current_stable_cmd = None

        # 性能统计
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.fps_frame_counter = 0

        # 1. 初始化串口
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
            print(f"[Info] Serial connected on {SERIAL_PORT}")
        except Exception as e:
            print(f"[Error] Serial connection failed: {e}")
            self.ser = None

        # 2. 加载模型
        print("[Info] Loading Models...")

        # 自动检查并生成 Engine 模型
        # 为了能够在局部函数里修改全局变量，这里使用一个临时的字典来处理路径
        # 直接修改 self 下的变量，或者在循环外部使用全局变量

        det_path = MODEL_DET_PATH
        seg_path = MODEL_SEG_PATH

        for engine_path in [det_path, seg_path]:
            if engine_path.endswith(".engine") and not os.path.exists(engine_path):
                pt_path = engine_path.replace(".engine", ".pt")
                print(
                    f"[Init] '{engine_path}' not found. Auto-exporting from '{pt_path}' to TensorRT Engine..."
                )
                print(
                    "[Init] This process takes 2-5 minutes on Orin Nano. Please wait..."
                )
                try:
                    model = YOLO(pt_path)
                    model.export(
                        format="engine", device=0, half=True
                    )  # 使用半精度更适合 Jetson
                    print(f"[Init] Export success: {engine_path}")
                except Exception as e:
                    print(f"[Error] Failed to export {engine_path}: {e}")
                    print("[Warn] Falling back to slow .pt model...")
                    if engine_path == det_path:
                        det_path = pt_path
                    else:
                        seg_path = pt_path

        self.model_det = YOLO(det_path)
        self.model_seg = YOLO(seg_path)
        print("[Info] Models Loaded.")

        # 3. 摄像头 (含 RTSP 推流)
        if RTSP_SERVER_AVAILABLE:
            # 启动 RTSP 服务器
            self.rtsp_server = GStreamerRtspServer()
            self.rtsp_server.start()

            # GStreamer Pipeline: Split to RTSP (UDP) and App (Appsink)
            cam_dev = "/dev/video0"
            cam_w = 640
            cam_h = 480
            cam_fps = 10
            bridge_host = "127.0.0.1"
            bridge_port = 5400

            gst_str = (
                f"v4l2src device={cam_dev} ! "
                f"video/x-raw, width={cam_w}, height={cam_h}, framerate={cam_fps}/1 ! "
                "tee name=t "
                # Branch 1: RTSP (Encode and push to UDP)
                f"t. ! queue leaky=1 ! videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 ! "
                f"rtph264pay config-interval=1 pt=96 ! udpsink host={bridge_host} port={bridge_port} sync=false "
                # Branch 2: App (Raw BGR to Appsink)
                "t. ! queue leaky=1 ! videoconvert ! video/x-raw, format=BGR ! appsink name=mysink emit-signals=true sync=false max-buffers=1 drop=true"
            )

            try:
                self.cap = GStreamerCapture(gst_str)
            except Exception as e:
                print(
                    f"[Warn] GStreamer init failed: {e}. Fallback to cv2.VideoCapture."
                )
                self.cap = cv2.VideoCapture(0)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        else:
            print("[Warn] RTSP libs not available. Fallback to cv2.VideoCapture.")
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

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
        """
        指令滤波逻辑：
        - L/R: 需要连续 3 次
        - S/P: 需要连续 4 次
        - F: 默认 3 次 (平滑启动)
        """
        threshold = 3
        if raw_cmd in ["L", "R"]:
            threshold = 3
        elif raw_cmd in ["S", "P"]:
            threshold = 4

        if raw_cmd == self.current_stable_cmd:
            self.consecutive_count += 1
        else:
            self.consecutive_count = 1
            self.current_stable_cmd = raw_cmd

        # 达到阈值才发送，且不重复发送相同指令 (除非你想持续发送)
        # 这里假设只在改变时发送，或者每隔一定周期发送。
        # 此处逻辑：一旦满足且不等于上次发送的，就发送
        if self.consecutive_count >= threshold:
            if raw_cmd != self.last_sent_cmd:
                self.send_cmd(raw_cmd)
                self.last_sent_cmd = raw_cmd
            else:
                # 即使是相同指令，偶尔发送一次也无妨（防丢包），但不要太频繁
                # 例如计数每增加 10 次发送一次
                if self.consecutive_count % 10 == 0:
                    self.send_cmd(raw_cmd)

    def process_frame(self):
        # 0. 摄像头读取 & FPS 控制
        ret, frame = self.cap.read()
        if not ret:
            return

        current_time = time.time()
        if current_time - self.last_process_time < PROCESS_INTERVAL:
            return  # 跳过处理，保持帧率
        self.last_process_time = current_time

        h, w, _ = frame.shape
        center_x = w // 2

        # 指令缓存
        current_cmd = "S"  # 默认停止，安全第一
        reason = "Init"

        # -------------------------------------------------
        # Step 1: 障碍物检测 (Detection) - 优先级最高
        # -------------------------------------------------
        results_det = self.model_det(frame, verbose=False, conf=CONF_THRESHOLD)
        obstacle_detected = False

        for r in results_det:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id in OBSTACLE_CLASSES:
                    # 检查位置: 只有在画面中间区域的障碍物才危险
                    x1, y1, x2, y2 = box.xyxy[0]
                    box_center_x = (x1 + x2) / 2
                    box_h = y2 - y1

                    # 障碍物判断逻辑：
                    # 1. 在横向中间 60% 区域内
                    # 2. 高度足够大 (离得近)
                    if (w * 0.2 < box_center_x < w * 0.8) and (box_h > h * 0.25):
                        obstacle_detected = True

                        # 绘制警告框
                        cv2.rectangle(
                            frame,
                            (int(x1), int(y1)),
                            (int(x2), int(y2)),
                            (0, 0, 255),
                            3,
                        )
                        cv2.putText(
                            frame,
                            "OBSTACLE",
                            (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 0, 255),
                            2,
                        )

                        if box_h > h * 0.5:  # 极近
                            reason = "Emergency Stop (Obstacle Close)"
                            current_cmd = "S"
                        else:
                            # 简单绕行逻辑：障碍物偏左，我向右；障碍物偏右，我向左
                            if box_center_x < center_x:
                                reason = "Avoid Right"
                                current_cmd = "R"  # 强行右转
                            else:
                                reason = "Avoid Left"
                                current_cmd = "L"  # 强行左转
                        break
            if obstacle_detected:
                break

        # -------------------------------------------------
        # Step 2: 路径规划 (Segmentation) - 既然没障碍，怎么走？
        # -------------------------------------------------
        if not obstacle_detected:
            results_seg = self.model_seg(frame, verbose=False, conf=CONF_THRESHOLD)

            # 寻找分割掩码
            path_found = False
            best_mask_center = None

            if results_seg[0].masks is not None:
                # 获取所有掩码点
                # 注意：这里简化处理，假设最大的那个掩码就是路
                # 如果你有特定类别的路 (PATH_CLASS_ID), 应该在这里过滤

                # 提取掩码并计算重心
                # Ultralytics 返回的 masks.data 是 tensor，需要转 numpy
                masks = results_seg[0].masks.data.cpu().numpy()  # (N, H, W) 小图

                # 假如只取置信度最高的那个 mask (通常可以工作)
                if len(masks) > 0:
                    # 缩放掩码回原图大小 (简单方案：直接用 xyn 或在小图算重心再映射)
                    # 这里直接在 160x120 (默认seg大小) 上计算重心，然后比例映射回 640x480
                    mask = masks[0]
                    M = cv2.moments(mask)
                    if M["m00"] > 0:  # 面积 > 0
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])

                        # 映射回原图坐标
                        scale_x = w / mask.shape[1]
                        real_cX = int(cX * scale_x)

                        # 绘制重心
                        cv2.circle(
                            frame,
                            (real_cX, int(cY * (h / mask.shape[0]))),
                            10,
                            (0, 255, 0),
                            -1,
                        )

                        # 导航逻辑
                        diff = real_cX - center_x
                        if abs(diff) < CENTER_TOLERANCE:
                            current_cmd = "F"
                            reason = "Path Center"
                        elif diff > 0:
                            current_cmd = "R"
                            reason = "Path Right"
                        else:
                            current_cmd = "L"
                            reason = "Path Left"
                        path_found = True

            if not path_found:
                current_cmd = "S"
                reason = "No Path Found"

        # 滤波并发送
        self.filter_and_send(current_cmd)

        # 界面显示
        status_text = f"RAW: {current_cmd} | SENT: {self.last_sent_cmd} | CNT: {self.consecutive_count}"
        cv2.putText(
            frame, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )
        cv2.putText(
            frame,
            f"Reason: {reason}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
        )

        # 统计信息显示 (参考 recog-yolov-v8m-seg.py)
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elapsed_time = time.time() - self.start_time

        # FPS 计算
        self.frame_count += 1
        self.fps_frame_counter += 1
        now = time.time()
        if now - self.last_fps_time >= 1.0:
            self.fps = self.fps_frame_counter / (now - self.last_fps_time)
            self.fps_frame_counter = 0
            self.last_fps_time = now

        # 绘制背景框
        cv2.rectangle(frame, (0, h - 85), (320, h), (0, 0, 0), -1)

        # 绘制统计文字
        cv2.putText(
            frame,
            f"Time: {timestamp_str}",
            (10, h - 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            f"Frame: {self.frame_count} | FPS: {self.fps:.1f}",
            (10, h - 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
        cv2.putText(
            frame,
            f"Elapsed: {elapsed_time:.1f}s",
            (10, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )

        cv2.imshow("Dual Model Guard", frame)

    def run(self):
        try:
            while True:
                self.process_frame()
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            self.send_cmd("S")  # 退出时停车
            self.cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    robot = RobotNavigator()
    robot.run()
