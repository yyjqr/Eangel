## -*- coding: UTF-8 -*-
#@author: Copilot
#@date: 2026.01
# Description: Design, Creativity and Hardware News Crawler

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
import scrapers_design as scrapers
from email.utils import formataddr
import ssl
import json
import re
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer

# 读取配置
config_path = os.path.join(os.path.dirname(__file__), '.', 'tech_key_config_map.json')
if os.path.exists(config_path):
    with open(config_path) as cfg_f:
        cfg = json.load(cfg_f)
else:
    cfg = {}

KEYWORDS_RANK_MAP = cfg.get('KEYWORDS_RANK_MAP', {})
# 为设计/硬件增加一些默认权重，如果配置中没有
design_defaults = {
    "design": 0.8, "award": 0.9, "creative": 0.8, "style": 0.7, "concept": 0.9,
    "supercar": 1.0, "hypercar": 1.0, "industrial": 0.7, "architecture": 0.6,
    "红点": 1.2, "iF设计": 1.2, "工业设计": 1.0, "造型": 0.8, "创意": 0.8,
    "超跑": 1.2, "奢华": 0.8, "奢侈品": 0.9, "硬件": 0.7, "汽车": 0.6, "旗舰": 0.7,
    "robot":1.2, "robotics":1.0, "drone":0.8, "3D printing":0.9, "wearable":0.7,
    "vehicle":0.6, "automotive":0.7, "smartphone":0.5, "laptop":0.5, "camera":0.6,
    "flight":0.8, "drone":0.7, "ev":0.9, "electric vehicle":0.9, "autonomous":0.8
}
for k, v in design_defaults.items():
    if k not in KEYWORDS_RANK_MAP:
        KEYWORDS_RANK_MAP[k] = v

BLOCKED_DOMAINS = cfg.get('BLOCKED_DOMAINS', [])
kRankLevelValue = cfg.get('RANK_THRESHOLD', 1.0) # 设计类阈值稍微调低一点，因为关键词可能没那么密集

stop_words = set([
    "is", "the", "this", "and", "a", "to", "of", "in", "for", "on",
    "if", "has", "are", "was", "be", "by", "at", "that", "it", "its",
    "as","about", "an", "or", "but", "not", "from", "with", "which",
    "there", "when", "so", "all", "any", "some", "one", "two"
])

class NewsScraper:
    """通用新闻爬虫基类"""
    def __init__(self, source_name):
        self.source_name = source_name
        self.articles = []

    def calculate_weight(self, title):
        """计算新闻权重"""
        return self.compute_rank_from_map(title, KEYWORDS_RANK_MAP, fuzzy=True, threshold=0.7)

    def determine_category(self, title, source_name):
        """根据标题和来源确定文章分类"""
        title_lower = title.lower()

        # 硬件/汽车 分类关键词
        hardware_words = [
            'car', 'automotive', 'vehicle', 'concept', 'hardware', 'device', 'gadget',
            'supercar', 'hypercar', 'watch', 'luxury', 'engine', 'motor', 'smartphone',
            'laptop', 'camera', '超跑', '奢侈品', '硬件', '汽车', '自动驾驶', '摩托',
            '座驾', '旗舰', '手机', '电脑', '相机', '显卡', 'EV', 'electric vehicle',
            'hyper-car', 'luxury watch', 'precision', 'craftsmanship'
        ]

        # 如果来源本身就是汽车类
        if source_name == "Car Design News":
            return '硬件/汽车'

        if any(word in title_lower for word in hardware_words):
            return '硬件/汽车'

        # 默认归类为 设计/创意
        return '设计/创意'

    def filter_and_store(self, keywords='设计'):
        """过滤并存储符合条件的文章"""
        filtered_articles = []
        current_date = datetime.now()
        six_months_ago = current_date - timedelta(days=180)

        for item in self.articles:
            # 兼容不同长度的元组
            image_url = ""
            publish_time_obj = datetime.now()
            created_at_obj = datetime.now()

            if len(item) == 6:
                title, url, weight, image_url, publish_time_obj, created_at_obj = item
            elif len(item) == 4:
                title, url, weight, image_url = item
            elif len(item) == 3:
                title, url, weight = item
            else:
                continue

            if weight > kRankLevelValue:
                # 过滤过长的URL和标题，防止数据库报错
                if len(url) > 250:
                    print(f"⚠️ URL过长 ({len(url)})，跳过: {url[:50]}...")
                    continue

                if len(title) > 250:
                    title = title[:245] + "..."

                # 检查URL是否已存在
                db_publish_time_str = mysqlWriteNewsV2.getArticlePublishTime(url)

                if db_publish_time_str:
                    try:
                        # 尝试解析数据库中的时间格式 %Y-%m-%d_%H:%M
                        db_publish_time = datetime.strptime(db_publish_time_str, '%Y-%m-%d_%H:%M')
                        if db_publish_time < six_months_ago:
                            print(f"文章已超过半年，不再发送: {url}")
                            continue
                        else:
                            print(f"文章已在数据库但未满半年，继续发送: {title[:30]}...")
                            filtered_articles.append((title, url, weight, image_url, publish_time_obj, created_at_obj))
                            continue
                    except Exception:
                        pass

                # 确定分类
                category = self.determine_category(title, self.source_name)

                # 写入数据库 (包含 image_url)
                if not isinstance(publish_time_obj, datetime):
                    publish_time_obj = datetime.now()

                publish_time_str = publish_time_obj.strftime('%Y-%m-%d_%H:%M')
                content = f"来自 {self.source_name} 的{category}内容"

                newsOne = (weight, title, self.source_name,
                          publish_time_str, content, url, keywords, category, image_url)

                sql = """ INSERT INTO techTB(Rate,title,author,publish_time,content,url,key_word,category,image_url)
                          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) """

                result = mysqlWriteNewsV2.writeDb(sql, newsOne)
                if result:
                    print(f"✅ 成功写入 [{category}]: {title[:50]}...")
                    filtered_articles.append((title, url, weight, image_url, publish_time_obj, created_at_obj))
                else:
                    print(f"❌ 写入失败: {title[:50]}...")

        return filtered_articles

    def compute_rank_from_map(self, text, key_map, fuzzy=False, threshold=0.8):
        if not text or not key_map:
            return 0.0
        text_lower = re.sub(r'\W+', ' ', text).lower()
        tokens = text_lower.split()
        rank = 0.0
        for key, weight in key_map.items():
            if not isinstance(key, str): continue
            key_l = key.lower()
            if key_l in text_lower:
                rank += float(weight)
            elif fuzzy:
                # 简单的模糊匹配增强
                if len(key_l) > 3 and key_l[:4] in text_lower:
                    rank += float(weight) * 0.5
        return float(rank)

class GenericDesignWrapper(NewsScraper):
    def __init__(self, scraper_class, source_name):
        super().__init__(source_name)
        self.scraper = scraper_class()

    def scrape(self, limit=15):
        try:
            print(f"\n开始抓取 {self.source_name}...")
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art['title'])
                # 给设计类来源一定的基础分
                weight += 0.5
                self.articles.append((art['title'], art['url'], weight, art.get('image_url', ''), art.get('publish_time', datetime.now()), art.get('created_at', datetime.now())))

            # 返回过滤后的文章列表，用于汇总
            return self.filter_and_store(self.source_name)
        except Exception as e:
            print(f"{self.source_name} 抓取异常: {e}")
            return []

class DesignNewsAggregator:
    """设计新闻聚合与输出类"""
    def __init__(self, filename="design_news_summary.txt"):
        self.filename = filename

    def save_to_txt(self, articles):
        """将新闻保存到文本文件"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(f"每日设计与创意新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"共收集到 {len(articles)} 篇高价值文章\n")
            f.write("=" * 60 + "\n\n")

            for idx, article in enumerate(articles, 1):
                image_url = ""
                publish_time = None
                created_at = None

                if len(article) == 6:
                    title, url, weight, image_url, publish_time, created_at = article
                elif len(article) == 4:
                    title, url, weight, image_url = article
                else:
                    title, url, weight = article

                f.write(f"{idx}. [{weight:.2f}] {title}\n")
                f.write(f"   🔗 {url}\n")
                if isinstance(publish_time, datetime):
                     f.write(f"   📅 发布时间: {publish_time.strftime('%Y-%m-%d %H:%M')}\n")
                if isinstance(created_at, datetime):
                     f.write(f"   🕒 采集时间: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if image_url:
                    f.write(f"   🖼️ {image_url}\n")
                f.write("\n")

        print(f"💾 新闻已保存到 {os.path.abspath(self.filename)}")
        return self.filename

def send_news_email(txt_file, recipient):
    """发送包含新闻摘要的邮件"""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    try:
        # 解密获取授权码
        _pwd = encrypt_and_verify_url.decrypt_getKey("dm1wbmFmYmxsdnR0YmJlaQ==".encode("utf-8"))

        # 读取内容
        with open(txt_file, 'r', encoding='utf-8') as f:
            news_content = f.read()

        sender = "840056598@qq.com"
        subject = f"每日设计与创意摘要 - {datetime.now().strftime('%Y-%m-%d')}"

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = formataddr(["亲爱的设计爱好者", recipient])
        msg['Subject'] = subject
        msg.attach(MIMEText(news_content, 'plain', 'utf-8'))

        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, _pwd.decode("utf-8"))
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()

        print(f"📧 邮件已成功发送至 {recipient}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False

def main():
    print(f"=== 设计与创意新闻采集任务开始: {datetime.now()} ===")

    scrapers_to_run = [
        (scrapers.YankoDesignScraper, "Yanko Design"),
        (scrapers.IDEAScraper, "IDEA Awards"),
        (scrapers.CoreDesignScraper, "Core77"),
        (scrapers.RedDotScraper, "Red Dot Award"),
        (scrapers.IFDesignScraper, "iF Design Award"),
        (scrapers.DesignboomScraper, "Designboom"),
        (scrapers.PopularMechanicsScraper, "Popular Mechanics"),
        (scrapers.DezeenScraper, "Dezeen"),
        (scrapers.MakezineScraper, "Makezine"),
        (scrapers.InfoQProductScraper, "InfoQ Product"),
        (scrapers.ProductHuntScraper, "Product Hunt"),

        (scrapers.CarDesignNewsScraper, "Car Design News"),
        (scrapers.LeManooshScraper, "leManoosh"),
        (scrapers.BehanceScraper, "Behance"),
        (scrapers.LVMHScraper, "LVMH"),
        (scrapers.KeringScraper, "Kering"),
        (scrapers.CarBuzzScraper, "CarBuzz"),
        (scrapers.CarAndDriverScraper, "Car and Driver")

    ]

    all_articles = []
    total_count = 0
    for scraper_cls, name in scrapers_to_run:
        wrapper = GenericDesignWrapper(scraper_cls, name)
        results = wrapper.scrape(limit=12)
        all_articles.extend(results)
        # 避免请求过快
        time.sleep(2)

    print(f"\n=== 采集任务结束. 共新增 {len(all_articles)} 条高价值记录 ===")

    if all_articles:
        # 按权重排序
        all_articles.sort(key=lambda x: x[2], reverse=True)

        aggregator = DesignNewsAggregator()
        txt_file = aggregator.save_to_txt(all_articles)

        # 发送邮件
        send_news_email(txt_file, "840056598@qq.com")
    else:
        print("今日无新增高价值设计资讯。")

if __name__ == "__main__":
    main()
