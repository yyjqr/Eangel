[![Build Status](https://travis-ci.org/yyjqr/Eangel.svg?branch=master)](https://travis-ci.org/yyjqr/Eangel)
# SE smart  robot
car_remote_app_control
基于树莓派，使用USB摄像头（Logitech系列），定时拍摄一定时长的视频或图片，然后发送邮件到某个邮箱。
采用c++开发，基于OpenCV C++模式的摄像头拍照或录制视频，而爬虫，邮件发送，是利用python脚本开发，很方便。
# 拍照或图像/视频传输
将摄像头拍摄的图片按照当时的时间存储下来，当然也可以把视频音频存储下来，然后再分析处理。基于socket,可通过实时显示拍摄的视频，或查看拍照的图片，来调整摄像头。(初步可采用mjpg-streamer)
<img width="741" alt="机器人图像传输控制逻辑_V1_202203" src="https://user-images.githubusercontent.com/26375374/157189279-26324d3b-3cec-40d8-967f-54ff0fc786da.png">
# 移动机器人控制
基于超声波和IMU，避障，获取车的姿态或振动等，再来控制机器人。另基于摄像头传输移动机器人画面，在线检测，图像处理来控制。在线识别检测基于yoloV4,yolo V5.
# 爬虫 
另把爬取的新闻，科技类附在邮件里。基于了BS4和XPATH,LXML等。

## C,C++编程重点研究
基于一些基本的代码研究数据类型，相关指针，内存问题。


