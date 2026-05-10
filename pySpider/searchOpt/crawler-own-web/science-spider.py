## -*- coding: UTF-8 -*-
#@author: Copilot
#@date: 2026.01
# Description: Science and Mathematics News Crawler

#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import encrypt_and_verify_url
import mysqlWriteNewsV2
from email.utils import formataddr
import ssl
import json
import re
import difflib
import feedparser

# 导入日期解析工具 (处理带横杠的文件名)
try:
    main_spider = __import__('main-spider2')
    extract_date_from_url_or_title = main_spider.extract_date_from_url_or_title
except ImportError:
    # 备用：如果导入失败，定义一个简单的
    def extract_date_from_url_or_title(url, title): return None

# 读取配置（复用 tech_key_config_map.json，也可以创建专门的 science 配置）
config_path = os.path.join(os.path.dirname(__file__), '.', 'tech_key_config_map.json')
with open(config_path) as cfg_f:
    cfg = json.load(cfg_f)
KEYWORDS_RANK_MAP = cfg.get('KEYWORDS_RANK_MAP', {})
# 增加数学和科学特定权重关键词
KEYWORDS_RANK_MAP.update({
    "mathematics": 0.9, "physics": 0.8, "quantum": 0.9, "biology": 0.7,
    "astronomy": 0.7, "discovery": 0.6, "nature": 0.5, "science": 0.5,
    "proof": 0.9, "equation": 0.8, "theorem": 0.9, "imo": 0.9, "math competition": 0.9,
    "statistical": 0.6, "climate": 0.5, "population": 0.5
})

BLOCKED_DOMAINS = cfg.get('BLOCKED_DOMAINS', [])
FETCH_DETAILS_FOR_DATE = cfg.get('FETCH_DETAILS_FOR_DATE', False)

# 全局配置
OUTPUT_FILE = "science_news_summary.txt"
kRankLevelValue = 0.35  # 适度降低阈值

class NewsScraper:
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.articles = []

    def calculate_weight(self, title):
        text_lower = title.lower()
        rank = 0.0
        for key, weight in KEYWORDS_RANK_MAP.items():
            if key.lower() in text_lower:
                rank += float(weight)
        return rank

    def filter_and_store(self, category):
        filtered = []
        for title, url, weight, image_url, pub_time in self.articles:
            if weight > kRankLevelValue:
                # 1. 先检查 URL 是否已存在，避免重复写入导致的 ERROR
                if mysqlWriteNewsV2.checkUrlExists(url):
                    print(f"Skipping duplicate URL: {url}")
                    continue

                # 2. 动态调整分类：检查是否具有“趣味性”
                final_category = category
                fun_keywords = ['fun', 'puzzle', 'riddle', 'interesting', 'amazing', 'mystery', 'beauty of', '趣味', '谜题', '数字之美']
                if any(k in title.lower() for k in fun_keywords):
                    final_category = '趣说数学'

                # 写入数据库
                publish_time_str = pub_time.strftime('%Y-%m-%d_%H:%M')
                newsOne = (weight, title, self.source_name,
                          publish_time_str, 'Science and Mathematics discovery', url, 'Science,Math', final_category, image_url)
                sql = """ INSERT INTO techTB(Rate,title,author,publish_time,content,url,key_word,category,image_url) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) """
                result = mysqlWriteNewsV2.writeDb(sql, newsOne)
                if result:
                    filtered.append((title, url, weight))
        return filtered

class RSSScraper(NewsScraper):
    """通用过滤式 RSS 爬虫"""
    def __init__(self, source_name, rss_url):
        super().__init__(source_name)
        self.rss_url = rss_url

    def scrape(self):
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:15]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                # 尝试获取图片
                img = ""
                if 'media_content' in entry: img = entry['media_content'][0]['url']

                dt = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])

                weight = self.calculate_weight(title)
                self.articles.append((title, url, weight, img, dt))
            return self.filter_and_store('科学与数学')
        except Exception as e:
            print(f"{self.source_name} error: {e}")
            return []

class ScienceDailyScraper(NewsScraper):
    """ScienceDaily - Mathematics/Physics"""
    def __init__(self, section='math_computers'):
        super().__init__(f"ScienceDaily {section}")
        self.base_url = f"https://www.sciencedaily.com/news/computers_math/{section}/"
        if section == 'physics':
             self.base_url = "https://www.sciencedaily.com/news/matter_energy/physics/"

    def scrape(self):
        try:
            resp = self.session.get(self.base_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 强化选择器
            links = soup.find_all('a', href=re.compile(r'/releases/'))
            for a in links:
                title = a.get_text(strip=True)
                if len(title) < 15: continue
                url = "https://www.sciencedaily.com" + a['href']

                # 提取日期 (ScienceDaily 格式: /releases/2025/03/250308...)
                pub_time = datetime.now()
                url_date_match = re.search(r'/releases/(\d{4})/(\d{2})/(\d{2})(\d{2})(\d{2})', url)
                if url_date_match:
                    try:
                        y = int(url_date_match.group(1))
                        m = int(url_date_match.group(2))
                        d = int(url_date_match.group(5))
                        pub_time = datetime(y, m, d)
                    except:
                        pass
                else:
                    extracted = extract_date_from_url_or_title(url, title)
                    if extracted and len(extracted) >= 10:
                        try: pub_time = datetime.strptime(extracted[:10], '%Y-%m-%d')
                        except: pass

                weight = self.calculate_weight(title)
                # 排除已经处理过的（基础去重）
                if any(art[1] == url for art in self.articles): continue
                self.articles.append((title, url, weight, "", pub_time))
            return self.filter_and_store('科学与数学')
        except Exception as e:
            print(f"ScienceDaily scraper error: {e}")
            return []

class OurWorldInDataScraper(NewsScraper):
    """Our World in Data - Data driven science news"""
    def __init__(self):
        super().__init__("Our World in Data")
        self.rss_url = "https://ourworldindata.org/feed"

    def scrape(self):
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                url = entry.get('link', '')

                dt = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                else:
                    extracted = extract_date_from_url_or_title(url, title)
                    if extracted and len(extracted) >= 10:
                        try: dt = datetime.strptime(extracted[:10], '%Y-%m-%d')
                        except: pass

                weight = self.calculate_weight(title) + 0.3 # 基础加分，其数据很有价值
                self.articles.append((title, url, weight, "", dt))
            return self.filter_and_store('科学与数学')
        except Exception as e:
            print(f"OWID error: {e}")
            return []

if __name__ == "__main__":
    job_list = [
        ScienceDailyScraper('mathematics'),
        ScienceDailyScraper('physics'),
        RSSScraper("Nature", "https://www.nature.com/nature.rss"),
        RSSScraper("Science Magazine", "https://www.science.org/rss/news_current.xml"),
        RSSScraper("IMU News", "https://www.mathunion.org/news/rss"), # 国际数学联盟
        OurWorldInDataScraper()
    ]
    for s in job_list:
        print(f"\n📡 Scraping {s.source_name}...")
        results = s.scrape()
        print(f"✅ Found {len(results)} items after filtering")
