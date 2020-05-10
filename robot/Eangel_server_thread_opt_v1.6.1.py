#import necessary package
# encoding: utf-8
##基于python3 采用线程，socket支持多客户端连接
# 202003  Jack   yyjqr789@sina.com
# 部分参考 https://www.cnblogs.com/liyang93/p/9117387.html
#codeing:gb18030
import socket
import time
import sys,subprocess
#import RPi.GPIO as GPIO
import serial
import logging    #20180318 JACK
import datetime
from threading import Thread #20190307 JACK

conn_list = []
conn_dt = {}


def get_ip_address():
        s =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("1.1.1.1",80))
        ipaddr=s.getsockname()[0]
        s.close()
        return ipaddr

#define host ip: Rpi's IP
#HOST_IP = "192.168.0.101"
HOST_IP=get_ip_address()
print (HOST_IP)
HOST_PORT = 6868

print("Starting socket: TCP...")
#1.create socket object:socket=socket.socket(family,type)
socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("TCP server listen @ %s:%d!" %(HOST_IP, HOST_PORT) )
host_addr = (HOST_IP, HOST_PORT)

#2.bind socket to addr:socket.bind(address)
socketTCP.bind(host_addr)
#3.listen connection request:socket.listen(backlog)
socketTCP.listen(5)
#4.waite for client:connection,address=socket.accept()
#socket_con, (client_ip, client_port) = socket_tcp.accept()
#print("Connection accepted from %s." %client_ip)
#socket_con.send("Welcome to RasPi TCP server!")

#5.handle
#GPIO.setmode(GPIO.BOARD)
#GPIO.setup(11,GPIO.OUT)
print("Receiving package...")


log_file ="%s%s%s"% ('EangelGo_new',datetime.date.today(),'.log')
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

logger.info("Eangel")
logger.info("Start print log")
logger.info(host_addr)
logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))   #20180318
logger.debug("Do something")
#logger.warning("Something maybe fail.")
#logger.info("logFinish")

#ser=serial.Serial("/dev/ttyUSB0",115200)

try:
    ser=serial.Serial("/dev/UNO",115200)  #try catch 0508
except serial.SerialException as e:
    #return None
    print("serial wrong")
   

def ReceiveDataThread(socket_tcp,address): 
    print ("Rev data....")
    while True:    #add 20200311!!!    
        try:
                #socket_tcp.settimeout(5)#500----->5s
                data=socket_tcp.recv(8192)
                #print ("Rev data ...")
                if len(data)>0:
                    print("Received:%s" %data ,address)  #%s--->%c 目前接受的是字符为主
#利用字节串的decode()方法将字节串解码成字符串（对象）
                    #print(data,type(data))
                    #data=data.decode()  #add  利用字符串的encode()方法将字符串编码成字节对象（bytes），默认使用utf-8字符集  0331
                    data=bytes.decode(data)
                    logger.info(data)
                    #print(data,type(data))
                            # "C" 20200301ADD            
                    if data=='C':
                       #os.system('~/home/pi/camCap/source/cam10min/camFS10m_opt')
                       subprocess.Popen('~/camCap/source/cam1min/camFS1min', shell = True, stdout = subprocess.PIPE)
                       print("Take picture 1min !")
                       logger.info("Take picture")
                    elif data=='M':
                       #subprocess.popen('mplayer /home/pi/Music/Soundtrack - Define Dancing.mp3')
                       subprocess.Popen(["mplayer", "-slave", "-quiet", "/home/pi/Music/Soundtrack - Define Dancing.mp3"], stdin = subprocess.PIPE, stdout=open("/dev/null","w"), stderr = subprocess.PIPE, shell = False)
                       print("Play music") 
                       time.sleep(1)
        # "Z" 20200307ADD    send Email        
                    elif data=='Z':
                       subprocess.Popen('~/sendDiffNews.sh', shell = True, stdout = subprocess.PIPE)
                       print("SEND Email------ !")
                       logger.info("SEND Email------ !")
                    

                    
                    elif data=='F':
                       # GPIO.output(11,GPIO.HIGH)
##TypeError: unicode strings are not supported, please encode to bytes: 'P'!!! 发送的字符，需要变成字节！！20200418
                       ser.write(str.encode('F'))
                       print("car go Forward")
                    elif data=='L':
                       # GPIO.output(11,GPIO.HIGH)
                       ser.write(str.encode('L'))
                       print("car turn left")

                    elif data=='R':
                       # GPIO.output(11,GPIO.LOW)
                       ser.write(str.encode('R'))
                       print("car turn Right")
                    elif data=='B':
                       ser.write(str.encode('B'))
                       print("car turn Back")
                    elif data=='P':
                       #ser.write('P')
                       ser.write(str.encode('P'))
                       print("car Pause")
                    elif data=='S':    #slow down  add 202003
                       ser.write(str.encode('S'))
                       print("car SLOW DOWN!")   

                    else:
                       ser.flushInput()
                       input=ser.read(1)
                       runtime=ord(input)
                       
                       print (" Robot running time is %d seconds ..."%runtime)  #20180625   
                    #continue
                    if not data:
                         print("RECEIVE WRONG!")
                         break
        except Exception as e:
                    print("出错了，错误类型是{}".format(type(e)))
                    socket_tcp.close()
                    print(address,'offline')
                    _index = conn_list.index(address)
                    #gui.listBox.delete(_index)
                    conn_dt.pop(address)
                    conn_list.pop(_index)
                    break
                    #sys.exit(1)

def accept_client():
    """
    接收新连接
    """
    while True:
        socket_tcp,address=socketTCP.accept()

        if socket_tcp not in conn_list:
        #client, _ = g_socket_server.accept()  # 阻塞，等待客户端连接
            conn_list.append(address)
            conn_dt[address] =socket_tcp
        print ("connect from: %s:%d" % (address[0],address[1]))

        # 加入连接池 20200307
        #g_conn_pool.append(client)
        # 给每个客户端创建一个独立的线程进行管理
        #thread = Thread(target=message_handle, args=(client,))
        thread=Thread(target=ReceiveDataThread,args=(socket_tcp,address))

        # 设置成守护线程
        #thread.setDaemon(True)
        thread.Daemon=True #add 0405
        thread.start()

if __name__ == '__main__':
    #init()
    # 新开一个线程，用于接收新连接
    thread = Thread(target=accept_client)
    #thread.setDaemon(True)
    thread.start()
    #thread.join()



