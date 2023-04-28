## -*- coding: UTF-8 -*-
#拼接字符串并换行
#@author: JACK YANG 
#@date:201902-->10 --->
      #202006-->202101--->202110
      #2023.03
# Email: yyjqr789@sina.com
#!/usr/bin/python3
import smtplib
#from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage  #20180603add JACK
from email.header import Header
import ssl
import sys,os,getopt  #os.listdir 201902 -->add getopt 202209
import time
from datetime import datetime # date for file
import glob  #查找通配文件 201902

from email.utils import formataddr


import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
#import pandas
#一些数据写入文件时会有编码不统一的问题，so codecs to assign code type!!
import codecs # use for write a file 0708


my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='yyjqr789@sina.com' #收件人邮箱账号
#receiver=my_sender
_pwd ="rulnucenyqcpXXXf"  #202010---202102   #需在qq邮箱开启SMTP服务并获取授权码

pin0=11
pin1=13
#GPIO.setup(pin1,GPIO.OUT)
save_news_path="/home/ai/techNews/"
# get the sys date and hour,minutes!!
now_time = datetime.now()
date=datetime.now().strftime('%Y-%m-%d_%H:%M')
print (date)
year_month=datetime.now().strftime('%Y-%m')

newsFullPath=os.path.join(save_news_path,date+'.html')
print(newsFullPath)

array=['机器人','新冠','量子','物联网','硬科技','数字','5G','Robot','robot','COVID','Digital','AI','IOT','ML']

arrayKEYWORDS_CN=['机器人','新冠','量子','物联网','硬科技','数字','5G','高端制造','智慧','智能','绿色','低碳','新能源','碳中和']

arrayKEYWORDS_EN=['chip','Chip','risc','RISC-V','5G','Robot','robot','COVID','Digital','AI','IOT','ML','APPLE','light','big data','auto','deep learning','bot','energy','clean']

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

def get_recognize_img(fn):
    
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
  ## 文件路径变动，所以split选择也需从7---变到index9 202210  
  ##---->/home/ai/jetson-inference/build/aarch64/bin/images/test/2022-11-06_15:38:40.jpg  1106
  ## 后台运行程序，识别图片存储到/tmp/xxx.jpg
    image=MIMEImage(data,name=fn.split("/")[2])  #以/分隔目录文件/tmp/xxx.jpg，只要后面的文件名 20190222！
    print("test image name {0}".format(fn.split("/")[2]))
    image.add_header('Content-ID','filename="%s"'  %fn)
    #image.add_header('Content-ID','AICam2022')  #发送的图片附件名称 0603
    return image

def get_file_list(file_path):
    #dir_list=glob.glob("/tmp/*.jpg")
    dir_list = []    
    extensions = ['jpg', 'jpeg','JPG','JPEG'] # 注意下这里
    for extension in extensions:
       file_glob=file_path+'*.' + extension
       #print("file_glob:{0}".format(file_glob))
       dir_list.extend(glob.glob(file_glob))
    #print (dir_list)  ##列出所有/tmp/下各种格式的图片
    if not dir_list:
        return
    else:
        # 注意，这里使用lambda表达式，将文件按照最后修改时间顺序升序排列
        # os.path.getmtime() 函数是获取文件最后修改时间
        dir_list = sorted(dir_list,  key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        # print(dir_list)
        return dir_list

def parse_cmd_param(argv):
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
   except getopt.GetoptError:
      print ('test.py -i <inputfile> -o <outputfile>')
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print ('test.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
   print ('输入的文件为：', inputfile)
   #print '输出的文件为：', outputfile
   return inputfile

def findKeyWordInNews(str):
   #print(str)
   for i in range(14):
       
       if array[i] in str:
           #print("test")
           return True
   return False

def findValuedInfoInNews(str,keyWords):
   #print(str)
   #print(len(keyWords))
   #print(keyWords)
   for i in range(len(keyWords)):
       
       if keyWords[i] in str:
           #print("test")
           return True
   return False



class GrabNewsSina():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://tech.sina.com.cn/'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        
        for news in soup.select('.tech-news li  a'):
           if findValuedInfoInNews(news.text,arrayKEYWORDS_CN):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
	                #print(news.text)
                   newsUrl=news.attrs['href']
                #article.append(url.strip())
                   print(newsUrl)
                   self.NewsList.append({string:newsUrl})
   
class GrabNewsAI():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://aitopics.org/search'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        
        for news in soup.select('.searchtitle   a'):
            if findValuedInfoInNews(news.text,array):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                #article.append(tittle.strip())   #strip去处多余空格
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
                    #article.append(tittle.strip())   #strip去处多余空格
                    if news.attrs['href'].startswith('http'):
                        newsUrl=news.attrs['href']
                    else:
                        newsUrl=url+news.attrs['href']
                    #article.append(url.strip())
                    print(newsUrl)
                    self.NewsList.append({string:newsUrl})




#科学网
def writeNewsTechNet():
    grabNews = GrabNewsTechnet()
    grabNews.getNews()
  
    #fp = codecs.open('news%s.html' % date , 'a', 'utf-8')
    with codecs.open(newsFullPath,'a', 'utf-8') as fp:
        for news in grabNews.NewsList:
            for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
                fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
                fp.write('<hr />')




#adopt AI from other article
def writeNews():
    grabNews = GrabNews()
    grabNews.getNews()
    # 加上获取新闻的日期
    fp = codecs.open(newsFullPath , 'a', 'utf-8')
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()

def writeNewsSina():
    grabNews = GrabNewsSina()
    grabNews.getNews()
    fp = codecs.open('news%s.html' % date , 'a', 'utf-8') #w---->a  改为追加内容的模式07
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()

def writeNewsAI():
    grabNews = GrabNewsAI()
    grabNews.getNews()
    print("SEARCH AI news")
    fp = codecs.open(newsFullPath, 'w', 'utf-8')  #w---->a  改为追加内容的模式07
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
    #add AI topic search 202006
    try:
        writeNewsAI()

        #writeNews()  ##no need to visit techcrunch!!
        writeNewsSina()
    except Exception as e:
        print (str(e))

    #writeNewsTechNet()
    #writeNews2()
    #fp = open('news%s.html' % date,'rb+')
    try:
        with open(newsFullPath,'rb+') as fp:
            techHtml = MIMEText(fp.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711
            msg.attach(techHtml)
    except Exception as e:
         print (str(e))
         content ="未获取到相关最新资讯"
         text = MIMEText(content, 'plain', 'utf-8')
         msg.attach(text)
    #fp.close
    
    path = '/tmp/'         # 替换为你的路径
    listN=get_file_list(path)
    print (listN)
    if listN:
       imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
       #imgPath=parse_cmd_param(sys.argv[1:])
       print('Send IMG is "%s" ' %imgPath)
    ## in detect program ,will pass the absolute total path ,so no need below covert.20221106
       #imgPath ="/home/ai/jetson-inference/data/images/test/"+imgPath
       try:
           msg.attach(get_recognize_img(imgPath))
       except Exception as e:  #如果try中的语句没有执行，则会执行>$
           print (str(e))
    else: 
        print("no pic capture!")
         
    msg['From']=formataddr(["Eangel Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的用户",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="EXAID 识别 %s" %year_month  #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
    server.login(my_sender,_pwd)  #括号中对应的是发件人邮箱账号、邮箱密码
    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND NEWS AND IMG OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False
    print (str(e))
    ret=False
  return ret


if __name__ == '__main__':
  mail()
        
