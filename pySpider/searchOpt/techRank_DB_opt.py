## -*- coding: UTF-8 -*-
#@author: JACK YANG 
#@date:201902-->10 --->
      #202006-->202101--->202110
      # 2022.09 add rank map

      # 2022.11 KEY OPT


# Email: yyjqr789@sina.com

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
from datetime import datetime # date for file
import glob  #查找通配文件 201902

from email.utils import formataddr


import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
from pprint import pprint
#import pandas
#一些数据写入文件时会有编码不统一的问题，so codecs to assign code type!!
import codecs # use for write a file 0708
import mysqlWriteNewsV2  #mysql database

import encrypt_and_verify_url

my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='yyjqr789@sina.com' #收件人邮箱

use_database=False;
pin1=13

#GPIO.setup(pin1,GPIO.OUT)
save_news_path="/home/pi/techNews/"
# get the sys date and hour,minutes!!
now_time = datetime.now()
date=datetime.now().strftime('%Y-%m-%d_%H:%M')
print (date)
year_month=datetime.now().strftime('%Y-%m')

newsFullPath=os.path.join(save_news_path,date+'.html')
print(newsFullPath)
sql = """ INSERT INTO techTB(Id,Rate,title,author,publish_time,content,url,key_word) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) """

kRankLevelValue =0.78   ##judge value

array=['机器人','新冠','量子','物联网','硬科技','数字','5G','Robot','robot','COVID','Digital','AI','IOT','ML']

arrayKEYWORDS_CN=['机器人','新冠','量子','物联网','硬科技','数字','5G','高端制造','智慧','智能','绿色','低碳','新能源','碳中和']

arrayKEYWORDS_EN=['chip','Chip','risc','RISC-V','5G','Robot','robot','COVID','Digital','AI','IOT','ML','APPLE','light','big data','auto','deep learning','bot','energy','clean']

with open('./tech_key_config_map.json') as j:
     #cfg = json.load(j)
     #print(cfg)
     KEYWORDS_RANK_MAP=json.load(j)['KEYWORDS_RANK_MAP']
#print(KEYWORDS_RANK_MAP)


def encrypt_getKey(key):
    a = base64.b64encode(key)
    print(a) #  b'aGVsbG8gd29ybGQ='
 
    b = base64.b64decode(a)

    print(b) # b"hello world"

def decrypt_getKey(key):
    b = base64.b64decode(key)
    #print(b)
    return b

def make_img_msg(fn):
    #msg = MIMEMultipart('alternative')
    
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
    image=MIMEImage(data,name=fn.split("/")[2])  #以/分隔目录文件/tmp/xxx.jpg，只要后面的文件名 20190222！
    image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    #image.add_header('Content-ID','EangelCam2019')  #发送的图片附件名称 0603
    return image

def get_file_list(file_path):
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



def findKeyWordInNews(str):

   for i in range(14):       
       if array[i] in str:
           #print("test")
           return True
   return False

def findValuedInfoInNews(str,keyWords):

   for i in range(len(keyWords)):
       
       if keyWords[i] in str:
           #print("test")
           return True
   return False

def findValuedInfoRank(str,keyMap):
   #print('{0}'.format(len(keyMap)))
   #print(keyMap)
   rankValue=0
   rankOldValue=0
   print_flag=True
   for i in keyMap:
       #print(i)   
       if  i in str:
           rankValue += keyMap[i]
       if rankValue != 0 :
          if print_flag:
              #print("compute str: {0} \n Rank key:{1} value:{2}\n".format(str,i,rankValue))
              print_flag=False
              rankOldValue=rankValue
          else:
              if rankValue>rankOldValue :
                  #print("Add rank: {0} value:{1}".format(i,rankValue))
                  rankOldValue=rankValue
   if rankValue !=0:
      print("Final news:{0} rank value:{1}\n\n".format(str,rankValue))
   return rankValue

def validate_url_access(self, url):
	# 定义响应头文文件
        headers = {"Content-Type": "application/json"}
	# 通过requests库
        try:
           res = requests.get(url=url, headers=headers,timeout=10)
           #print("validating the url access,waiting......")
	# 如果返回值非200 则跳出该函数返回false
           if res.status_code != 200:
              print("get url:{0} error:{1}\n".format(url,res))
              return False
        except Exception as e:
           print (str(e))
           return False
        return True


### techcrunch,can't visit from 2021.11,because of yahoo info!!!
class GrabNews():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://techcrunch.com/'
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        for news in soup.select('.post-block__title  a'):
            if findValuedInfoInNews(news.text,arrayKEYWORDS_EN):
                tittle=news.text
                print(news.text) 
                for string in news.stripped_strings:
                    newsUrl=news.attrs['href']
                #article.append(url.strip())
                    self.NewsList.append({string:newsUrl})



class GrabNewsProduct():
    def __init__(self):
        self.NewsList = []
    def getNews(self):
        url = 'https://www.popularmechanics.com/'
        headers = { 'User-Agent':'Mozilla/5.0 (Windows NT 6.3;Win64;x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36'}
        #html = requests.get(url,headers = headers).text
        print("timeout optimize")
        req  = requests.get(url,headers = headers, timeout=5)
        html =req.text      
 # r2.encoding = 'utf-8'
        print ("requests.get {} encoding: {} " .format(url, requests.get(url).encoding))
        
        soup = BeautifulSoup(html, "html.parser")

        #print(soup.get_text())
        newsIndex=0
        #for news in soup.select('a.enk2x9t2 css-7v7n8p epl65fo4'):  #更换了class相关字段,class前要加点.  202202 ---->enk2x9t2 css-7v
        for news in soup.select('a.enk2x9t2'):
            curent_news_rank =findValuedInfoRank(news.text,KEYWORDS_RANK_MAP) 
            #if findValuedInfoInNews(news.text,arrayKEYWORDS_EN):
            if curent_news_rank >kRankLevelValue :
               tittle=news.text
               print(news.text)
               str_news=news.txt
               #print("After filter\n")
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
                    
                    if validate_url_access(self,newsUrl)==False :
                        del self.NewsList[-1]
                                                 
                        print("Error,this url {0} can't browse!!\n".format(newsUrl))
                    newsOne=(newsIndex,curent_news_rank ,news.text,'SmartLife',date, 'content',
                        newsUrl, '产品科技')
                    result = mysqlWriteNewsV2.writeDb(sql, newsOne)


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

        r2 = requests.get(url,timeout=5)
        r2.encoding = 'utf-8'



        soup = BeautifulSoup(r2.text, "html.parser")
        newsIndex =0
        for news in soup.select('.searchtitle   a'):
            #if findValuedInfoInNews(news.text,array):
            curent_news_rank =findValuedInfoRank(news.text,KEYWORDS_RANK_MAP)
            if curent_news_rank > kRankLevelValue :
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                #article.append(tittle.strip())   #strip去处多余空格
                    newsUrl=news.attrs['href']
                #article.append(url.strip())
                    print(newsUrl)

##if  "techcrunch" not in newsUrl:   validate_url_access can verify browsing techcrunch or not!! 11.20
                    if validate_url_access(self,newsUrl)==True :
                        self.NewsList.append({string:newsUrl})
                    else :
                        print("Error,this url can't browse!!\n")

               ## 写入数据库
                    if use_database == True : 
                        newsOne=(newsIndex,curent_news_rank ,news.text,'SmartLife',date, 'content',
                        newsUrl, '人工智能')
                        result = mysqlWriteNewsV2.writeDb(sql, newsOne)



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
                    if validate_url_access(self,newsUrl)==True :
                        #print ("test validate")
                        self.NewsList.append({string:newsUrl})
                    else :
                        print("Error,this url can't browse!!\n")

                    #self.NewsList.append({string:newsUrl})




#科学网
def writeNewsTechNet():
    grabNews = GrabNewsTechnet()
    grabNews.getNews()
  
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
    print("SEARCH AI news")
    grabNews = GrabNewsAI()
    grabNews.getNews()
    fp = codecs.open(newsFullPath, 'w', 'utf-8')  #w---->a  改为追加内容的模式07
    for news in grabNews.NewsList:
        for key in news.keys(): # key:value. key是新闻标题，value是新闻链接
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            fp.write('<hr />')
    fp.close()


#adopt 工业产品，军工产品  from other article
def writeNewsProduct():
    print("\n SEARCH Product news")
    grabNews = GrabNewsProduct()
    grabNews.getNews()
     #w---->a  改为追加内容的模式 202209
    fp = codecs.open(newsFullPath, 'a', 'utf-8')
    for news in grabNews.NewsList:
        for key in news.keys(): 
            fp.write('<a href=%s>%s</a>' % (news[key], '*'+key))
            #print(news[key])
            fp.write('<hr />')
    fp.close()


def mail():
  ret=True

  _pwd =encrypt_and_verify_url.decrypt_getKey("cnVsbnVjZW55cWNwYmJiZg==".encode("utf-8"))

  try:
    #msg = MIMEMultipart('alternative')
    msg = MIMEMultipart()  # test two html file 201907
    #add AI topic search 202006

    try:
       writeNewsAI()
    except Exception as e:
       print (str(e))
       try:

           encrypt_and_verify_url.run_cmd_Popen_fileno("telnet 34.72.71.171 443")

       except Exception as e:
           print (str(e))

    try:
        writeNewsProduct()  
        writeNewsSina()
    except Exception as e:
        print (str(e))

    writeNewsTechNet()
    #writeNews2()
    with open(newsFullPath,'rb+') as fp:
        techHtml = MIMEText(fp.read(), 'html', 'utf-8')  #内容, 格式, 编码 English web 20190711
        msg.attach(techHtml)
    #fp.close
    
    path = '/tmp'         # 替换为你的路径
    listN=get_file_list(path)
    #print (listN)
    if listN:
       imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
       print('Send IMG is "%s" ' %imgPath)
       msg.attach(make_img_msg(imgPath))
    else: 
        print("no pic capture!")     
    msg['From']=formataddr(["Eangel Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的用户",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="EXAID 价值Rank %s" %year_month  #邮件的主题，也可以说是标题

    server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465

    server.login(my_sender,_pwd.decode("utf-8"))  #括号中对应的是发件人邮箱账号、邮箱密码---->bytes need decode to string 1113

    server.sendmail(my_sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
    print ('SEND NEWS AND IMG OK')
    server.quit()  #这句是关闭连接的意思
  except Exception as e:  #如果try中的语句没有执行，则会执行下面的ret=False
    print (str(e))
    ret=False
  return ret


if __name__ == '__main__':
  mail()
        
