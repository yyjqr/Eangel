#拼接字符串并换行## -*- coding: UTF-8 -*-
#@author: JACK YANG 201902  yyjqr789@sina.com
# 基于python3 开发！！
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
import neteaseSpider #0207
from lxml.html import etree
from lxml.html.clean import Cleaner #html cleaner 0415
import RPi.GPIO as GPIO


my_sender='840056598@qq.com' #发件人邮箱账号，为了后面易于维护，所以写成了变量
receiver='xxx@sina.com'
#receiver=my_sender
_pwd = "xxx......."  #0603  #需在qq邮箱开启SMTP服务并获取授权码20180505

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
    txt=MIMEText(data,'plain','utf-8')
    #image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    txt.add_header('Content-ID','Spider2019')  #发送的图片附件名称 0603
    return txt


def make_img_msg(fn):
    #msg = MIMEMultipart('alternative')
    
    f=open(fn,'rb') # r--->rb read+binary 0603
    data=f.read()
    f.close()
    image=MIMEImage(data,name=fn.split("/")[2])  #以/分隔目录文件/tmp/xxx.jpg，只要后面的文件名 20190222！
    #image.add_header('Content-ID','attachment;filenam="%s" ' %fn)
    image.add_header('Content-ID','EangelCam2019')  #发送的图片附件名称 0603
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
    spider=neteaseSpider.Spider(start_url)


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
    # Ctext取周围k行(k<5),定为3

    blocksWidth = 3
    # 每一个Cblock的长度
    Ctext_len = []
    # Ctext
    lines = content.split('n')
    print (lines)
    print ("test Parsing")
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
    # 开始标识
    start = -1
    # 结束标识
    end = -1
    # 是否开始标识
    boolstart = False
    # 是否结束标识
    boolend = False
    # 行块的长度阈值
    max_text_len = 88
    # 文章主内容
    main_text = []
    # 没有分割出Ctext
    if len(Ctext_len) < 3:
    	return '没有正文'
    for i in range(len(Ctext_len) - 3):
    # 如果高于这个阈值
        if(Ctext_len[i] > max_text_len and (not boolstart)):
    # Cblock下面3个都不为0，认为是正文
          if (Ctext_len[i + 1] != 0 or Ctext_len[i + 2] != 0 or Ctext_len[i + 3] != 0):
            boolstart = True
            start = i
            continue
        if (boolstart):
        # Cblock下面3个中有0，则结束
            if (Ctext_len[i] == 0 or Ctext_len[i + 1] == 0):
                end = i
                boolend = True
                mp = []

    # 判断下面还有没有正文
        if(boolend):
            for ii in range(start, end + 1):
                if(len(lines[ii]) < 5):
                    continue
                tmp.append(lines[ii] + "n")
                str = "".join(list(tmp))
                # 去掉版权信息
                if ("Copyright" in str or "版权所有" in str):
                    continue
                main_text.append(str)
                boolstart = boolend = False
    # 返回主内容
    result = "".join(list(main_text))
    print (result)

def mail():
  ret=True
  try:
    msg = MIMEMultipart('alternative')
     #构建邮件附件
 #获取文件路径
 
    #net_spiderNews()
    #txtFile=make_txt_msg('/home/pi/Documents/news网易新闻抓取/科技.txt')
    file='/home/pi/news网易新闻抓取/科技.txt'
    print (file)
    #parseHtml(file)
    txtFile=make_txt_msg(file)
    msg.attach(txtFile)   #添加附件

    path = '/tmp'         # 替换为你的路径
    dir = os.listdir(path)                  # dir是目录下的全部文件
    listN=get_file_list(path)
    #print (listN)
    imgPath=listN[-1]  #取列表的最后一个文件，即倒数第一个20190218
    print('Send IMG is "%s" ' %imgPath)
    
    msg.attach(make_img_msg(imgPath))
    #msg.attach(make_img_msg('/home/pi/EangelCam2019.jpg'))    #  single ''!!! 0603
    msg['From']=formataddr(["Eangel Robot",my_sender])  #括号里的对应发件人邮箱昵称、发件人邮箱账号
    msg['To']=formataddr(["亲爱的玩家",receiver])  #括号里的对应收件人邮箱昵称、收件人邮箱账号
    msg['Subject']="Raspi 3B Cam 2019" #邮件的主题，也可以说是标题

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
   #time.sleep(15)
   #GPIO.output(pin1,GPIO.LOW)

if __name__ == '__main__':
  mail()
        
