#拼接字符串并换行## -*- coding: UTF-8 -*-
#!/usr/bin/python3.5
#@author: JACK YANG 201902-->06  yyjqr789@sina.com

import smtplib
#from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage  #20180603add JACK
from email.header import Header
import ssl
import sys,os  #os.listdir 201902
import importlib
#importlib.reload(sys)   #python2------->python3  弃用下面的方式！
#reload(sys)
import time
import glob  #查找通配文件 201902

from email.utils import formataddr
import neteaseSpiderV2 #0207--->0629
from lxml.html import etree
from lxml.html.clean import Cleaner #html cleaner 0415
import RPi.GPIO as GPIO


my_sender='xxx@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='xxx@xxx.com'
#receiver=my_sender
#_pwd = "xxx"  #0603
#_user = "你的qq邮箱"
_pwd = "xxx"   #需在qq邮箱开启SMTP服务并获取授权码20180505
GPIO.setwarnings(False)
pin0=11
pin1=13
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin0,GPIO.OUT)
GPIO.setup(pin1,GPIO.OUT)



def make_txt_msg(fn):
    #msg = MIMEMultipart('alternative')
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
    print("attach text")
    #txt=MIMEText(data,name=fn)
    txt=MIMEText(data,'plain','utf-8')
    #image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    txt.add_header('Content-ID','Spider2019')  #发送的图片附件名称 0603
    return txt


def make_img_msg(fn):
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
    image=MIMEImage(data,name=fn.split("/")[2])  #以/分隔目录文件/tmp/xxx.jpg，只要后面的文件名 20190222！
    #image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    image.add_header('Content-ID','EangelCam2019')  #发送的图片附件名称 0603
    #msg.attach(image)
    return image

def get_file_list(file_path):
    #dir_list = os.listdir(file_path)
    #print ('"%s"\n' %dir )
    dir_list=glob.glob("/tmp/*.jpg")
    print (dir_list)
    if not dir_list:
        return
    else:
        # 注意，这里使用lambda表达式，将文件按照最后修改时间顺序升序排列
        # os.path.getctime() 函数是获取文件最后创建时间
        dir_list = sorted(dir_list,  key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        # print(dir_list)
        return dir_list

def net_spiderNews():
    print("网易新闻排行榜爬取spidering")
    start_url = "http://news.163.com/rank/"
    spider=neteaseSpiderV2.Spider(start_url)


def parseHtml(file):
    print("解析HTML")
    html = etree.HTML(file)
    tag3 = html.xpath('/html/tr/td[1]/text()')
    print (tag3) 

def filterHtml(file):
    #html = requests.get(url, headers=headers).content
#清除不必要的标签
    #html=file
    html=etree.HTML(file)
    cleaner = Cleaner(style = True,scripts=True,comments=True,javascript=True,page_structure=False,safe_attrs_only=False)

    content = cleaner.clean_html(html)
#这里打印出来的结果会将上面过滤的标签去掉，但是未过滤的标签任然存在。
    print (content)
    return content

def parseNews(file):
    print("解析新闻爬取spidering")
    #new_page_info = re.findall(r'<td class=".*?">.*?<a href="(.*?)\.html.*?>(.*?)</a></td>',new_page,re.S)
    # 假设content为已经拿到的html
    fr = open(file)   #add 0404
    content = fr.read() 
    blocksWidth = 3
    # 每一个Cblock的长度
    Ctext_len = []
    # Ctext
    lines = content.split('n')
    # 去空格
    for i in range(len(lines)):
    	if lines[i] == ' ' or lines[i] == 'n':
    		lines[i] = ''
    # 计算纵坐标，每一个Ctext的长度
    for i in range(0, len(lines) - blocksWidth):
    	wordsNum = 0
    	for j in range(i, i + blocksWidth):
    		lines[j] = lines[j].replace("\s", "")
    		wordsNum += len(lines[j])
    	Ctext_len.append(wordsNum)


def mail():
  ret=True
  try:
    msg = MIMEMultipart('alternative')
 #获取文件路径
 
    #txtFile=make_txt_msg('/home/pi/Documents/news网易新闻抓取/科技.txt')
    num=int(time.time())
    print (num%4) 
    if (num%4) == 0:
        file='/home/pi/news网易新闻抓取/科技.txt'
    elif (num%4) == 1:
        file='/home/pi/news网易新闻抓取/财经.txt'
    elif (num%4) == 2:
        file='/home/pi/news网易新闻抓取/新闻.txt'
    else:
        file='/home/pi/news网易新闻抓取/教育.txt'
    print (file)
    txtFile=make_txt_msg(file)
    msg.attach(txtFile)   #添加附件
    #part_attach1 = MIMEApplication(open(file,'rb').read()) #打开附件

    path = '/tmp'         # 替换为你的路径
    dir = os.listdir(path)                  # dir是目录下的全部文件
    listN=get_file_list(path)
    #print (listN)
    imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
    print('Send IMG is "%s" ' %imgPath)
    
    
    msg.attach(make_img_msg(imgPath))
    #msg.attach(make_img_msg('/home/pi/EangelCam2019.jpg'))    #  single ''!!! 0603
    msg['From']=formataddr(["Eangel Robot Ⅱ",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的玩家",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="SE3 Cam 2019" #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
    server.login(my_sender,_pwd)  #括号中对应的是发件人邮箱账号、邮箱密码
    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND IMG OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False  python2---->python3 (as e) 201903
    print (str(e))
    ret=False
  return ret

  #if ret:
 # print 'ok' #如果发送成功则会返回ok，稍等20秒左右就可以收到邮件
  #GPIO.output(pin0,GPIO.HIGH)
   #time.sleep(10)
   #GPIO.output(pin0,GPIO.LOW)
 #else:
   #print 'send failed' #如果发送失败则会返回failed
   #GPIO.output(pin1,GPIO.HIGH)

if __name__ == '__main__':
  net_spiderNews()  
  mail()
        
