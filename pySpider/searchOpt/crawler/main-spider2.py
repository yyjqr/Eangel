## -*- coding: UTF-8 -*-
#@author: JACK YANG
#@date:
      # 2022.09 add rank map
      # 2024.10 scikit-learn
      # 2025.07 scraper类爬虫
# @Email: yyjqr789@sina.com

#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from typing import List, Dict, Optional

import encrypt_and_verify_url
from email.utils import formataddr
import ssl
import json

from sklearn.feature_extraction.text import TfidfVectorizer


# 全局配置
OUTPUT_FILE = "tech_news_summary.txt"
KEYWORDS_RANK_MAP = {...}  # 您的关键词权重映射
kRankLevelValue = 0.5  # 新闻价值阈值
# Define a set of common words to filter out (stop words)
stop_words = set([
    "is", "the", "this", "and", "a", "to", "of", "in", "for", "on",
    "if", "has", "are", "was", "be", "by", "at", "that", "it", "its",
    "as","about",
    "an", "or", "but", "not", "from", "with", "which", "there", "when",
    "so", "all", "any", "some", "one", "two", "three", "four", "five"
])



class NewsScraper:
    """通用新闻爬虫基类"""
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = requests.Session()  # 添加共享的 Session 对象
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        self.base_url = ""
        self.articles = []   
    def scrape(self):
        """子类需实现的具体爬取逻辑"""
        raise NotImplementedError("子类必须实现 scrape 方法")
    
    def filter_and_store(self):
        """过滤并存储符合条件的文章"""
        filtered_articles = []
        for title, url, weight in self.articles:
            if weight > kRankLevelValue:
                filtered_articles.append((title, url, weight))
        return filtered_articles
    # 计算关键词权重
    def calculate_keyword_weights(self, texts, keywords):
        vectorizer = TfidfVectorizer()

        tfidf_matrix = vectorizer.fit_transform(texts)
    ##scikit-learn>1.0.x use this version
        feature_names = vectorizer.get_feature_names_out()
        print("test feature_names", feature_names)
        # Define a set of common words to filter out (stop words)
    # Filter out stop words and numbers from feature names
        filtered_feature_names = [feature for feature in feature_names if feature not in stop_words and not feature.isdigit()]
        # Assuming we want to select the top N important feature names
    # For demonstration, let's say we want the top 3 features
    # You can replace this logic with your own importance criteria
        top_n = 6
        important_feature_names = filtered_feature_names[:top_n]  # Select top N feature names
        print("important_feature_names:{0}".format(important_feature_names));
        keyword_indices = []
        keyword_weights_sum = 0
        for keyword in keywords:
            if keyword in filtered_feature_names:
                index = filtered_feature_names.index(keyword)
                keyword_indices.append(index)
                keyword_weights = tfidf_matrix[:, index].toarray()
                print("Keyword: {0}, Index: {1}, Weight: {2}".format(keyword, index, keyword_weights))
                keyword_weights_sum += keyword_weights.sum()
        return keyword_weights_sum


class MitScraper(NewsScraper):
    """MIT Technology Review 爬虫"""
    def __init__(self):
        super().__init__("MIT Technology Review")
    
    def scrape(self):
        url = 'https://www.technologyreview.com/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        news_elements = soup.find_all(class_='homepageStoryCard__wrapper--5d95dc382241d259dc249996a6e29782')
        print(f"weight test")   
        for news_element in news_elements:
            try:
                title_elem = news_element.find(class_='homepageStoryCard__hed--92c78a74bbc694463e43e32aafbbdfd7')
                link_elem = news_element.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = link_elem['href']
                    
                    # 确保URL是完整的
                    if not url.startswith('http'):
                        url = f"https://www.technologyreview.com{url}"
                    
                    # 计算新闻权重
                    weight = self.calculate_weight(title)
                    print(f"weight is {weight}")
                    self.articles.append((title, url, weight))
            except Exception as e:
                print(f"处理文章时出错: {str(e)}")
        
        return self.filter_and_store()
    
    def calculate_weight(self, title):
        """计算新闻权重（简化版）"""
        # 这里使用您的实际权重计算逻辑
        return self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
        #return 0.3  # 示例值

class HackerNewsScraper(NewsScraper):
    """Hacker News 爬虫"""
    def __init__(self):
        #super().__init__("Hacker News")
        super().__init__("Hacker News")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.source = "Hacker News"
    def scrape(self, limit: int = 10) -> List[Dict]:
        """爬取 Hacker News 热门文章"""
        articles = []
        try:
            # 获取热门文章ID
            response = self.session.get(f"{self.base_url}/topstories.json")
            story_ids = response.json()[:limit]

            for story_id in story_ids:
                self.get_random_delay()

                # 获取文章详情
                story_response = self.session.get(f"{self.base_url}/item/{story_id}.json")
                story_data = story_response.json()

                if story_data and story_data.get('url'):
                    article = {
                        'title': story_data.get('title', ''),
                        'url': story_data.get('url', ''),
                        'summary': f"Hacker News热门文章，得分：{story_data.get('score', 0)}",
                        'source': self.source,
                        'author': story_data.get('by', ''),
                        'tags': 'Tech,News',
                        'publish_time': datetime.fromtimestamp(story_data.get('time', 0)),
                        'views': story_data.get('score', 0),
                        'likes': story_data.get('descendants', 0)
                    }
                     # 计算新闻权重
                    weight = self.calculate_weight(title)
                    self.articles.append(article,url,weight)

            print(f"成功爬取 {len(articles)} 篇 Hacker News 文章")
            return self.filter_and_store()

        except Exception as e:
            print(f"爬取 Hacker News 失败: {e}")
            return []


class TechNewsAggregator:
    """科技新闻聚合器"""
    def __init__(self):
        self.scrapers = [
            MitScraper(),
            #HackerNewsScraper(),
            # 添加其他来源的爬虫...
        ]
    
    def collect_news(self):
        """收集所有来源的新闻"""
        all_articles = []
        
        print(f"📅 开始收集科技新闻 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔍 价值阈值: > {kRankLevelValue}")
        print("-" * 60)
        
        for scraper in self.scrapers:
            print(f"\n📡 正在采集 {scraper.source_name}...")
            try:
                articles = scraper.scrape()
                print(f"✅ 找到 {len(articles)} 篇有价值文章")
                all_articles.extend(articles)
            except Exception as e:
                print(f"❌ 采集失败: {str(e)}")
        
        # 按权重排序
        all_articles.sort(key=lambda x: x[2], reverse=True)
        return all_articles
    
    def save_to_txt(self, articles, filename=OUTPUT_FILE):
        """将新闻保存到文本文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"每日科技新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"共收集到 {len(articles)} 篇高价值文章\n")
            f.write("=" * 60 + "\n\n")
            
            for idx, (title, url, weight) in enumerate(articles, 1):
                f.write(f"{idx}. [{weight:.2f}] {title}\n")
                f.write(f"   🔗 {url}\n\n")
        
        print(f"💾 新闻已保存到 {os.path.abspath(filename)}")
        return filename

def send_news_email(txt_file, recipient):
    """发送包含新闻摘要的邮件"""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib
    _pwd =encrypt_and_verify_url.decrypt_getKey("dm1wbmFmYmxsdnR0YmJlaQ==".encode("utf-8"))
    # 读取文本文件内容
    with open(txt_file, 'r', encoding='utf-8') as f:
        news_content = f.read()
    
    # 邮件配置
    sender = "840056598@qq.com"
    password = _pwd
    subject = f"每日科技新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}"
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender
    receiver = recipient 
    msg['To']=formataddr(["亲爱的用户",receiver])  #括号里的对应收件人邮箱
    msg['Subject'] = subject
    
    # 添加文本内容
    msg.attach(MIMEText(news_content, 'plain', 'utf-8'))
    print(f"send subject {subject}")
    # 创建安全上下文（解决SSL验证问题）
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # 发送邮件
    try:
        #with smtplib.SMTP_SSL('smtp.qq.com', 465, context) as server:
            #server.login(sender, _pwd.decode("utf-8"))
            #print("login email OK\n")
            #server.sendmail(sender, [receiver,], msg.as_string())
        server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
        server.login(sender,_pwd.decode("utf-8"))  #括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        print(f"📧 邮件已成功发送至 {recipient}")
        print ('SEND NEWS AND IMG OK')
        server.quit()  #这句是关闭连接
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 认证失败: 请检查邮箱和授权码是否正确")
        print("💡 提示: QQ邮箱需要使用授权码而非密码")
    except smtplib.SMTPException as e:
        print(f"❌ SMTP协议错误: {str(e)}")
        print(f"错误代码: {e.smtp_code}")
        print(f"错误消息: {e.smtp_error.decode('utf-8')}")
    except Exception as e:
        print(f"❌ 发送失败: {str(e)}")
# 主执行流程
if __name__ == "__main__":
    with open('./tech_key_config_map.json') as j:

       KEYWORDS_RANK_MAP=json.load(j)['KEYWORDS_RANK_MAP']

    # 创建聚合器并收集新闻
    aggregator = TechNewsAggregator()
    articles = aggregator.collect_news()
    
    # 保存到文本文件
    txt_file = aggregator.save_to_txt(articles)
    
    # 发送邮件
    send_news_email(txt_file, "840056598@qq.com")
    
    # 可选：清理临时文件
    # os.remove(txt_file)
