[![Build Status](https://travis-ci.org/yyjqr/Eangel.svg?branch=master)](https://travis-ci.org/yyjqr/Eangel)
# SE smart  robot
car_remote_app_control
基于树莓派，使用USB摄像头（Logitech系列），定时拍摄一定时长的视频或图片，然后发送邮件到某个邮箱。
采用c++开发，基于OpenCV C++模式的摄像头拍照或录制视频,而爬虫，邮件发送，是利用python脚本开发，很方便。
# 拍照或视频录制
将摄像头拍摄的图片按照当时的时间存储下来，当然也可以把视频音频存储下来，然后再分析处理。
# 爬虫 
另把爬取的新闻，科技类附在邮件里。基于了BS4和XPATH,LXML等。
