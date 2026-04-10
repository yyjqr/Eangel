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

        # State variables for logic (Last known position)
        self.last_center = None
        self.last_img_width = 640  # Default

        try:
            # Declare parameters
            self.declare_parameter("speed", 0.5)
            self.declare_parameter("turn", 1.0)
            self.declare_parameter("repeat_rate", 0.0)
            self.declare_parameter("serial_port", "/dev/ttyAMA0")
            self.declare_parameter("baud_rate", 9600)
            self.declare_parameter(
                "model_path", "yolov8n.pt"
            )  # Default to PT, uses engine if available
            self.declare_parameter("device", "0")  # CUDA device 0

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
            device_param = (
                self.get_parameter("device").get_parameter_value().string_value
            )

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
                    self.get_logger().info(f"Connected to Arduino at {port}")
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

            # Initialize Camera
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Failed to open USB camera (ID 0)")

            # Video settings
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Timer for loop
            self.timer = self.create_timer(0.05, self.process_frame)  # 20 Hz

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

                # Calculate Center
                center = int((x1 + x2) / 2)
                self.last_center = center

                # Control Logic
                right_thresh = int(img_w * 0.75)
                left_thresh = int(img_w * 0.25)

                # Draw Threshold lines
                cv2.line(frame, (left_thresh, 0), (left_thresh, img_h), (255, 0, 0), 1)
                cv2.line(
                    frame, (right_thresh, 0), (right_thresh, img_h), (0, 0, 255), 1
                )

                if center >= right_thresh:
                    # Previous logic: th = -1 (Turn Right)
                    x, y, z, th = 1, 0, 0, -1
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
                    # Previous logic: th = 1 (Turn Left)
                    x, y, z, th = 1, 0, 0, 1
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
                    # Go Straight
                    x, y, z, th = 1, 0, 0, 0
                    cv2.putText(
                        frame,
                        "Go Straight",
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

        # Print logic state for debugging without GUI
        # Only print if state changes or periodically to avoid spam
        # print(f"Cmd: x={x}, th={th}, Target: {target_found}")

        # Show Image
        cv2.imshow("YOLOv8 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.cleanup()
            rclpy.shutdown()
            return

        # Update ROS Publisher
        if self.pub_thread:
            # Debug log
            if x != 0 or th != 0:
                logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                print(
                    f"Action: x={x}, th={th}, Target Found: {target_found}   \r", end=""
                )

            self.pub_thread.update(
                float(x),
                float(y),
                float(z),
                float(th),
                float(self.speed_val),
                float(self.turn_val),
            )

        # Update Arduino (Optional)
        print(f"start to send  \n")
        self.send_arduino_command(x, th)

    def send_arduino_command(self, x, th):
        if self.arduino and self.arduino.is_open:
            cmd = "S"
            if x > 0:  # Moving forward
                if th > 0.1:  # Left
                    cmd = "L"
                elif th < -0.1:  # Right
                    cmd = "R"
                else:
                    cmd = "F"  # Forward
            elif x == 0:  # Stopped or Spot Turn
                if th > 0.1:
                    cmd = "L"  # Spot turn left
                elif th < -0.1:
                    cmd = "R"  # Spot turn right
                else:
                    cmd = "S"
            print(f"x:{x}, th:{th},cmd {cmd}\n")
            logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            try:
                self.arduino.write(f"{cmd}\n".encode())
            except Exception:
                pass

    def cleanup(self):
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
