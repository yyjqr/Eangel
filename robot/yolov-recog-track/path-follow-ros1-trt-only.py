"""
YOLOv8 TensorRT Path Follow ROS 1 Node (No PyTorch/Ultralytics dependency)
Compatible with: Python 3.6, TensorRT 8.x, ROS Noetic/Melodic
"""
import rospy
from geometry_msgs.msg import Twist
import cv2
import numpy as np
import threading
import time
import os
import sys

# Try importing TensorRT
try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
except ImportError:
    print("Error: TensorRT or pycuda not installed.")
    print("pip install pycuda")
    sys.exit(1)

# Serial for Arduino (Optional)
try:
    import serial
except ImportError:
    serial = None

CONF_THRESH = 0.5
IOU_THRESHOLD = 0.45

# TensorRT Logger
TRT_LOGGER = trt.Logger(trt.Logger.INFO)


class YOLOv8TRT:
    def __init__(self, engine_file_path):
        self.cfx = cuda.Device(0).make_context()
        self.stream = cuda.Stream()

        # Load Engine
        with open(engine_file_path, "rb") as f:
            runtime = trt.Runtime(TRT_LOGGER)
            self.engine = runtime.deserialize_cuda_engine(f.read())

        self.context = self.engine.create_execution_context()

        # Setup Buffers
        self.inputs = []
        self.outputs = []
        self.bindings = []
        self.d_inputs = []
        self.d_outputs = []

        for binding in self.engine:
            size = trt.volume(self.engine.get_binding_shape(binding))
            dtype = trt.nptype(self.engine.get_binding_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)

            self.bindings.append(int(device_mem))

            if self.engine.binding_is_input(binding):
                self.inputs.append(host_mem)
                self.d_inputs.append(device_mem)
            else:
                self.outputs.append(host_mem)
                self.d_outputs.append(device_mem)

    def infer(self, img):
        self.cfx.push()

        # Preprocess
        input_img, ratio, dwdh = self.preprocess(img)

        # Copy to Host Buffer
        np.copyto(self.inputs[0], input_img.ravel())

        # Copy Host -> Device
        cuda.memcpy_htod_async(self.d_inputs[0], self.inputs[0], self.stream)

        # Inference
        self.context.execute_async_v2(
            bindings=self.bindings, stream_handle=self.stream.handle
        )

        # Copy Device -> Host
        cuda.memcpy_dtoh_async(self.outputs[0], self.d_outputs[0], self.stream)

        # Synchronize
        self.stream.synchronize()

        self.cfx.pop()

        # Postprocess
        output = self.outputs[0]
        # Reshape depending on model output. YOLOv8 usually outputs [1, 84, 8400]
        # Transpose to [8400, 84] for easier processing
        prediction = output.reshape(1, 84, -1)
        prediction = np.transpose(prediction[0], (1, 0))

        boxes, confidences, class_ids = self.postprocess(
            prediction, img.shape, ratio, dwdh
        )
        return boxes, confidences, class_ids

    def preprocess(self, img):
        # Resize/Letterbox to 640x640
        input_shape = (640, 640)
        img_h, img_w = img.shape[:2]
        scale = min(input_shape[0] / img_h, input_shape[1] / img_w)

        new_h, new_w = int(img_h * scale), int(img_w * scale)
        img_resized = cv2.resize(img, (new_w, new_h))

        dw, dh = input_shape[1] - new_w, input_shape[0] - new_h
        dw /= 2
        dh /= 2

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

        img_padded = cv2.copyMakeBorder(
            img_resized,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

        # Normalize
        input_img = img_padded.astype(np.float32) / 255.0
        input_img = input_img.transpose(2, 0, 1)  # HWC -> CHW
        input_img = np.expand_dims(input_img, axis=0)  # CHW -> NCHW
        input_img = np.ascontiguousarray(input_img)

        return input_img, scale, (dw, dh)

    def postprocess(self, prediction, img0_shape, ratio, dwdh):
        boxes = []
        confidences = []
        class_ids = []

        dw, dh = dwdh

        # prediction shape: [8400, 84] (xc, yc, w, h, class0_score, class1_score...)

        # Filter by confidence
        scores = np.max(prediction[:, 4:], axis=1)
        mask = scores > CONF_THRESH

        filtered_pred = prediction[mask]
        filtered_scores = scores[mask]
        filtered_class_ids = np.argmax(filtered_pred[:, 4:], axis=1)

        # Extract boxes
        filtered_boxes = filtered_pred[:, :4]

        # Rescale boxes to original image
        # Box format: xc, yc, w, h

        for i in range(len(filtered_boxes)):
            box = filtered_boxes[i]
            score = filtered_scores[i]
            cls_id = filtered_class_ids[i]

            # Restore to original image coordinates
            x = (box[0] - dw) / ratio
            y = (box[1] - dh) / ratio
            w = box[2] / ratio
            h = box[3] / ratio

            x1 = int(x - w / 2)
            y1 = int(y - h / 2)
            w = int(w)
            h = int(h)

            boxes.append([x1, y1, w, h])
            confidences.append(float(score))
            class_ids.append(int(cls_id))

        # NMS
        indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESH, IOU_THRESHOLD)

        final_boxes = []
        final_scores = []
        final_class_ids = []

        if len(indices) > 0:
            for i in indices.flatten():
                final_boxes.append(boxes[i])
                final_scores.append(confidences[i])
                final_class_ids.append(class_ids[i])

        return final_boxes, final_scores, final_class_ids

    def destroy(self):
        self.cfx.pop()


class PublishThread(threading.Thread):
    def __init__(self, publisher, rate):
        super(PublishThread, self).__init__()
        self.publisher = publisher
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
        while not self.done and not rospy.is_shutdown():
            with self.condition:
                self.condition.wait(self.timeout)
                twist.linear.x = float(self.x * self.speed)
                twist.linear.y = float(self.y * self.speed)
                twist.linear.z = float(self.z * self.speed)
                twist.angular.x = 0.0
                twist.angular.y = 0.0
                twist.angular.z = float(self.th * self.turn)

            self.publisher.publish(twist)

        # Stop
        twist.linear.x = 0.0
        self.publisher.publish(twist)


class YOLOv8TrackerTRT:
    def __init__(self):
        self.last_center = None
        self.last_img_width = 640

        # ROS Params
        self.speed_val = rospy.get_param("~speed", 0.5)
        self.turn_val = rospy.get_param("~turn", 1.0)
        repeat = rospy.get_param("~repeat_rate", 0.0)

        # Engine Path
        # Look for yolov8n.engine in current dir by default
        default_engine = os.path.join(os.getcwd(), "yolov8n.engine")
        self.engine_path = rospy.get_param("~engine_path", default_engine)

        if not os.path.exists(self.engine_path):
            rospy.logerr(f"Engine file not found: {self.engine_path}")
            rospy.logerr(
                "Please export it first using: yolo export model=yolov8n.pt format=engine"
            )
            sys.exit(1)

        # Initialize TRT
        try:
            rospy.loginfo(f"Loading TensorRT Engine: {self.engine_path}")
            self.model = YOLOv8TRT(self.engine_path)
            rospy.loginfo("TensorRT Engine Loaded Successfully")
        except Exception as e:
            rospy.logerr(f"Failed to load TensorRT engine: {e}")
            sys.exit(1)

        # Initialize Serial
        self.arduino = None
        if serial:
            port = rospy.get_param("~serial_port", "/dev/ttyACM0")
            baud = rospy.get_param("~baud_rate", 9600)
            try:
                self.arduino = serial.Serial(port, baud, timeout=0.1)
                rospy.loginfo(f"Connected to Arduino at {port}")
            except Exception as e:
                rospy.logwarn(f"Arduino connection failed: {e}")

        # Publisher
        self.cmd_vel_pub = rospy.Publisher("cmd_vel", Twist, queue_size=1)
        self.pub_thread = PublishThread(self.cmd_vel_pub, repeat)

        # Camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            rospy.logerr("Failed to open camera 0")
            sys.exit(1)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def process_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # Inference
        boxes, confs, class_ids = self.model.infer(frame)

        x, y, z, th = 0, 0, 0, 0
        target_found = False
        img_h, img_w = frame.shape[:2]
        self.last_img_width = img_w

        # Find best Person
        best_conf = 0.0
        best_box = None

        for i in range(len(boxes)):
            if class_ids[i] == 0:  # Person
                if confs[i] > best_conf:
                    best_conf = confs[i]
                    best_box = boxes[i]

        if best_box:
            target_found = True
            bx, by, bw, bh = best_box
            x1, y1 = bx, by
            x2, y2 = bx + bw, by + bh

            # Draw
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"Person {best_conf:.2f}",
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

            center = int(x1 + bw / 2)
            self.last_center = center

            right_thresh = int(img_w * 0.75)
            left_thresh = int(img_w * 0.25)

            cv2.line(frame, (left_thresh, 0), (left_thresh, img_h), (255, 0, 0), 1)
            cv2.line(frame, (right_thresh, 0), (right_thresh, img_h), (0, 0, 255), 1)

            if center >= right_thresh:
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

        # Lost Target Logic
        if not target_found:
            if self.last_center is not None:
                if self.last_center >= int(self.last_img_width / 2):
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
                x, y, z, th = 0, 0, 0, 0
                cv2.putText(
                    frame, "Stop", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2
                )

        # Show
        cv2.imshow("TRT v8", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.cleanup()
            rospy.signal_shutdown("User quit")
            return

        # Update ROS
        if self.pub_thread:
            if x != 0 or th != 0:
                print(f"Action: x={x}, th={th} \r", end="")
            self.pub_thread.update(
                float(x),
                float(y),
                float(z),
                float(th),
                float(self.speed_val),
                float(self.turn_val),
            )

        # Update Arduino
        self.send_arduino_command(x, th)

    def send_arduino_command(self, x, th):
        if self.arduino and self.arduino.is_open:
            cmd = "S"
            if x > 0:
                if th > 0.1:
                    cmd = "L"
                elif th < -0.1:
                    cmd = "R"
                else:
                    cmd = "F"
            elif x == 0:
                if th > 0.1:
                    cmd = "L"
                elif th < -0.1:
                    cmd = "R"
                else:
                    cmd = "S"
            try:
                self.arduino.write(f"{cmd}\n".encode())
            except Exception:
                pass

    def cleanup(self):
        if self.arduino:
            self.arduino.close()
        self.cap.release()
        cv2.destroyAllWindows()
        self.model.destroy()
        if self.pub_thread:
            self.pub_thread.stop()

    def run(self):
        rate = rospy.Rate(20)
        while not rospy.is_shutdown():
            self.process_frame()
            rate.sleep()


if __name__ == "__main__":
    rospy.init_node("yolov8_trt_node", anonymous=False)
    tracker = YOLOv8TrackerTRT()
    try:
        tracker.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    finally:
        tracker.cleanup()
