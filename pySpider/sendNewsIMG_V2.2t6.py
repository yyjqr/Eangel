#拼接字符串并换行## -*- coding: UTF-8 -*-
#@author: JACK YANG 201902-->07  yyjqr789@sina.com
#!/usr/bin/python3.5
import smtplib
#from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage  #20180603add JACK
from email.header import Header
import ssl
import sys,os  #os.listdir 201902
#sys.setdefaultencoding('utf-8')
import time
from datetime import datetime
import glob  #查找通配文件 201902

from email.utils import formataddr


import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
#import pandas
import codecs # use for write a file 0708

#import RPi.GPIO as GPIO

my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='yyjqr789@sina.com' #收件人邮箱账号，为了后面易于维护，所以写成了变量
#receiver=my_sender
_pwd = "tfqlcytviyqdbcib"  #0603
#_user = "你的qq邮箱"
#_pwd  = "cppfdkkotkehbdjj"   #需在qq邮箱开启SMTP服务并获取授权码20180505
#my_user='jiangza@tonglunpaipai.com'
pin0=11
pin1=13
#GPIO.setwarnings(False)
#GPIO.setmode(GPIO.BOARD)
#GPIO.setup(pin0,GPIO.OUT)
#GPIO.setup(pin1,GPIO.OUT)

def make_img_msg(fn):
    #msg = MIMEMultipart('alternative')
    
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
        # os.path.getmtime() 函数是获取文件最后修改时间
        # os.path.getctime() 函数是获取文件最后创建时间
        dir_list = sorted(dir_list,  key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        # print(dir_list)
        return dir_list

class GrabNews():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://techcrunch.com/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        #newsTitle = soup.find(text="信息公开")
        #newsList = newsTitle.parent.next_sibling.next_sibling.find_all('a')
        #for news in newsList:
            #for string in news.stripped_strings:
                #newsUrl = 'http://eis.whu.edu.cn/' + news['href']
                #self.NewsList.append({string:newsUrl})
        for news in soup.select('.post-block__title  a'):
           for string in news.stripped_strings:
                tittle=news.text
                #article.append(tittle.strip())   #strip去处多余空格
                print(news.text)
                newsUrl=news.attrs['href']
                #article.append(url.strip())
                #print(a)
                self.NewsList.append({string:newsUrl})

class GrabNews2():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://tech.sina.com.cn/'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        #for news in newsList:
            #for string in news.stripped_strings:
                #newsUrl = 'http://eis.whu.edu.cn/' + news['href']
                #self.NewsList.append({string:newsUrl})
        for news in soup.select('.tech-news li  a'):
           tittle=news.text
           print(news.text)
           for string in news.stripped_strings:
                #tittle=news.text
                #article.append(tittle.strip())   #strip去处多余空格
                #print(news.text)
                newsUrl=news.attrs['href']
                #article.append(url.strip())
                print(newsUrl)
                self.NewsList.append({string:newsUrl})
   


#adopt from other article
def writeNews():
    grabNews = GrabNews()
    grabNews.getNews()
    #timeDate=time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
    #timeDate=time.strftime("%Y-%m-%d", time.localtime())
    now = datetime.now
    print(now.strftime('%a, %b %d %H:%M'))
    #timeDate=time.strftime("%Y-%m-%d", time.localtime())
    timeDate=now.strftime('%a, %b %d %H:%M')
    fp = codecs.open('news"%s".html', 'w', 'utf-8' %timeDate)
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()

def writeNews2():
    grabNews = GrabNews2()
    grabNews.getNews()
    #print("test write 0711")
    fp = codecs.open('news.html', 'a', 'utf-8')  #w---->a  改为追加内容的模式07
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()



def mail():
  ret=True
  try:
    #msg = MIMEMultipart('alternative')
    msg = MIMEMultipart()  # test two html file 201907
    #msg['Subject'] = Header("subject",'utf-8')
    #news=getNews('https://techcrunch.com/')
    #txt=MIMEText(news.encode(),'plain','unicode')  #utf-8- English web 20190711
    writeNews()
    writeNews2()
    fp = open('news.html')
    techHtml = MIMEText(fp.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711
    #txt=MIMEText(news.encode(),'plain','unicode')
    msg.attach(techHtml)
    fp.close
    
    #writeNews2()
    #fp2 = open('sina-news.html')
    #techHtml_2 = MIMEText(fp2.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711
    #txt=MIMEText(news.encode(),'plain','unicode')
    #msg.attach(techHtml_2)
    #fp2.close

    path = '/tmp'         # 替换为你的路径
    dir = os.listdir(path)                  # dir是目录下的全部文件
    listN=get_file_list(path)
    #print (listN)
    imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
    print('Send IMG is "%s" ' %imgPath)
    #get_file_list(path)
    #for d in dir:                        # d是每一个文件的文件名
    #imgPath = path +'/'+ imgPath     #拼接字符串并换行
    
    #for imgPath in glob.glob("/tmp/*.jpg"):        
         #print (imgPath)    
    
    #imgPath=get_file_list(imgPath) 
    pic=make_img_msg(imgPath) 
    if pic is None:
        print ("no picture captured!")
    else:
        msg.attach(make_img_msg(imgPath))
    #msg.attach(make_img_msg('/home/pi/EangelCam2019.jpg'))    #  single ''!!! 0603
    msg['From']=formataddr(["Eangel Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的玩家",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="SE3 Cam 2019" #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
    server.login(my_sender,_pwd)  #括号中对应的是发件人邮箱账号、邮箱密码
    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND NEWS AND IMG OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False
    print (str(e))
    ret=False
  return ret

#ret=mail()
#if ret:
 # print 'ok' #如果发送成功则会返回ok，稍等20秒左右就可以收到邮件
  #GPIO.output(pin0,GPIO.HIGH)
   #time.sleep(10)
   #GPIO.output(pin0,GPIO.LOW)
 #else:
   #print 'send failed' #如果发送失败则会返回failed
   #GPIO.output(pin1,GPIO.HIGH)
   #time.sleep(15)
   #GPIO.output(pin1,GPIO.LOW)

if __name__ == '__main__':
  mail()
        
