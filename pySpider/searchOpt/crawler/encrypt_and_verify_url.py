## -*- coding: UTF-8 -*-
#@author: JACK YANG 
      # key 2022.11
# Email: yyjqr789@sina.com

#!/usr/bin/python3


import sys,os 
import base64

def encrypt_getKey(key):
    a = base64.b64encode(key)
    print(a) #  b'aGVsbG8gd29ybGQ='
 
    b = base64.b64decode(a)

    print(b) # b"hello world"

def decrypt_getKey(key):
    b = base64.b64decode(key)
    return b

def run_cmd_Popen_fileno(cmd_string):
    """
    执行cmd命令，并得到执行后的返回值，python调试界面输出返回值
    :return:
    """
    import subprocess
    
    print('运行cmd指令：{}'.format(cmd_string))
    pipe = subprocess.Popen(cmd_string, shell=True, stdout=None, stderr=None)
    print ("test popen")
    return pipe.communicate()
