"""
An example that uses TensorRT's Python api to make inferences.
"""

from __future__ import print_function
import threading

# ROS 2 imports
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import sys, select, termios, tty

import ctypes
import os
import random
import sys
import threading
import time

import cv2
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
import tensorrt as trt

# import torch       <-- Removed dependency
# import torchvision <-- Removed dependency
try:
    import serial
except ImportError:
    serial = None

# COCO Categories
categories = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]

INPUT_W = 608
INPUT_H = 608
CONF_THRESH = 0.25
IOU_THRESHOLD = 0.45
msg = ""
x = 0
y = 0
z = 0
th = 0
status = 0
int_box = [0, 0, 0, 0]


def plot_one_box(x, img, color=None, label=None, line_thickness=None):
    """
    description: Plots one bounding box on image img,
                 this function comes from YoLov5 project.
    param:
        x:      a box likes [x1,y1,x2,y2]
        img:    a opencv image object
        color:  color to draw rectangle, such as (0,255,0)
        label:  str
        line_thickness: int
    return:
        no return
    """
    tl = (
        line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1
    )  # line/font thickness
    color = color or [random.randint(0, 255) for _ in range(3)]
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(
            img,
            label,
            (c1[0], c1[1] - 2),
            0,
            tl / 3,
            [225, 255, 255],
            thickness=tf,
            lineType=cv2.LINE_AA,
        )


class YoLov5TRT(object):
    """
    description: A YOLOv5 class that warps TensorRT ops, preprocess and postprocess ops.
    """

    def __init__(self, engine_file_path):
        # Create a Context on this device,
        self.cfx = cuda.Device(0).make_context()
        stream = cuda.Stream()
        TRT_LOGGER = trt.Logger(trt.Logger.INFO)
        runtime = trt.Runtime(TRT_LOGGER)

        # Deserialize the engine from file
        with open(engine_file_path, "rb") as f:
            engine = runtime.deserialize_cuda_engine(f.read())
        context = engine.create_execution_context()

        host_inputs = []
        cuda_inputs = []
        host_outputs = []
        cuda_outputs = []
        bindings = []

        for i in range(engine.num_io_tensors):
            name = engine.get_tensor_name(i)
            shape = engine.get_tensor_shape(name)
            size = trt.volume(shape)
            dtype = trt.nptype(engine.get_tensor_dtype(name))

            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            cuda_mem = cuda.mem_alloc(host_mem.nbytes)
            # Append the device buffer to device bindings.
            bindings.append(int(cuda_mem))
            # Append to the appropriate list.
            if engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                host_inputs.append(host_mem)
                cuda_inputs.append(cuda_mem)
            else:
                host_outputs.append(host_mem)
                cuda_outputs.append(cuda_mem)

        # Store
        self.stream = stream
        self.context = context
        self.engine = engine
        self.host_inputs = host_inputs
        self.cuda_inputs = cuda_inputs
        self.host_outputs = host_outputs
        self.cuda_outputs = cuda_outputs
        self.bindings = bindings

    def infer(self, input_image_path):
        # threading.Thread.__init__(self)
        # Make self the active context, pushing it on top of the context stack.
        global int_box, x, y, z, th
        self.cfx.push()
        # Restore
        stream = self.stream
        context = self.context
        engine = self.engine
        host_inputs = self.host_inputs
        cuda_inputs = self.cuda_inputs
        host_outputs = self.host_outputs
        cuda_outputs = self.cuda_outputs
        bindings = self.bindings
        # Do image preprocess
        input_image, image_raw, origin_h, origin_w = self.preprocess_image(
            input_image_path
        )
        # Copy input image to host buffer
        np.copyto(host_inputs[0], input_image.ravel())
        # Transfer input data  to the GPU.
        cuda.memcpy_htod_async(cuda_inputs[0], host_inputs[0], stream)
        # Run inference.
        context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)
        # Transfer predictions back from the GPU.
        cuda.memcpy_dtoh_async(host_outputs[0], cuda_outputs[0], stream)
        # Synchronize the stream
        stream.synchronize()
        # Remove any context from the top of the context stack, deactivating it.
        self.cfx.pop()
        # Here we use the first row of output in that batch_size = 1
        output = host_outputs[0]
        # Do postprocess
        result_boxes, result_scores, result_classid = self.post_process(
            output, origin_h, origin_w
        )
        if 0 in result_classid:
            for i in range(len(result_boxes)):
                box = result_boxes[i]
                if int(result_classid[i]) == 0 and result_scores[i] >= 0.5:
                    int_box = list(map(int, box))
                    center = int((int_box[0] + int_box[2]) / 2)
                    print("center:", center)
                    print("result:", 1)

                    # 使用相对坐标而不是绝对坐标
                    right_thresh = int(origin_w * 0.75)
                    left_thresh = int(origin_w * 0.25)

                    if center >= right_thresh:
                        print("right")
                        x, y, z, th = 1, 0, 0, -1
                        pass
                    elif center <= left_thresh:
                        print("left")
                        x, y, z, th = 1, 0, 0, 1
                        pass
                    else:
                        print("go")
                        x, y, z, th = 1, 0, 0, 0
                    plot_one_box(
                        box,
                        image_raw,
                        label="{}:{:.2f}".format(
                            categories[int(result_classid[i])], result_scores[i]
                        ),
                    )
                else:
                    int_box = int_box
                    pass
            return image_raw
        else:
            prebox = int_box
            precenter = int((prebox[0] + prebox[2]) / 2)
            print("result:", 2)
            if int_box != [0, 0, 0, 0]:
                mid_point = int(origin_w / 2)
                if precenter >= mid_point:
                    print("turn right")
                    x, y, z, th = 0, 0, 0, -1
                else:
                    print("turn left")
                    x, y, z, th = 0, 0, 0, 1
            else:
                print("stop!")
                x, y, z, th = 0, 0, 0, 0
            print("precenter", precenter)
            return input_image_path

    def destroy(self):
        # Remove any context from the top of the context stack, deactivating it.
        self.cfx.pop()

    def preprocess_image(self, input_image_path):
        """
        description: Read an image from image path, convert it to RGB,
                     resize and pad it to target size, normalize to [0,1],
                     transform to NCHW format.
        param:
            input_image_path: str, image path
        return:
            image:  the processed image
            image_raw: the original image
            h: original height
            w: original width
        """
        image_raw = input_image_path
        h, w, c = image_raw.shape
        image = cv2.cvtColor(image_raw, cv2.COLOR_BGR2RGB)
        # Calculate widht and height and paddings
        r_w = INPUT_W / w
        r_h = INPUT_H / h
        if r_h > r_w:
            tw = INPUT_W
            th = int(r_w * h)
            tx1 = tx2 = 0
            ty1 = int((INPUT_H - th) / 2)
            ty2 = INPUT_H - th - ty1
        else:
            tw = int(r_h * w)
            th = INPUT_H
            tx1 = int((INPUT_W - tw) / 2)
            tx2 = INPUT_W - tw - tx1
            ty1 = ty2 = 0
        # Resize the image with long side while maintaining ratio
        image = cv2.resize(image, (tw, th))
        # Pad the short side with (128,128,128)
        image = cv2.copyMakeBorder(
            image, ty1, ty2, tx1, tx2, cv2.BORDER_CONSTANT, (128, 128, 128)
        )
        image = image.astype(np.float32)
        # Normalize to [0,1]
        image /= 255.0
        # HWC to CHW format:
        image = np.transpose(image, [2, 0, 1])
        # CHW to NCHW format
        image = np.expand_dims(image, axis=0)
        # Convert the image to row-major order, also known as "C order":
        image = np.ascontiguousarray(image)
        return image, image_raw, h, w

    def xywh2xyxy(self, origin_h, origin_w, x):
        """
        description:    Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
        param:
            origin_h:   height of original image
            origin_w:   width of original image
            x:          A boxes tensor, each row is a box [center_x, center_y, w, h]
        return:
            y:          A boxes tensor, each row is a box [x1, y1, x2, y2]
        """
        y = np.zeros_like(x)
        r_w = INPUT_W / origin_w
        r_h = INPUT_H / origin_h
        if r_h > r_w:
            y[:, 0] = x[:, 0] - x[:, 2] / 2
            y[:, 2] = x[:, 0] + x[:, 2] / 2
            y[:, 1] = x[:, 1] - x[:, 3] / 2 - (INPUT_H - r_w * origin_h) / 2
            y[:, 3] = x[:, 1] + x[:, 3] / 2 - (INPUT_H - r_w * origin_h) / 2
            y /= r_w
        else:
            y[:, 0] = x[:, 0] - x[:, 2] / 2 - (INPUT_W - r_h * origin_w) / 2
            y[:, 2] = x[:, 0] + x[:, 2] / 2 - (INPUT_W - r_h * origin_w) / 2
            y[:, 1] = x[:, 1] - x[:, 3] / 2
            y[:, 3] = x[:, 1] + x[:, 3] / 2
            y /= r_h

        return y

    def post_process(self, output, origin_h, origin_w):
        """
        description: postprocess the prediction
        param:
            output:     A tensor likes [num_boxes,cx,cy,w,h,conf,cls_id, cx,cy,w,h,conf,cls_id, ...]
            origin_h:   height of original image
            origin_w:   width of original image
        return:
            result_boxes: finally boxes, a boxes tensor, each row is a box [x1, y1, x2, y2]
            result_scores: finally scores, a tensor, each element is the score correspoing to box
            result_classid: finally classid, a tensor, each element is the classid correspoing to box
        """
        # Get the num of boxes detected
        num = int(output[0])
        # Reshape to a two dimentional ndarray
        pred = np.reshape(output[1:], (-1, 6))[:num, :]

        # Get the boxes
        boxes = pred[:, :4]
        # Get the scores
        scores = pred[:, 4]
        # Get the classid
        classid = pred[:, 5]
        # Choose those boxes that score > CONF_THRESH
        si = scores > CONF_THRESH
        boxes = boxes[si, :]
        scores = scores[si]
        classid = classid[si]

        # Transform bbox from [center_x, center_y, w, h] to [x1, y1, x2, y2]
        boxes = self.xywh2xyxy(origin_h, origin_w, boxes)

        if len(boxes) == 0:
            return np.array([]), np.array([]), np.array([])

        # Do nms using OpenCV (avoids torch dependency)
        # NMSBoxes needs [x, y, w, h] (top-left, width, height)
        # Our boxes are [x1, y1, x2, y2]

        # Convert for cv2.dnn.NMSBoxes
        w = boxes[:, 2] - boxes[:, 0]
        h = boxes[:, 3] - boxes[:, 1]
        x_tl = boxes[:, 0]
        y_tl = boxes[:, 1]

        boxes_list = []
        for i in range(len(boxes)):
            boxes_list.append([int(x_tl[i]), int(y_tl[i]), int(w[i]), int(h[i])])

        indices = cv2.dnn.NMSBoxes(
            boxes_list, scores.tolist(), CONF_THRESH, IOU_THRESHOLD
        )

        if len(indices) > 0:
            indices = indices.flatten()
            result_boxes = boxes[indices, :]
            result_scores = scores[indices]
            result_classid = classid[indices]
        else:
            result_boxes = np.array([])
            result_scores = np.array([])
            result_classid = np.array([])

        return result_boxes, result_scores, result_classid


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

        # Set timeout to None if rate is 0 (causes new_message to wait forever
        # for new data to publish)
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
        self.condition.acquire()
        self.x = x
        self.y = y
        self.z = z
        self.th = th
        self.speed = speed
        self.turn = turn
        # Notify publish thread that we have a new message.
        self.condition.notify()
        self.condition.release()

    def stop(self):
        self.done = True
        self.update(0, 0, 0, 0, 0, 0)
        self.join()

    def run(self):
        twist = Twist()
        while not self.done and rclpy.ok():
            self.condition.acquire()
            # Wait for a new message or timeout.
            self.condition.wait(self.timeout)

            # Copy state into twist message.
            twist.linear.x = self.x * self.speed
            twist.linear.y = self.y * self.speed
            twist.linear.z = self.z * self.speed
            twist.angular.x = 0.0
            twist.angular.y = 0.0
            twist.angular.z = self.th * self.turn

            self.condition.release()

            # Publish.
            self.publisher.publish(twist)

        # Publish stop message when thread exits.
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.publisher.publish(twist)


class YOLOv5Node(Node):
    def __init__(self):
        super().__init__("yolov5_node")
        self.pub_thread = None
        self.yolov5_wrapper = None
        self.cap = None
        self.vid_writer = None

        try:
            # 声明参数
            self.declare_parameter("speed", 0.5)
            self.declare_parameter("turn", 1.0)
            self.declare_parameter("repeat_rate", 0.0)
            self.declare_parameter("serial_port", "/dev/ttyACM0")
            self.declare_parameter("baud_rate", 9600)

            # 获取参数
            speed = self.get_parameter("speed").get_parameter_value().double_value
            turn = self.get_parameter("turn").get_parameter_value().double_value
            repeat = (
                self.get_parameter("repeat_rate").get_parameter_value().double_value
            )

            # 初始化串口
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

            # 创建发布者线程
            self.pub_thread = PublishThread(self, repeat)

            # 检查引擎文件是否存在
            PLUGIN_LIBRARY = "build/libmyplugins.so"
            engine_file_path = "build/yolov5s.engine"

            if not os.path.exists(engine_file_path):
                raise Exception(f"Engine file not found: {engine_file_path}")

            # 加载插件库
            try:
                ctypes.CDLL(PLUGIN_LIBRARY)
            except Exception as e:
                self.get_logger().warn(f"Failed to load plugin library: {e}")

            # 创建 YoLov5TRT 实例
            self.yolov5_wrapper = YoLov5TRT(engine_file_path)

            # 检查引擎是否成功加载
            if self.yolov5_wrapper.engine is None:
                raise Exception("Failed to load TensorRT engine")

            # 设置视频捕获
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Failed to open camera")

            # 设置视频写入器
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            save_path = "save/video_out.avi"

            # 创建保存目录（如果不存在）
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            self.vid_writer = cv2.VideoWriter(save_path, fourcc, fps, (w, h))

            # 创建定时器
            self.timer = self.create_timer(0.1, self.process_frame)

            self.get_logger().info("YOLOv5 node initialized successfully")

        except Exception as e:
            self.get_logger().error(f"Failed to initialize node: {e}")
            # 清理已分配的资源
            self.cleanup()
            raise  # 重新抛出异常

    def process_frame(self):
        global x, y, z, th

        ret, image = self.cap.read()
        if not ret:
            self.get_logger().error("Failed to capture image")
            return

        img = self.yolov5_wrapper.infer(image)
        cv2.imshow("result", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):  # 1 millisecond
            self.cleanup()
            rclpy.shutdown()
            return

        self.pub_thread.update(
            x,
            y,
            z,
            th,
            self.get_parameter("speed").get_parameter_value().double_value,
            self.get_parameter("turn").get_parameter_value().double_value,
        )

        # Send command to Arduino
        if self.arduino and self.arduino.is_open:
            cmd = "S"
            if x > 0:
                if th > 0.1:  # Left
                    cmd = "L"
                elif th < -0.1:  # Right
                    cmd = "R"
                else:
                    cmd = "F"
            elif x == 0:
                if th > 0.1:
                    cmd = "L"  # Spot turn left
                elif th < -0.1:
                    cmd = "R"  # Spot turn right
                else:
                    cmd = "S"

            try:
                self.arduino.write(f"{cmd}\n".encode())
            except Exception as e:
                self.get_logger().warn(f"Serial error: {e}")

    def cleanup(self):
        if self.arduino:
            self.arduino.close()
        self.cap.release()
        self.vid_writer.release()
        cv2.destroyAllWindows()
        self.yolov5_wrapper.destroy()
        self.pub_thread.stop()


def main(args=None):
    rclpy.init(args=args)
    node = None

    try:
        # 创建节点
        print("create YOLOv5Node++++++")
        node = YOLOv5Node()

        # 等待订阅者
        try:
            node.pub_thread.wait_for_subscribers()
        except Exception as e:
            node.get_logger().warn(f"Waiting for subscribers failed: {e}")

        # 打印启动信息
        node.get_logger().info("YOLOv5 TensorRT node started")
        speed = node.get_parameter("speed").get_parameter_value().double_value
        turn = node.get_parameter("turn").get_parameter_value().double_value
        node.get_logger().info(vels(speed, turn))

        # 运行节点
        rclpy.spin(node)

    except KeyboardInterrupt:
        node.get_logger().info("Node stopped by user")
    except Exception as e:
        if node is not None:
            node.get_logger().error(f"Error: {e}")
        else:
            print(f"Error during node initialization: {e}")
    finally:
        # 清理资源
        try:
            if node is not None:
                node.cleanup()
                node.destroy_node()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            rclpy.shutdown()


def vels(speed, turn):
    return "currently:\tspeed %s\tturn %s " % (speed, turn)


if __name__ == "__main__":
    main()
