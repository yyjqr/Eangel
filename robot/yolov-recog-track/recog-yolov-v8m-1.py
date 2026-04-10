"""
YOLOv8 based Path Follow ROS 2 Node (Ultralytics)
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import cv2
import numpy as np
import threading
import time
import os
import sys
import logging  # 20180318 JACK
import datetime
import json

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
        # Use a custom context to avoid interfering with the default context (used by OpenCV/Qt/GTK)
        self.context = None
        self.loop = None
        self.server = None
        self.daemon = True  # Kill when main thread exits

    def run(self):
        if not RTSP_SERVER_AVAILABLE:
            print("GstRtspServer not available, skipping RTSP server start.")
            return

        if not Gst.is_initialized():
            Gst.init(None)

        # Create isolated context
        self.context = GLib.MainContext.new()
        self.loop = GLib.MainLoop(self.context)

        # Create server
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(self.port)

        mounts = self.server.get_mount_points()
        factory = GstRtspServer.RTSPMediaFactory()

        # Internal bridge pipeline: Receive H264 from UDP (sent by YOLO node) and pay it to RTSP
        # udpsrc port=5400 -> application/x-rtp -> rtph264depay -> rtph264pay -> RTSP clients
        # Note: We must depay and repay to ensure timestamps and SSRC are handled correctly for the new session,
        # OR just forward the RTP packets if caps match exactly. Depay/Repay is safer.
        # Actually payload=96 is critical.
        pipeline_str = (
            "( udpsrc port=5400 auto-multicast=false ! "
            "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! "
            "rtph264depay ! rtph264pay name=pay0 pt=96 )"
        )

        factory.set_launch(pipeline_str)
        factory.set_shared(True)  # Share one UDP listener for multiple RTSP clients

        mounts.add_factory(self.mount_point, factory)

        print(
            f"[RTSP Server] Server started at rtsp://0.0.0.0:{self.port}{self.mount_point}"
        )
        print(f"[RTSP Server] Internally listening on UDP 5400 for video stream.")

        # Attach to the custom context!
        self.server.attach(self.context)

        # Run the loop with the context
        self.loop.run()

    def stop(self):
        if self.loop.is_running():
            self.loop.quit()


class GStreamerCapture:
    """
    Custom GStreamer capture class to replace cv2.VideoCapture
    when OpenCV is not built with GStreamer support.
    """

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

        # Bus for error handling
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)
        self.last_error = None

        # Start playing
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
        elif t == Gst.MessageType.STATE_CHANGED:
            pass

    def isOpened(self):
        if self.last_error:
            return False

        # Wait up to 5 seconds for state change to settle
        # Gst.SECOND is 1000000000 (ns)
        timeout = 5 * Gst.SECOND
        ret, current, pending = self.pipeline.get_state(timeout)

        if ret == Gst.StateChangeReturn.SUCCESS:
            print(f"[GStreamerCapture] State settled: {current.value_nick}")
            return current == Gst.State.PLAYING
        elif ret == Gst.StateChangeReturn.ASYNC:
            print(
                f"[GStreamerCapture] State change ASYNC. Current: {current.value_nick}, Pending: {pending.value_nick}"
            )
            # If still async after 5s, it's likely stuck, but we return True tentatively if not NULL/READY
            return current != Gst.State.NULL
        elif ret == Gst.StateChangeReturn.NO_PREROLL:
            print(
                f"[GStreamerCapture] State change NO_PREROLL (Live stream?). Current: {current.value_nick}"
            )
            return True
        else:
            print(f"[GStreamerCapture] State change failed: {ret}")
            return False

    def read(self):
        if self.last_error:
            print(
                f"[GStreamerCapture] Cannot read, pipeline in error state: {self.last_error}"
            )
            return False, None

        # Pull sample from appsink
        sample = self.appsink.emit("pull-sample")
        if not sample:
            return False, None

        buf = sample.get_buffer()
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        h = structure.get_value("height")
        w = structure.get_value("width")

        # Read buffer data
        # Note: extract_dup allocates new memory.
        # For zero-copy we'd need map(Gst.MapFlags.READ), but safety first.
        buffer = buf.extract_dup(0, buf.get_size())

        # Assuming BGR/RGB 3 channel (based on caps in pipeline)
        # Verify format strings if needed, but we force BGR in pipeline
        try:
            frame = np.ndarray((h, w, 3), buffer=buffer, dtype=np.uint8)
            return (
                True,
                frame.copy(),
            )  # Return a copy to be safe given underlying buffer scope
        except Exception as e:
            print(f"Frame decode error: {e}")
            return False, None

    def release(self):
        self.pipeline.set_state(Gst.State.NULL)

    def set(self, prop, val):
        pass  # Dummy for compatibility

    def get(self, prop):
        return 0  # Dummy


# Ultralytics YOLO
try:
    from ultralytics import YOLO
except ImportError:
    print(
        "Error: ultralytics not installed. Please install with: pip install ultralytics"
    )
    sys.exit(1)

log_file = "%s%s%s" % ("EangelGo_new", datetime.date.today(), ".log")
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

handler = logging.FileHandler(log_file)  # "Eangel log.txt"
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)

logger.info("Eangel")
logger.info("Start print log")
# logger.info(host_addr)
logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Serial for Arduino (Optional)
try:
    import serial
except ImportError:
    serial = None

CONF_THRESH = 0.5


class PublishThread(threading.Thread):
    def __init__(self, node, rate):
        super(PublishThread, self).__init__()
        self.node = node
        self.publisher = node.create_publisher(Twist, "cmd_vel", 1)
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.th = 0.0
        self.speed = 0.0
        self.turn = 0.0
        self.condition = threading.Condition()
        self.done = False

        if rate != 0.0:
            self.timeout = 1.0 / rate
        else:
            self.timeout = None

        self.start()

    def wait_for_subscribers(self):
        i = 0
        while rclpy.ok() and self.publisher.get_subscription_count() == 0:
            if i == 4:
                self.node.get_logger().info(
                    "Waiting for subscriber to connect to cmd_vel"
                )
            time.sleep(0.5)
            i += 1
            i = i % 5
        if not rclpy.ok():
            raise Exception("Got shutdown request before subscribers connected")

    def update(self, x, y, z, th, speed, turn):
        with self.condition:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
            self.th = float(th)
            self.speed = float(speed)
            self.turn = float(turn)
            self.condition.notify()

    def stop(self):
        self.done = True
        self.update(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.join()

    def run(self):
        twist = Twist()
        while not self.done and rclpy.ok():
            with self.condition:
                self.condition.wait(self.timeout)
                # Copy state into twist message
                # Ensure all values are floats to prevent AssertionError in ROS 2 messages
                twist.linear.x = float(self.x * self.speed)
                twist.linear.y = float(self.y * self.speed)
                twist.linear.z = float(self.z * self.speed)
                twist.angular.x = 0.0
                twist.angular.y = 0.0
                twist.angular.z = float(self.th * self.turn)

            self.publisher.publish(twist)

        # Stop
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.publisher.publish(twist)


class YOLOv8Node(Node):
    def __init__(self):
        super().__init__("yolov8_node")
        self.pub_thread = None
        self.cap = None
        self.rtsp_server = None

        # Load Config from JSON
        self.cfg = {}
        try:
            with open("config.json", "r") as f:
                self.cfg = json.load(f)
            self.get_logger().info("Loaded config.json")
        except Exception as e:
            self.get_logger().warn(f"Failed to load config.json: {e}, using defaults")

        # State variables for logic (Last known position)
        self.last_center = None
        self.last_img_width = 640  # Default

        # Frame statistics
        self.frame_count = 0
        self.fps = 0.0
        self.fps_update_time = time.time()
        self.fps_frame_count = 0
        self.start_time = time.time()

        # Last command state (避免重复打印)
        self.last_cmd = None
        self.last_cmd_time = 0

        # ===== 摄像头指令防抖状态（与UNO超声波互补，而非干扰） =====
        # 障碍物(B指令)：连续3秒检测到障碍物才发送一次B
        self.obstacle_start_time = None
        self.obstacle_sent = False
        # 转向(L/R指令)：3秒内连续5次同方向判断才发送一次
        self.turn_history = []  # [(direction, timestamp), ...]
        self.last_turn_sent_time = 0
        # 最后实际发送给UNO的指令及时间
        self.last_uno_cmd = None
        self.last_uno_cmd_time = 0
        # 发送指令的最小间隔（秒），避免与超声波指令冲突
        self.MIN_CMD_INTERVAL = 3.0

        try:
            # Defaults
            def_cam_dev = self.cfg.get("camera", {}).get("device", "/dev/video0")
            def_cam_w = self.cfg.get("camera", {}).get("width", 640)
            def_cam_h = self.cfg.get("camera", {}).get("height", 480)
            def_cam_fps = self.cfg.get("camera", {}).get("fps", 20)

            def_rtsp_port = self.cfg.get("rtsp", {}).get("port", "8554")
            def_rtsp_mount = self.cfg.get("rtsp", {}).get("mount_point", "/test")

            def_model = self.cfg.get("model", {}).get("path", "yolov8m.pt")

            # Helper to get parameter with default from JSON or value
            self.declare_parameter("speed", 0.5)
            self.declare_parameter("turn", 1.0)
            self.declare_parameter("repeat_rate", 0.0)
            self.declare_parameter("serial_port", "/dev/ttyUSB0")
            self.declare_parameter("baud_rate", 115200)
            self.declare_parameter("model_path", def_model)

            # Camera & Streaming parameters
            self.declare_parameter("camera_device", def_cam_dev)
            self.declare_parameter("camera_width", def_cam_w)
            self.declare_parameter("camera_height", def_cam_h)
            self.declare_parameter("camera_fps", def_cam_fps)

            # Enable RTSP Server by default now
            self.declare_parameter("enable_rtsp_server", True)
            self.declare_parameter("rtsp_port", def_rtsp_port)
            self.declare_parameter("rtsp_mount", def_rtsp_mount)

            # Get parameters
            self.speed_val = (
                self.get_parameter("speed").get_parameter_value().double_value
            )
            self.turn_val = (
                self.get_parameter("turn").get_parameter_value().double_value
            )
            repeat = (
                self.get_parameter("repeat_rate").get_parameter_value().double_value
            )
            model_path_param = (
                self.get_parameter("model_path").get_parameter_value().string_value
            )

            cam_dev = (
                self.get_parameter("camera_device").get_parameter_value().string_value
            )
            cam_w = (
                self.get_parameter("camera_width").get_parameter_value().integer_value
            )
            cam_h = (
                self.get_parameter("camera_height").get_parameter_value().integer_value
            )
            cam_fps = (
                self.get_parameter("camera_fps").get_parameter_value().integer_value
            )

            enable_rtsp_server = (
                self.get_parameter("enable_rtsp_server")
                .get_parameter_value()
                .bool_value
            )
            rtsp_port = (
                self.get_parameter("rtsp_port").get_parameter_value().string_value
            )
            rtsp_mount = (
                self.get_parameter("rtsp_mount").get_parameter_value().string_value
            )

            # Initialize Serial (Arduino)

            # Initialize Serial (Arduino)
            self.arduino = None
            if serial:
                port = (
                    self.get_parameter("serial_port").get_parameter_value().string_value
                )
                baud = (
                    self.get_parameter("baud_rate").get_parameter_value().integer_value
                )
                try:
                    self.arduino = serial.Serial(port, baud, timeout=0.1)
                    time.sleep(2)  # 等待Arduino复位完成（打开串口会触发UNO复位）
                    self.arduino.flushInput()
                    self.arduino.flushOutput()
                    self.get_logger().info(
                        f"Connected to Arduino at {port}, waited for reset"
                    )
                except Exception as e:
                    self.get_logger().warn(f"Failed to connect to Arduino: {e}")
            else:
                self.get_logger().warn(
                    "pyserial not installed, Arduino communication disabled"
                )

            # Initialize Publisher Thread
            self.pub_thread = PublishThread(self, repeat)

            # Initialize YOLOv8
            self.get_logger().info(f"Loading YOLOv8 model: {model_path_param}")
            # Check if engine exists first for better performance on Jetson
            engine_path = model_path_param.replace(".pt", ".engine")
            if os.path.exists(engine_path):
                self.get_logger().info(f"Found engine file {engine_path}, using that.")
                self.model = YOLO(engine_path, task="detect")
            else:
                self.get_logger().info(
                    f"Engine not found, loading {model_path_param}. first run might be slow."
                )
                self.model = YOLO(model_path_param, task="detect")

            self.out_writer = None

            # Start RTSP Server if enabled
            if enable_rtsp_server and RTSP_SERVER_AVAILABLE:
                self.rtsp_server = GStreamerRtspServer(
                    port=rtsp_port, mount_point=rtsp_mount
                )
                self.rtsp_server.start()
                self.get_logger().info(
                    f"RTSP Server background thread started on port {rtsp_port}"
                )

            # Initialize Camera
            # We want to push to UDP 5400 locally if RTSP server is running (bridge mode)
            # Or if user still thinks about "stream_host" (handled by simple enabling rtsp server now)

            if enable_rtsp_server:
                if not GI_AVAILABLE:
                    self.get_logger().error(
                        "GStreamer python bindings not found. Falling back to simple USB."
                    )
                else:
                    # Use GStreamer pipeline to split stream (Tee) -> [Stream to Local UDP, Appsink for YOLO]
                    # Local UDP (5400) is picked up by RTSP Server
                    bridge_host = "127.0.0.1"
                    bridge_port = 5400

                    self.get_logger().info(
                        f"Opening USB camera {cam_dev} -> Tee -> [RTSP Server Bridge {bridge_host}:{bridge_port}]"
                    )
                    # Updated pipeline: 20fps, name=mysink, explicit format for x264
                    gst_str = (
                        f"v4l2src device={cam_dev} ! "
                        f"video/x-raw, width={cam_w}, height={cam_h}, framerate={cam_fps}/1 ! "
                        "tee name=t "
                        # Branch 1: Encode and push to local UDP (RTSP Server consumes this)
                        f"t. ! queue leaky=1 ! videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 ! "
                        f"rtph264pay config-interval=1 pt=96 ! udpsink host={bridge_host} port={bridge_port} sync=false "
                        # Branch 2: Raw BGR to Appsink
                        "t. ! queue leaky=1 ! videoconvert ! video/x-raw, format=BGR ! appsink name=mysink emit-signals=true sync=false max-buffers=1 drop=true"
                    )
                    try:
                        self.cap = GStreamerCapture(gst_str)
                    except Exception as e:
                        self.get_logger().error(
                            f"Failed to init GStreamer pipeline: {e}"
                        )
                        # Fallback
                        self.cap = cv2.VideoCapture(0)

            if not enable_rtsp_server:
                # Normal USB capture (No RTSP)
                self.get_logger().info(f"Opening USB camera {cam_dev} (No streaming)")
                # extract ID from /dev/videoX
                try:
                    dev_id = int(cam_dev.replace("/dev/video", ""))
                except:
                    dev_id = 0
                self.cap = cv2.VideoCapture(dev_id)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)

            if not self.cap.isOpened():
                raise Exception(f"Failed to open camera ({cam_dev})")

            # Outgoing stream state (not used if Tee is active, but kept for compatibility or manual write if needed)
            self.enable_rtsp = enable_rtsp_server

            # Timer for loop
            self.timer = self.create_timer(0.5, self.process_frame)  # 20 Hz --->2Hz

            self.get_logger().info("YOLOv8 Node initialized successfully")

        except Exception as e:
            self.get_logger().error(f"Failed to initialize node: {e}")
            self.cleanup()
            raise

    def process_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().error("Failed to read frame")
            return

        # 更新帧计数
        self.frame_count += 1
        self.fps_frame_count += 1
        current_time = time.time()

        # 每秒更新FPS
        if current_time - self.fps_update_time >= 1.0:
            self.fps = self.fps_frame_count / (current_time - self.fps_update_time)
            self.fps_frame_count = 0
            self.fps_update_time = current_time

        # Inference
        # verbose=False to keep terminal clean
        results = self.model(frame, verbose=False, conf=CONF_THRESH)

        # Logic Variables
        x, y, z, th = 0, 0, 0, 0
        target_found = False
        center = 0
        img_h, img_w = frame.shape[:2]
        self.last_img_width = img_w

        # Draw and Analyze
        # YOLOv8 results is a list (one for each image in batch)
        result = results[0]

        # Check for Person (Class 0)
        # result.boxes.cls is a tensor of class IDs
        # result.boxes.conf is a tensor of scores
        # result.boxes.xyxy is a tensor of bounding boxes

        highest_conf = 0.0
        best_box = None

        if len(result.boxes) > 0:
            for boxtensor in result.boxes:
                cls_id = int(boxtensor.cls[0])
                conf = float(boxtensor.conf[0])

                # Filter specific classes (e.g., person=0)
                if cls_id == 0:
                    if conf > highest_conf:
                        highest_conf = conf
                        best_box = boxtensor

            if best_box is not None:
                target_found = True
                bbox = best_box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                x1, y1, x2, y2 = map(int, bbox)

                # 计算目标框大小（用于距离估计）
                box_width = x2 - x1
                box_height = y2 - y1
                box_area = box_width * box_height
                box_area_ratio = box_area / (img_w * img_h)  # 目标占画面比例

                # Draw Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Person {highest_conf:.2f}"
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

                # 显示距离估计信息
                distance_label = f"Area: {box_area_ratio*100:.1f}%"
                cv2.putText(
                    frame,
                    distance_label,
                    (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 0),
                    1,
                )

                # Calculate Center
                center = int((x1 + x2) / 2)
                self.last_center = center

                # Control Logic
                right_thresh = int(img_w * 0.70)  # 稍微调整阈值
                left_thresh = int(img_w * 0.30)

                # 距离阈值（根据目标占画面比例判断）
                CLOSE_THRESH = 0.25  # 目标占画面25%以上，太近了，需要暂停或后退
                VERY_CLOSE_THRESH = 0.40  # 目标占画面40%以上，非常近，需要后退

                # Draw Threshold lines
                cv2.line(frame, (left_thresh, 0), (left_thresh, img_h), (255, 0, 0), 1)
                cv2.line(
                    frame, (right_thresh, 0), (right_thresh, img_h), (0, 0, 255), 1
                )

                # 首先判断距离
                if box_area_ratio >= VERY_CLOSE_THRESH:
                    # 太近了，后退
                    x, y, z, th = -1, 0, 0, 0
                    cv2.putText(
                        frame,
                        "TOO CLOSE - Reverse",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )
                elif box_area_ratio >= CLOSE_THRESH:
                    # 比较近，暂停
                    x, y, z, th = 0, 0, 0, 0
                    cv2.putText(
                        frame,
                        "Close - Pause",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 165, 255),
                        2,
                    )
                elif center >= right_thresh:
                    # 右转前进
                    x, y, z, th = 1, 0, 0, -0.5  # 调整转向强度
                    cv2.putText(
                        frame,
                        "Turn Right",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )
                elif center <= left_thresh:
                    # 左转前进
                    x, y, z, th = 1, 0, 0, 0.5  # 调整转向强度
                    cv2.putText(
                        frame,
                        "Turn Left",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 0, 0),
                        2,
                    )
                else:
                    # 直行
                    x, y, z, th = 1, 0, 0, 0
                    cv2.putText(
                        frame,
                        "Go Forward",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2,
                    )

        # Logic when target NOT found (Lost tracking)
        if not target_found:
            if self.last_center is not None:
                # Turn in the direction it was last seen
                mid_point = int(self.last_img_width / 2)
                if self.last_center >= mid_point:
                    x, y, z, th = 0, 0, 0, -1
                    cv2.putText(
                        frame,
                        "Search Right",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 255),
                        2,
                    )
                else:
                    x, y, z, th = 0, 0, 0, 1
                    cv2.putText(
                        frame,
                        "Search Left",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 255),
                        2,
                    )
            else:
                # Never seen, stop
                x, y, z, th = 0, 0, 0, 0
                cv2.putText(
                    frame, "Stop", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
                )

        # 在图像上绘制时间戳和帧统计信息
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elapsed_time = time.time() - self.start_time

        # 绘制信息背景框
        cv2.rectangle(frame, (0, img_h - 80), (300, img_h), (0, 0, 0), -1)

        # 时间戳
        cv2.putText(
            frame,
            f"Time: {timestamp_str}",
            (10, img_h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        # 帧数和FPS
        cv2.putText(
            frame,
            f"Frame: {self.frame_count} | FPS: {self.fps:.1f}",
            (10, img_h - 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
        # 运行时间
        cv2.putText(
            frame,
            f"Elapsed: {elapsed_time:.1f}s",
            (10, img_h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 0),
            1,
        )

        # 优化控制台打印 - 只在状态变化时打印
        cmd_str = f"x={x}, th={th:.2f}"
        if cmd_str != self.last_cmd or (current_time - self.last_cmd_time) > 2.0:
            print(
                f"[{timestamp_str}] Frame:{self.frame_count:05d} FPS:{self.fps:.1f} | Cmd: {cmd_str} | Target: {target_found}"
            )
            self.last_cmd = cmd_str
            self.last_cmd_time = current_time

        # Show Image
        # Note: Streaming is handled by the GStreamer Tee in self.cap, so no manual write needed here.

        cv2.imshow("YOLOv8 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.cleanup()
            rclpy.shutdown()
            return

        # Update ROS Publisher
        if self.pub_thread:
            self.pub_thread.update(
                float(x),
                float(y),
                float(z),
                float(th),
                float(self.speed_val),
                float(self.turn_val),
            )

        # Update Arduino (Optional)
        self.send_arduino_command(x, th)

    def send_arduino_command(self, x, th):
        """摄像头指令防抖发送逻辑

        设计原则：摄像头检测是UNO超声波检测的补充，而非替代。
        - 障碍物(B)：连续3秒检测到障碍物，才发送一次B指令
        - 转向(L/R)：3秒内连续5次同方向判断，才发送一次L或R
        - 前进(F)和停止(P/S)：不从摄像头发送，由UNO超声波自主控制
        """
        if not self.arduino or not self.arduino.is_open:
            return

        current_time = time.time()
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 第一步：确定当前帧的意图指令
        intended_cmd = None
        if x > 0:  # 前进
            if th > 0.1:
                intended_cmd = "L"  # 左转前进
            elif th < -0.1:
                intended_cmd = "R"  # 右转前进
            else:
                intended_cmd = "F"  # 直行前进
        elif x < 0:  # 后退（障碍物太近）
            intended_cmd = "B"
        elif x == 0:  # 原地
            if th > 0.1:
                intended_cmd = "L"
            elif th < -0.1:
                intended_cmd = "R"
            else:
                intended_cmd = "P"  # 暂停

        # 记录每帧的意图（调试用，不是每帧都打印）
        if self.frame_count % 20 == 0:  # 每秒打印一次
            logger.debug(
                f"[{timestamp_str}] x:{x:+.1f}, th:{th:+.2f} -> intent: {intended_cmd}"
            )

        # ===== 第二步：障碍物(B指令)防抖 —— 连续3秒才发送 =====
        if intended_cmd == "B":
            if self.obstacle_start_time is None:
                self.obstacle_start_time = current_time
                self.obstacle_sent = False
                logger.info(f"[{timestamp_str}] 开始检测到障碍物，等待确认...")

            elapsed = current_time - self.obstacle_start_time
            if not self.obstacle_sent and elapsed >= 3.0:
                # 连续3秒都是障碍物，确认发送B
                self._send_to_arduino("B", timestamp_str)
                self.obstacle_sent = True
                logger.info(f"[{timestamp_str}] ★ 障碍物确认(持续{elapsed:.1f}s)，已发送B指令")

            # 障碍物状态下，清除转向历史
            self.turn_history.clear()
            return
        else:
            # 不是障碍物，重置障碍物追踪
            if self.obstacle_start_time is not None:
                logger.info(f"[{timestamp_str}] 障碍物消失，重置追踪")
            self.obstacle_start_time = None
            self.obstacle_sent = False

        # ===== 第三步：转向(L/R指令)防抖 —— 3秒内连续5次同方向才发送 =====
        if intended_cmd in ("L", "R"):
            self.turn_history.append((intended_cmd, current_time))

            # 清除3秒之前的旧记录
            self.turn_history = [
                (c, t) for c, t in self.turn_history if current_time - t <= 3.0
            ]

            # 检查最近的记录中是否有连续5次同方向
            if len(self.turn_history) >= 5:
                # 取最后5条记录
                last_5_cmds = [c for c, t in self.turn_history[-5:]]
                if all(c == intended_cmd for c in last_5_cmds):
                    # 5次连续同方向，且距离上次发送间隔足够
                    if current_time - self.last_turn_sent_time >= 3.0:
                        self._send_to_arduino(intended_cmd, timestamp_str)
                        self.last_turn_sent_time = current_time
                        self.turn_history.clear()  # 发送后清空，重新积累
                        logger.info(
                            f"[{timestamp_str}] ★ 转向确认(5次{intended_cmd})，已发送{intended_cmd}指令"
                        )
            return

        # ===== 第四步：前进(F)和停止(P) —— 不发送，由UNO超声波自主控制 =====
        # 摄像头不发送F和P指令，避免与UNO的超声波检测逻辑冲突
        # UNO负责：前进、停止、超声波避障
        # 摄像头负责：视觉障碍物后退(B)、视觉转向辅助(L/R)
        if intended_cmd in ("F", "P"):
            # 前进/暂停状态下，清空转向历史（说明方向已恢复正常）
            if len(self.turn_history) > 0 and intended_cmd == "F":
                self.turn_history.clear()
            return

    def _send_to_arduino(self, cmd, timestamp_str=""):
        """底层发送指令到Arduino UNO（参考Eangel_server_thread_opt_UsbDEV.py的写法）
        全局节流：任何指令间隔不小于 MIN_CMD_INTERVAL(3秒)
        """
        # 全局3秒节流：距离上次发送不足3秒则跳过
        current_time = time.time()
        if (
            self.last_uno_cmd_time > 0
            and (current_time - self.last_uno_cmd_time) < self.MIN_CMD_INTERVAL
        ):
            logger.debug(
                f"[{timestamp_str}] 节流跳过 {cmd}，距上次发送仅{current_time - self.last_uno_cmd_time:.1f}s"
            )
            return
        try:
            # 发送前清空输入缓冲区，避免积压数据干扰
            self.arduino.flushInput()
            # 使用bytes直接发送，与参考文件 ser.write(b'B') 一致
            self.arduino.write(cmd.encode("utf-8"))
            self.last_uno_cmd = cmd
            self.last_uno_cmd_time = time.time()
            logger.info(f"[{timestamp_str}] >>> 发送到UNO: {cmd}")
        except Exception as e:
            logger.error(f"Serial write error: {e}")

    def cleanup(self):
        if self.rtsp_server:
            self.rtsp_server.stop()
            self.rtsp_server = None

        if self.arduino:
            self.arduino.close()
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        if self.pub_thread:
            self.pub_thread.stop()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = YOLOv8Node()
        # Wait for ROS subscribers (optional safety)
        # try:
        #     node.pub_thread.wait_for_subscribers()
        # except Exception:
        #     pass

        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if node:
            node.cleanup()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
