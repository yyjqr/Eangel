### -*- coding: UTF-8 -*-
import socketserver
import socket
import cv2
import numpy as np
import threading

IMAGESIZE = 921600
IMAGEWIDTH = 640
IMAFEHEIGHT = 480
FRAMELENGTH = 1024

# 读取路径下的视频文件，以OpenCV打开
# 当然也可以打开摄像头
#filepath = 'VideoTest.mp4'
#cap = cv2.VideoCapture(filepath)
# 从摄像头采集图像
capture = cv2.VideoCapture(-1)
#ret, frame = capture.read()
# 创建服务器
server = socket.socket()
# 获取到本机IP
def get_ip_address():
        s =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("1.1.1.1",80))
        ipaddr=s.getsockname()[0]
        s.close()
        return ipaddr

#define host ip: Rpi's IP
HOST_IP=get_ip_address()
#PCname = socket.gethostname()
#IP = socket.gethostbyname(PCname)
print(HOST_IP)
# 设置IP和端口号
server.bind((HOST_IP, 8082))
server.listen(1)

print('connecting...')


# 多线程接收数据
# socket接收为阻塞接收方式，阻断程序运行
# 用多线程的方式来避免发生阻塞
class Receive_Thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.return_value = b'0'

    def run(self):
        while True:
            # 每次接收一个字节的数据
            self.return_value = cmd = conn.recv(1)

    # 返回接收到的数据
    def get_value(self):
        return self.return_value



while True:
    # 等待客户端连接
    # 阻塞方式，不连接不会执行下一步
    # conn为新创建的socket对象
    # 用于下边数据收发
    conn, addr = server.accept()
    print('收到请求')
    print('客户端地址', addr)
    # 创建数据接收线程
    rec_thread = Receive_Thread()
    rec_thread.start()
    while True:
        # 读取下一帧
        ret, frame = capture.read()
        # 数据类型为uint8
        framed = cv2.resize(frame, (IMAGEWIDTH, IMAFEHEIGHT))
        framed = cv2.cvtColor(framed, cv2.COLOR_BGR2RGB)
        has_sent = 0
        rec_data = rec_thread.get_value()
        # 打印接收到的控制指令
        if rec_data != b'0':
            print(rec_data)
        # 发送图片，每次发送1024字节
        while has_sent < IMAGESIZE:
            data_to_send = framed[has_sent: has_sent+FRAMELENGTH]
            conn.send(data_to_send)
            has_sent += FRAMELENGTH
        cv2.waitKey(100)
        cv2.imshow('jj', framed)
    break

cap.release()

#到这里完成了TCPserver的部分，接下来在Qt中完成TCPClient的部分

