
#import necessary package
# encoding: utf-8
#codeing:gb18030
import socket
import time
import sys,subprocess
import RPi.GPIO as GPIO
import serial
import logging    #20180318 JACK
import datetime

#define host ip: Rpi's IP
#HOST_IP = "192.168.0.101"
HOST_PORT = 6868

def get_ip_address():
        s =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("1.1.1.1",80))
        ipaddr=s.getsockname()[0]
        s.close()
        return ipaddr
HOST_IP=get_ip_address()
print (HOST_IP)

print("Starting socket: TCP...")
#1.create socket object:socket=socket.socket(family,type)
socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("TCP server listen @ %s:%d!" %(HOST_IP, HOST_PORT) )
host_addr = (HOST_IP, HOST_PORT)

#2.bind socket to addr:socket.bind(address)
socket_tcp.bind(host_addr)
#3.listen connection request:socket.listen(backlog)
socket_tcp.listen(5)
#4.waite for client:connection,address=socket.accept()
socket_con, (client_ip, client_port) = socket_tcp.accept()
print("Connection accepted from %s." %client_ip)
socket_con.send("Welcome to RasPi TCP server!")
#5.handle
GPIO.setmode(GPIO.BOARD)
#GPIO.setup(11,GPIO.OUT)
print("Receiving package...")

#ser=serial.Serial("/dev/ttyUSB0",115200)
ser=serial.Serial("/dev/UNO",115200)
log_file ="%s%s%s"% ('EangelGoing',datetime.date.today(),'.log')
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
logger.info("Eangel")
logger.info(host_addr)
logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))   #20180318
logger.debug("Do something")
#logger.warning("Something maybe fail.")
logger.info("logFinish")
while True:
    try:
        data=socket_con.recv(8192)
        if len(data)>0:
            print("Received:%s"%data)
            logger.info(data)
            if  data=='F':
               # GPIO.output(11,GPIO.HIGH)
               ser.write('F')
               print("car go Forward")
            elif data=='L':
               # GPIO.output(11,GPIO.HIGH)
               ser.write('L')
               print("car turn left")

            elif data=='R':
               # GPIO.output(11,GPIO.LOW)
            #socket_con.send(data)
               ser.write('R')
               print("car turn Right")
            elif data=='B':
               ser.write('B')
               print("car turn Back")
            elif data=='P':
               ser.write('P')
               print("car Pause")
            elif data=='M':
               #subprocess.popen('mplayer /home/pi/Music/Soundtrack - Define Dancing.mp3')
               subprocess.Popen(["mplayer", "-slave", "-quiet", "/home/pi/Music/Soundtrack - Define Dancing.mp3"], stdin = subprocess.PIPE, stdout=open("/dev/null","w"), stderr = subprocess.PIPE, shell = False)
	       print("Play music") 
               time.sleep(1)
            else:
               ser.flushInput()
               input=ser.read(1)
               runtime=ord(input)
               
               print (" Robot running time is %d seconds ..."%runtime)  #20180625   
            continue
    except Exception:
            socket_tcp.close()
            sys.exit(1)
