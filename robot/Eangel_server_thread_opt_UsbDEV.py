#import necessary package
# encoding: utf-8
##基于python3 采用线程，socket支持多客户端连接
#  Jack   yyjqr789@sina.com
#202003-05 
#2024.12 opt process
# 部分参考 https://www.cnblogs.com/liyang93/p/9117387.html
#codeing:gb18030
import socket
import time
import sys
import subprocess
import serial
import logging
import datetime
from threading import Thread
import get_host_ip
# Global variables
conn_list = []
conn_dt = {}

def get_ip_address():
    """Get the local IP address of the device."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

def get_ip_address_opt():
    """Get the active local IP address of the device."""
    # Get the default gateway interface
    gateways = netifaces.gateways()
    default_interface = gateways['default'].get(netifaces.AF_INET, [None])[0]

    if default_interface is not None:
        # Get the IP address associated with the default interface
        iface_info = netifaces.ifaddresses(default_interface)
        ip_info = iface_info.get(netifaces.AF_INET)
        
        if ip_info:
            return ip_info[0]['addr']
    
    return None  # Return None if no active IP address is found

# Define host IP and port
#HOST_IP = get_ip_address_opt()
HOST_IP = get_host_ip.get_wifi_ip()
HOST_PORT = 6868

print(f"Starting socket: TCP on {HOST_IP}:{HOST_PORT}...")

# Create and bind the TCP socket
socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socketTCP.bind((HOST_IP, HOST_PORT))
socketTCP.listen(5)

# Initialize logging
log_file = f"EangelGo_new{datetime.date.today()}.log"
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler(log_file)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(console)

logger.info("Eangel")
logger.info("Start print log")
logger.info((HOST_IP, HOST_PORT))
logger.info(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Initialize serial connection
try:
    ser = serial.Serial("/dev/UNO", 115200)
except serial.SerialException:
    print("Serial connection failed.")
    logger.warning("UNO Client connection may have failed.")

def receive_data_thread(socket_tcp, address):
    """Thread to handle data reception from clients."""
    print("Receiving data...")
    while True:
        try:
            data = socket_tcp.recv(8192)
            if data:
                data = data.decode()  # Decode bytes to string
                print(f"Received: {data}")

                # Handle commands
                handle_command(data)
            else:
                print("No data received, closing connection.")
                break
        except Exception as e:
            logger.error(f"Error: {e}")
            socket_tcp.close()
            print(f"{address} offline")
            conn_list.remove(address)
            del conn_dt[address]
            break

def handle_command(data):
    """Process received commands."""
    commands = {
        'C': lambda: subprocess.Popen('~/camCap/source/cam1min/camFS1min', shell=True, stdout=subprocess.PIPE),
        'M': lambda: subprocess.Popen('~/playMusic.sh', stdin=subprocess.PIPE, stdout=open("/dev/null", "w"), stderr=subprocess.PIPE, shell=True),
        'Z': lambda: subprocess.Popen('~/sendDiffNews.sh', shell=True, stdout=subprocess.PIPE),
        'F': lambda: ser.write(b'F'),
        'L': lambda: ser.write(b'L'),
        'R': lambda: ser.write(b'R'),
        'B': lambda: ser.write(b'B'),
        'P': lambda: ser.write(b'P'),
        'S': lambda: (ser.flushInput(), ser.write(b'S')),
    }

    if data in commands:
        commands[data]()
        print(f"Executed command: {data}")
        logger.info(f"Executed command: {data}")
    else:
        ser.flushInput()
        input_byte = ser.read(1)
        runtime = ord(input_byte)
        print(f"Robot running time is {runtime} seconds...")

def accept_client():
    """Accept new client connections."""
    while True:
        socket_tcp, address = socketTCP.accept()
        if socket_tcp not in conn_list:
            conn_list.append(address)
            conn_dt[address] = socket_tcp
            print(f"Connected from: {address[0]}:{address[1]}")

            thread = Thread(target=receive_data_thread, args=(socket_tcp, address))
            thread.daemon = True
            thread.start()

if __name__ == '__main__':
    # Start the client acceptance thread
    # 新开一个线程，用于接收新连接
    thread = Thread(target=accept_client)
    thread.start()

