#!/usr/python
#-*- coding:utf-8 -*-
#coding gb18030
import paramiko

def parmiko_con(execmd):
    #实例化一个ssh

	ssh = paramiko.SSHClient() 
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
	IP="192.168.30.125"
	port=22
	username="pi"
	password="hello123"
	ssh.connect(IP, port,username, password) 
	
	stdin, stdout, stderr = ssh.exec_command (execmd) 
	print(stdout.readlines())

if __name__ == '__main__':
    parmiko_con("ls -alh")
    parmiko_con("date")
    parmiko_con("df -h")
    print('ok')
