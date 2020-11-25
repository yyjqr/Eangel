#拼接字符串并换行## -*- coding: UTF-8 -*-
#@author: JACK YANG 201902-->10-->202008->202011  yyjqr789@sina.com
#!/usr/bin/python3
import smtplib
#from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage  #20180603add JACK
from email.header import Header
import ssl
import sys,os  #os.listdir 201902
import time
import glob  #查找通配文件 201902

from email.utils import formataddr


import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import codecs # use for write a file 0708


my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='yyjqr789@sina.com' #收件人邮箱账号
#receiver=my_sender
_pwd = "XXX"  #需在qq邮箱开启SMTP服务并获取授权码


def make_img_msg(fn):
    #msg = MIMEMultipart('alternative')
    
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
    image=MIMEImage(data,name=fn.split("/")[2])  #以/分隔目录文件/tmp/xxx.jpg，只要后面的文件名 20190222！
    #image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    image.add_header('Content-ID','EangelCam2021')  #发送的图片附件名称 0603
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
        dir_list = sorted(dir_list,  key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        # print(dir_list)
        return dir_list

array=['机器人','新冠','量子','物联网','硬科技','数字','5G','Robot','robot','Robotics','COVID','Digital','AI','IOT','ML']
def findKeyWordInNews(str):
   #print(str)
   for i in range(15):
       
       if array[i] in str:
           #print("test")
           return True
   return False

class GrabNews():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://techcrunch.com/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        
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
        for news in soup.select('.tech-news li  a'):
           tittle=news.text
           print(news.text)
           for string in news.stripped_strings:
                newsUrl=news.attrs['href']
                #article.append(url.strip())
                print(newsUrl)
                self.NewsList.append({string:newsUrl})
                

         
    
    

class GrabNewsTechnet():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'http://stdaily.com/'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        for news in soup.select('div.fp_subtitle   a'):  ##ti_news---->fp_title
        #for news in soup.select('div.ti_news   a'):
            if findKeyWordInNews(news.text):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                    if news.attrs['href'].startswith('http'):
                        newsUrl=news.attrs['href']
                    else:
                        newsUrl=url+news.attrs['href']
                    #article.append(url.strip())
                    
                    if {string:newsUrl} not in self.NewsList:
                        print('newsUrl', newsUrl)
                        self.NewsList.append({string:newsUrl})
                    else:
                        print("------- ")
                
class GrabNewsAI():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://aitopics.org/search'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        
        for news in soup.select('.searchtitle   a'):
            if findKeyWordInNews(news.text):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                    
                    newsUrl=news.attrs['href']
                    #article.append(url.strip())
                    print(newsUrl)
                    self.NewsList.append({string:newsUrl})

# get the sys date and hour,minutes!!
now_time = datetime.now()
date=datetime.now().strftime('%Y-%m-%d_%H:%M')
print (date)

#adopt from other article
def writeNews():
    grabNews = GrabNews()
    grabNews.getNews()
  
    fp = codecs.open('news%s.html' % date , 'a', 'utf-8')
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()



def writeNews2():
    grabNews = GrabNews2()
    grabNews.getNews()
    #print("test write 0711")
    fp = codecs.open('news%s.html' % date , 'a', 'utf-8')  #w---->a  改为追加内容的模式07
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()

def writeNewsTechNet():
    grabNews = GrabNewsTechnet()
    grabNews.getNews()
  
    fp = codecs.open('news%s.html' % date , 'a', 'utf-8')
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()
    
#adopt AI from other article
def writeNewsAI():
    print("SEARCH AI news")
    grabNews = GrabNewsAI()
    grabNews.getNews()
    
    fp = codecs.open('news%s.html' % date, 'w', 'utf-8') 
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
    writeNewsAI()
    writeNews()
    #writeNews2()
    writeNewsTechNet()
    fp = open('news%s.html' % date,'rb+')
    techHtml = MIMEText(fp.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711--->fp.read().decode('utf-8')
    msg.attach(techHtml)
    fp.close

     
    pic=None
    print (pic) 
    if pic is None:
        print ("no picture captured!")
    else:
        print ("no pic!")
        #msg.attach(make_img_msg(imgPath))
    msg['From']=formataddr(["smart Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的玩家",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="Robot agent 2020" #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
    server.login(my_sender,_pwd)  #括号中对应的是发件人邮箱账号、邮箱密码
    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND AI NEWS  OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False
    print (str(e))
    ret=False
  return ret


if __name__ == '__main__':
  mail()
        
