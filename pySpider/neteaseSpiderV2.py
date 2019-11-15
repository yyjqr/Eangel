# -*- coding: utf-8 -*-
#!/usr/bin/python3

import os
import re
import requests
from lxml import etree
from lxml.html.clean import Cleaner  #CLEANER 0415

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

    #content = cleaner.clean_html(html).encode('gbk')
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
    content = re.sub(r'<td?>', '', content)  #add 匹配td开始的字符串
    content = re.sub(r'</td>', '', content)  #add Test 1023  
    #content = re.sub(r'</?^class+>', '', content)   #<td class=
    content = re.sub(r'<td class="rank">', '', content)  #<td class=  
    content = re.sub(r'<td class="gray">', '', content)  #<td class="gray">
 # 清理网页头标题之类
    #content = content.split('本周点击排行')[1]
    content = content.split('点击数')[1]
    content = content.split('返回顶部')[0]
    return content

def Spider(url):
    i = 0
    myPage = requests.get(url).content.decode("gbk")
    myPageResults = Page_Info(myPage)
    save_path = "news网易新闻抓取"
    filename = str(i)+"_网易新闻排行榜"
    i += 1
    for item, url in myPageResults:
        print ("downloading", url)
        new_page = requests.get(url).content.decode("gbk")
        new_page=filterHtml(new_page)
        testNewPage(save_path, item, new_page)
        newPageResults = New_Page_Info(new_page)
        #filename = str(i) + "_" + item
        #StringListSave(save_path, filename, newPageResults)
        #i += 1
        #print (i)

if __name__ == '__main__':
    print ("start")
    start_url = "http://news.163.com/rank/"
    Spider(start_url)
    print ("end")
