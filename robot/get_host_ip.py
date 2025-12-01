#import necessary package
# encoding: utf-8
##基于python3 采用线程，socket支持多客户端连接
# 202412  Jack   yyjqr789@sina.com
# 部分参考 https://www.cnblogs.com/liyang93/p/9117387.html
#codeing:gb18030

import socket
import netifaces

def get_wifi_ip():
    # 获取所有网络接口
    interfaces = netifaces.interfaces()
    
    for interface in interfaces:
        # 只处理无线接口，通常是以'wl'或'wlan'开头的接口名
        if interface.startswith('wl') or interface.startswith('wlan'):
            # 获取接口的地址信息
            addrs = netifaces.ifaddresses(interface)
            # 检查是否有IPv4地址
            if netifaces.AF_INET in addrs:
                ip_info = addrs[netifaces.AF_INET][0]
                return ip_info['addr']
    
    return None

if __name__ == "__main__":
    wifi_ip = get_wifi_ip()
    if wifi_ip:
        print(f"本地WiFi IP地址: {wifi_ip}")
    else:
        print("未找到WiFi IP地址")
