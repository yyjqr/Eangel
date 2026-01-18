## -*- coding: UTF-8 -*-
# @author: Copilot
# @date: 2026.01
# Description: Economic and Enterprise News Crawler

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
import scrapers_economy as scrapers
from email.utils import formataddr
import ssl
import json
import re
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer

# 读取配置
with open(
    os.path.join(os.path.dirname(__file__), ".", "economy_key_config_map.json")
) as cfg_f:
    cfg = json.load(cfg_f)
KEYWORDS_RANK_MAP = cfg.get("KEYWORDS_RANK_MAP", {})
BLOCKED_DOMAINS = cfg.get("BLOCKED_DOMAINS", [])
CUSTOM_SITES = cfg.get("CUSTOM_SITES", [])
# 是否在必要时请求详情页面以提取发布时间
FETCH_DETAILS_FOR_DATE = cfg.get("FETCH_DETAILS_FOR_DATE", False)

# 全局配置
OUTPUT_FILE = "economy_news_summary.txt"
# 新闻价值阈值
kRankLevelValue = cfg.get("RANK_THRESHOLD", 0.5)

# Define a set of common words to filter out (stop words)
stop_words = set(
    [
        "is",
        "the",
        "this",
        "and",
        "a",
        "to",
        "of",
        "in",
        "for",
        "on",
        "if",
        "has",
        "are",
        "was",
        "be",
        "by",
        "at",
        "that",
        "it",
        "its",
        "as",
        "about",
        "an",
        "or",
        "but",
        "not",
        "from",
        "with",
        "which",
        "there",
        "when",
        "so",
        "all",
        "any",
        "some",
        "one",
        "two",
        "three",
        "four",
        "five",
    ]
)


class NewsScraper:
    """通用新闻爬虫基类"""

    def __init__(self, source_name):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        self.base_url = ""
        self.articles = []

    def scrape(self):
        """子类需实现的具体爬取逻辑"""
        raise NotImplementedError("子类必须实现 scrape 方法")

    def get_random_delay(self):
        """随机延迟，避免被封"""
        time.sleep(random.uniform(1, 3))

    def calculate_weight(self, title):
        """计算新闻权重"""
        return self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)

    def determine_category(self, title, keywords):
        """根据标题和关键词确定文章分类"""
        title_lower = title.lower()

        # 定义经济分类规则
        categories = {
            "宏观经济": [
                "gdp",
                "inflation",
                "fed",
                "imf",
                "policy",
                "rate",
                "tax",
                "economy",
                "macro",
            ],
            "股市投资": [
                "stock",
                "market",
                "nasdaq",
                "dow",
                "ipo",
                "earnings",
                "fund",
                "invest",
            ],
            "企业动态": [
                "merger",
                "acquisition",
                "ceo",
                "layoff",
                "report",
                "microsoft",
                "apple",
                "tesla",
                "google",
                "amazon",
            ],
            "金融科技": ["fintech", "crypto", "bitcoin", "blockchain", "bank", "payment"],
            "贸易与供应链": [
                "trade",
                "tariff",
                "supply chain",
                "freight",
                "export",
                "import",
            ],
            "经济评论": ["opinion", "analysis", "forecast", "outlook", "trend"],
        }

        for cat, words in categories.items():
            if any(word in title_lower for word in words):
                return cat
        return "经济综合"

    def filter_and_store(self, keywords="经济"):
        """过滤并存储符合条件的文章"""
        filtered_articles = []
        current_date = datetime.now()
        six_months_ago = current_date - timedelta(days=180)

        for title, url, weight in self.articles:
            if weight > kRankLevelValue:
                # 检查URL是否已存在
                db_publish_time_str = mysqlWriteNewsV2.getArticlePublishTime(url)

                if db_publish_time_str:
                    try:
                        # 尝试解析数据库中的时间格式 %Y-%m-%d_%H:%M
                        db_publish_time = datetime.strptime(
                            db_publish_time_str, "%Y-%m-%d_%H:%M"
                        )
                        if db_publish_time < six_months_ago:
                            print(f"文章已超过半年，不再发送: {url}")
                            continue
                        else:
                            print(f"文章已在数据库但未满半年，继续发送: {title[:50]}...")
                            filtered_articles.append((title, url, weight))
                            continue
                    except Exception as e:
                        print(f"解析数据库时间失败: {e}, 默认跳过")
                        continue

                filtered_articles.append((title, url, weight))

                # 确定分类
                category = self.determine_category(title, keywords)

                # 写入数据库
                publish_time = datetime.now().strftime("%Y-%m-%d_%H:%M")
                newsOne = (
                    weight,
                    title,
                    self.source_name,
                    publish_time,
                    "content",
                    url,
                    keywords,
                    category,
                )
                sql = """ INSERT INTO techTB(Rate,title,author,publish_time,content,url,key_word,category) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) """
                result = mysqlWriteNewsV2.writeDb(sql, newsOne)
                if result:
                    print(f"✅ 成功写入数据库 [{category}]: {title[:50]}...")
                else:
                    print(f"❌ 写入数据库失败: {title[:50]}...")

        return filtered_articles

    def compute_rank_from_map(self, text, key_map, fuzzy=False, threshold=0.8):
        if not text or not key_map:
            return 0.0
        text_lower = re.sub(r"\W+", " ", text).lower()
        tokens = text_lower.split()
        rank = 0.0
        for key, weight in key_map.items():
            try:
                key_l = key.lower()
            except Exception:
                continue
            if key_l in text_lower:
                rank += float(weight)
            elif fuzzy:
                seq = difflib.SequenceMatcher(None, key_l, text_lower)
                if seq.ratio() >= threshold:
                    rank += float(weight) * seq.ratio()
                else:
                    for t in tokens:
                        seq2 = difflib.SequenceMatcher(None, key_l, t)
                        if seq2.ratio() >= threshold:
                            rank += float(weight) * seq2.ratio()
                            break
        return float(rank)

    # 计算关键词权重
    def calculate_keyword_weights(self, texts, keywords):
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
        except:
            # Fallback if TF-IDF fails (e.g. empty texts)
            text = " ".join(texts)
            return self.compute_rank_from_map(text, keywords, fuzzy=True, threshold=0.7)

        text = " ".join(texts)
        return self.compute_rank_from_map(text, keywords, fuzzy=True, threshold=0.7)


class BloombergWrapper(NewsScraper):
    def __init__(self):
        super().__init__("Bloomberg")
        self.scraper = scrapers.BloombergScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("Bloomberg")
        except Exception as e:
            print(f"Bloomberg 爬取失败: {e}")
            return []


class CNBCWrapper(NewsScraper):
    def __init__(self):
        super().__init__("CNBC")
        self.scraper = scrapers.CNBCScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("CNBC")
        except Exception as e:
            print(f"CNBC 爬取失败: {e}")
            return []


class EconomistWrapper(NewsScraper):
    def __init__(self):
        super().__init__("The Economist")
        self.scraper = scrapers.EconomistScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("The Economist")
        except Exception as e:
            print(f"The Economist 爬取失败: {e}")
            return []


class GartnerWrapper(NewsScraper):
    def __init__(self):
        super().__init__("Gartner")
        self.scraper = scrapers.GartnerScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("Gartner")
        except Exception as e:
            print(f"Gartner 爬取失败: {e}")
            return []


class SinaWrapper(NewsScraper):
    def __init__(self):
        super().__init__("Sina Finance")
        self.scraper = scrapers.SinaFinanceScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("新浪财经")
        except Exception as e:
            print(f"新浪财经 爬取失败: {e}")
            return []


class CaixinWrapper(NewsScraper):
    def __init__(self):
        super().__init__("财新网")
        self.scraper = scrapers.CaixinScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("财新网")
        except Exception as e:
            print(f"财新网 爬取失败: {e}")
            return []


class WallStreetCNWrapper(NewsScraper):
    def __init__(self):
        super().__init__("东方财富网")
        self.scraper = scrapers.WallStreetCNScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("东方财富网")
        except Exception as e:
            print(f"东方财富网 爬取失败: {e}")
            return []


class TencentStockWrapper(NewsScraper):
    def __init__(self):
        super().__init__("新浪财经")
        self.scraper = scrapers.TencentStockScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("新浪财经")
        except Exception as e:
            print(f"新浪财经 爬取失败: {e}")
            return []


class EconomyNewsAggregator:
    """经济新闻聚合器"""

    def __init__(self):
        self.scrapers = [
            BloombergWrapper(),
            CNBCWrapper(),
            EconomistWrapper(),
            GartnerWrapper(),
            SinaWrapper(),
            CaixinWrapper(),
            WallStreetCNWrapper(),
            TencentStockWrapper(),
        ]

    def collect_news(self):
        """收集所有来源的新闻"""
        all_articles = []

        print(f"📅 开始收集经济新闻 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"每日经济新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}\n")
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

    try:
        _pwd = encrypt_and_verify_url.decrypt_getKey(
            "dm1wbmFmYmxsdnR0YmJlaQ==".encode("utf-8")
        )
    except:
        print("Decrypt key failed, skipping email.")
        return

    # 读取文本文件内容
    with open(txt_file, "r", encoding="utf-8") as f:
        news_content = f.read()

    # 邮件配置
    sender = "840056598@qq.com"
    subject = f"每日经济新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}"

    # 创建邮件
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = formataddr(["亲爱的用户", recipient])
    msg["Subject"] = subject

    # 添加文本内容
    msg.attach(MIMEText(news_content, "plain", "utf-8"))

    # 发送邮件
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, _pwd.decode("utf-8"))
        server.sendmail(
            sender,
            [
                recipient,
            ],
            msg.as_string(),
        )
        print(f"📧 邮件已成功发送至 {recipient}")
        server.quit()
        return True
    except Exception as e:
        print(f"❌ 发送失败: {str(e)}")


# 主执行流程
if __name__ == "__main__":
    # 创建聚合器并收集新闻
    aggregator = EconomyNewsAggregator()
    articles = aggregator.collect_news()

    # 保存到文本文件
    txt_file = aggregator.save_to_txt(articles)

    # 发送邮件
    send_news_email(txt_file, "840056598@qq.com")
