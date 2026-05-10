#拼接字符串并换行## -*- coding: UTF-8 -*-
#@author: JACK YANG
#@date:201902-->10-->202008->202011 
#       ->202104-->202201--->0307
#Email:  yyjqr789@sina.com
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
import glob  #查找通配文件 

from email.utils import formataddr


import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import codecs # use for write a file 0708
import mysqlWriteNewsV2
import random

my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='yyjqr789@sina.com' #收件人邮箱账号
#receiver=my_sender
_pwd = "nufuXXcoehyobbji"  #需在qq邮箱开启SMTP服务并获取授权码


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
    

array=['机器人','物联网','硬科技','数字','5G','Robot','robot','Robotics','Digital','AI','IOT','ML','car','Car','plane','Plane','gun',
       'flighter','NASA','Mars','War','craft','Craft','fighter',
       'electricity','Electricity','power']

arrayKEYWORDS_CN=['机器人','新冠','量子','物联网','硬科技','数字','5G','高端制造','智慧','智能','绿色','低碳','新能源','碳中和']

arrayKEYWORDS_EN=['5G','Robot','robot','COVID','Digital','AI','IOT','ML','APPLE','light','big data','auto','deep learning','bot','energy','clean']

arrayKEYWORDS_MIL_ADVANCED_TECH=['war','fighter','electricity','Electricity','power','JET','flighter','unmanned','NUCLEAR','nuclear','electric','weapon',
                                 'cruiser','carrier','laser','autonomous','drone','drones','Navy','Russia','South China','China','Taiwan','bomb']

sql = """ INSERT INTO techTB(Id,Rate,title,author,publish_time,content,url,key_word) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) """

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

def findValuedInfoOPT(str,keyWords):
   #print(str)
   valueIndex=0
   for i in range(len(keyWords)):
       
       if keyWords[i] in str:
           valueIndex+=1
           if valueIndex>=2:
              print("this news Rate:%d" %valueIndex)
              return True
   return False

# get the sys date and hour,minutes!!
#def GetDate():
now_time = datetime.now()
date=datetime.now().strftime('%Y-%m-%d_%H:%M')
print ("现在日期:%s" %date)
timeForDB=datetime.now().strftime('%H:%M:%S')
year_month=datetime.now().strftime('%Y-%m')
print ("现在时间:%s" %timeForDB)


class GrabNews():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://techcrunch.com/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        
        for news in soup.select('.post-block__title  a'):
           for string in news.stripped_strings:
                tittle=news.text
                #article.append(tittle.strip())   #strip去处多余空格
                print(news.text)
                newsUrl=news.attrs['href']
                #article.append(url.strip())
                #print(a)
                self.NewsList.append({string:newsUrl})

class GrabNewsSina():
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
        #print("sql index:%d" %mysqlWriteNewsV1.getLastInsertId() )
        #newsIndex=random.randint(20,100000)
        newsIndex=0
        for news in soup.select('.searchtitle   a'):
            if findKeyWordInNews(news.text):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                    
                    newsUrl=news.attrs['href']
                    #article.append(url.strip())
                    print(newsUrl)
                    self.NewsList.append({string:newsUrl})
                    #newsIndex=newsIndex+1
                    print(newsIndex)
                    newsOne=(newsIndex, '1',news.text,'Jack',date, 'content',
                      newsUrl, '人工智能')
                    result = mysqlWriteNewsV2.writeDb(sql, newsOne)
                    print("write DB state: %d" %result)

class GrabNewsProduct():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://www.popularmechanics.com/'
        headers = { 'User-Agent':'Mozilla/5.0 (Windows NT 6.3;Win64;x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36'}
        r2 = requests.get(url,headers = headers).text
       # r2.encoding = 'utf-8'
        print ("requests.get {} encoding: {} " .format(url, requests.get(url).encoding))
        soup = BeautifulSoup(r2, "html.parser")
        print("test-----")
        #for news in soup.select('a.custom-item-title'):
        for news in soup.select('a.enk2x9t2'):  #更换了class相关字段,class前要加点.  202202 
            if findValuedInfoInNews(news.text,arrayKEYWORDS_EN):
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                    
                    if news.attrs['href'].startswith('http'):
                        newsUrl=news.attrs['href']
                    else:
                        newsUrl=url+news.attrs['href']
                    #article.append(url.strip())
                    
                    if {string:newsUrl} not in self.NewsList:
                        #print('newsUrl', newsUrl)
                        self.NewsList.append({string:newsUrl})
                    else:
                        print("------- ")

class GrabDriveWEB():
     def __init__(self):
        self.NewsList = []
     def getNews(self):
        url = 'https://www.thedrive.com/the-war-zone'
        URL = 'https://www.thedrive.com'
        r2 = requests.get(url)
        r2.encoding = 'utf-8'

        soup = BeautifulSoup(r2.text, "html.parser")
        #newsIndex= random.randint(20,100000)
        newsIndex=0
        for news in soup.select('.linkable'):
            RateRank=findValuedInfoOPT(news.text,arrayKEYWORDS_MIL_ADVANCED_TECH)
            if findValuedInfoOPT(news.text,arrayKEYWORDS_MIL_ADVANCED_TECH):
               tittle=news.text

               #print(news)
               #print("test Drive")
               print(news.text)
               for string in news.stripped_strings:
                    #print("URL")
                    if news.attrs['href'].startswith('http'):
                        newsUrl=news.attrs['href']
                    else:
                        newsUrl=URL+news.attrs['href']
                    
                    self.NewsList.append({string:newsUrl})
                    #newsIndex=newsIndex+1
                    print(newsIndex)
                    newsOne=(newsIndex,'2', news.text,'Jack',date, 'Barbare',
                      newsUrl, '军事')
                    result = mysqlWriteNewsV2.writeDb(sql, newsOne)
                    print("write DB state: %d" %result)


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



def writeNewsDrive():
    grabNews = GrabDriveWEB()
    grabNews.getNews()
    #print("test Drive 0711")
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
            print(key)
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


#adopt 工业产品，军工产品  from other article
def writeNewsProduct():
    print("SEARCH Product news")
    grabNews = GrabNewsProduct()
    grabNews.getNews()
    
    fp = codecs.open('news%s.html' %date, 'w', 'utf-8')
    #fileName='news%s.html' %date
    #print(fileName)
    #fp = codecs.open("newsProduct.html", 'w', 'utf-8') 
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            #print("test write")
            #print(news[key])
            fp.write('<hr />')
    fp.close()

    
def mail():
  ret=True
  try:
    #msg = MIMEMultipart('alternative')
    msg = MIMEMultipart()  # test two html file 201907
    writeNewsAI()
    #writeNewsProduct()
    #writeNews()
    writeNewsDrive()
    #writeNewsTechNet()
    fp = open('news%s.html' % date,'rb+')
    techHtml = MIMEText(fp.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711--->fp.read().decode('utf-8')
    msg.attach(techHtml)
    fp.close()

    path = '/tmp'         # 替换为你的路径
    listN=get_file_list(path)
    #print (listN)
    if listN:
       imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
       print('Send IMG is "%s" ' %imgPath)
       msg.attach(make_img_msg(imgPath))
    else: 
        print("no pic capture!")  
    msg['From']=formataddr(["smart Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的玩家",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="科技milDB %s" %year_month  #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
    server.login(my_sender,_pwd)  #括号中对应的是发件人邮箱账号、邮箱密码
    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND AI NEWS and write to DB OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False
    print (str(e))
    ret=False
  return ret


if __name__ == '__main__':
  mail()
        
