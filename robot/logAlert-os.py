#import necessary package
# encoding: utf-8
#coding:gb18030
#date :2020--->2022.2--->2022.7


import socket
import time
import sys,subprocess
import RPi.GPIO as GPIO
import serial
import logging    #20180318 JACK
import datetime

import device_info_check

#print("Starting socket: TCP...")
#1.create socket object:socket=socket.socket(family,type)
socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#print("TCP server listen @ %s:%d!" %(HOST_IP, HOST_PORT) )
#host_addr = (HOST_IP, HOST_PORT)
#GPIO.setup(11,GPIO.OUT)
#print("Receiving package...")

log_file ="%s%s%s"% ('./logs/syslog/EangelRaspi',datetime.date.today(),'.log')
logger = logging.getLogger(__name__)
logger.setLevel(level = logging.INFO)

handler = logging.FileHandler(log_file)  #"Eangel log.txt"
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)

logger.info("Start print log")
logger.info("Eangel raspi RUN>>>>>>>>>>>>>")
#logger.info("Arduino UNO  RUN>>>>>>>>>>>>>")
ArduinoState=True
DeviceName=""
DevicdInfo=""

def get_ip_address():
        s =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("1.1.1.1",80))
        ipaddr=s.getsockname()[0]
        s.close()
        return ipaddr
host_addr=get_ip_address()
print (host_addr)
logger.info(host_addr)
logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))   #20180318
logger.debug("Do something")
#logger.warning("Something maybe fail.")
#logger.info("Finish")

#logger.warning("Eangel error or Something maybe fail.")

def disk_stat(path):
    import os
    hd={}
    disk = os.statvfs(path)
    percent = (disk.f_blocks - disk.f_bfree) * 100 / (disk.f_blocks -disk.f_bfree + disk.f_bavail) + 1
    return percent
print ("disk space :%f" %disk_stat('.'))
#print ("disk space :%f" %disk_stat('/boot'))
    
def sendAlert():
    from datetime import datetime
    num =disk_stat('.')
    if (num> 90):
       print("设备存储过多")
       now_time = datetime.now()
       date=now_time.strftime('%Y-%m-%d_%H:%M:%S')
       print ('date:{0} device:{1}'.format(date,DeviceName))
       info= date+"\n设备信息：\n"+str(DeviceInfo)+"\n ip:"+host_addr+"\n 存储空间不足，目前使用"+str(num)
       #subprocess.Popen('~/sendAlert.sh', stdin = subprocess.PIPE, stdout=open("/dev/null","w"), stderr = subprocess.PIPE, shell = True)
       #device_info_check.get_device_log(info)
       device_info_check.mail(info,DeviceName)
def getDeviceCpuOrOsInfo():
     import platform   #导入platform模块
     global  DeviceName
     global   DeviceInfo
     print('操作系统名称：', platform.system()) #获取操作系统名称
     print('操作系统名称及版本号：', platform.platform()) #获取操作系统名称及版本号
     print('操作系统版本号：', platform.version()) #获取操作系统版本号
     print('操作系统的位数：', platform.architecture()) #获取操作系统的位数
     print('计算机类型：', platform.machine()) #计算机类型
     print('计算机的网络名称：', platform.node()) #计算机的网络名称
     print('计算机处理器信息：', platform.processor()) #计算机处理器信息
     print('包含上面所有的信息汇总：', platform.uname())#包含上面所有的信息汇总
     DeviceName =platform.node()
     DeviceInfo = platform.uname()
     print("test Device:", DeviceInfo)
getDeviceCpuOrOsInfo()

sendAlert()

