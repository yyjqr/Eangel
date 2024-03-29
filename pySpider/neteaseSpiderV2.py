# -*- coding: utf-8 -*-
#!/usr/bin/python3
# 2019-202005 爬取科技新闻，去掉大部分tag标签--->改为utf编解码  202108
import os
import re
import requests
from lxml import etree
from lxml.html.clean import Cleaner  #CLEANER 0415
import chardet 
import urllib

def Page_Info(myPage):
    '''Regex'''
    # 这里的re.findall 返回的是一个元组列表,内容是 (.*?) 中匹配到的内容
    # 析取每个链接的标题和链接
    myPage_Info = re.findall(r'<div class="titleBar" id=".*?"><h2>(.*?)</h2><div class="more"><a href="(.*?)">.*?</a></div></div>',myPage,re.S)
    return myPage_Info

def StringListSave(save_path, filename, slist):
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    path = save_path + "/" + filename + ".txt"
    with open(path, "w+") as fp:
        for s in slist:
            # 做了utf8转码,转为终端可识别的码制
            fp.write("%s\t\t%s\n" % (s[0].encode("utf8"), s[1].encode("utf8")))
            #fp.write("%s\t\t%s\n" % (s[0], s[1]))

#测试new_page的内容    
def testNewPage(save_path, filename, new_page):
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    path = save_path + "/" + filename + ".txt"
    fp = open(path, "w+")
    fp.write(new_page)
    
def New_Page_Info(new_page):
    '''Regex(slowly) or Xpath(fast)'''
    # new_page_info = re.findall(r'<td class=".*?">.*?<a href="(.*?)\.html.*?>(.*?)</a></td>',new_page,re.S)
    # results = []
    # for url, item in new_page_info:
    #     results.append((item, url+".html"))
    # return results

    #将new_page的内容转为html格式的树
    dom = etree.HTML(new_page)
    #析取 <tr <td <a中的文本
    new_items = dom.xpath('//tr/td/a/text()')
    #析取 <tr <td <a中的链接, @href 是一个属性
    new_urls = dom.xpath('//tr/td/a/@href')
    assert(len(new_items) == len(new_urls))
    return zip(new_items, new_urls)

def filterHtml(new_page):
    #html = requests.get(url, headers=headers).content
    html=new_page
#清除不必要的标签
    cleaner = Cleaner(style = True,scripts=True,comments=True,javascript=True,page_structure=True,safe_attrs_only=False)
    ##测试编码成utf-8 2021
    #content = cleaner.clean_html(html).encode('utf-8')
    content = cleaner.clean_html(html)
#这里打印出来的结果会将上面过滤的标签去掉，但是未过滤的标签任然存在。
    #print (content)
    """清理新闻内容"""
    # 清理未知字符和空白字符
    content = re.sub(r'\?+', ' ', content)
    content = re.sub(r'( *\n+)+', '\n', content)
    content = re.sub(r'\u3000', '', content)
    content = re.sub(r'<tr>', '', content)  #add Test 1023
    content = re.sub(r'</tr>', '', content)  #add Test 1023
    #content = re.sub(r'<td?>', '', content)  #add 匹配td开始的字符串
    #content = re.sub(r'<td[^>]*>(.*?)</td>', '', content)  #add 匹配td开始的字符串
    content = re.sub(r'<td[^>]*>', '', content)  #add 匹配td开始的字符串  20200502!
    content = re.sub(r'<img[^>]*>', '', content)  #add 匹配img 开始的字符串
    content = re.sub(r'<td class="rank">', '', content)  #add 匹配td开始的字符串
    content = re.sub(r'<td class="cBlue">', '', content)  #add 匹配td开始的字符串
    content = re.sub(r'<td class="gray">', '', content)  #add 匹配td开始的字符串
    #content = re.sub(r'<span>^[0-9]*</span>', '', content)  #add 匹配span开始的字符串
    content = re.sub(r'<span>[^>]*</span>', '', content)  #add 匹配span开始的字符串
    
    #content = re.sub(r'<td class="^[A-Za-z0-9]+$>"', '', content)  #add Test 0502  
    #content = re.sub(r'<td ^class>', '', content)  #add Test 0502  
    #content = re.sub(r'<^td>', '', content)   #<td class=  
    content = re.sub(r'</td>', '', content)   #<td class=  
 # 清理网页头标题之类
    #content = content.split('本周点击排行')[1]
    content = content.split('点击数')[1]
    content = content.split('返回顶部')[0]
    return content

def Spider(url):
    i = 0
    print ("downloading ", url)
    #myPage = requests.get(url).content.decode("gbk")
    myPage = requests.get(url).content.decode("utf-8")
    myPageResults = Page_Info(myPage)
    ##开始滤除部分特殊字符 202108，避免解析异常
    #myPageResults=filterHtml(myPageResults)

    save_path = "news网易新闻抓取"
    filename = str(i)+"_网易新闻排行榜"
    StringListSave(save_path, filename, myPageResults)
    i += 1
    for item, url in myPageResults:
        print ("downloading", url)
        #new_page = requests.get(url).content.decode("gbk")
        new_page = requests.get(url).content.decode("utf-8")
        #print(requests.get(url).content)
      ##获取的结果是bytes,而bytes没有readline函数！！！ 20210829
        #f=requests.get(url).content
        #line = f.readline()
        new_page=filterHtml(new_page)
        testNewPage(save_path, item, new_page)
        newPageResults = New_Page_Info(new_page)
        filename = str(i) + "_" + item
        StringListSave(save_path, filename, newPageResults)
        i += 1

def testEncode(url):
      #先获取网页内容
    data1 = urllib.request.urlopen(url).read()
  #用chardet进行内容分析
    chardit1 = chardet.detect(data1)
    print ("html codeing:"+chardit1['encoding']) # 

if __name__ == '__main__':
    print ("start")
    start_url = "http://news.163.com/rank/"
    testEncode(start_url)
    Spider(start_url)
    print ("end")
