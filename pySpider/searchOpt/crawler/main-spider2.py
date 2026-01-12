## -*- coding: UTF-8 -*-
# @author: JACK YANG
# @date:
# 2022.09 add rank map
# 2024.10 scikit-learn
# 2025.07 scraper类爬虫
# 2026.01 增加python Django 前端展示数据库内容
# @Email: yyjqr789@sina.com

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
import scrapers
from email.utils import formataddr
import ssl
import json
import re
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer

# 读取配置
with open(
    os.path.join(os.path.dirname(__file__), ".", "tech_key_config_map.json")
) as cfg_f:
    cfg = json.load(cfg_f)
KEYWORDS_RANK_MAP = cfg.get("KEYWORDS_RANK_MAP", {})
BLOCKED_DOMAINS = cfg.get("BLOCKED_DOMAINS", [])
CUSTOM_SITES = cfg.get("CUSTOM_SITES", [])
# 是否在必要时请求详情页面以提取发布时间（默认 False，避免大量额外请求）
FETCH_DETAILS_FOR_DATE = cfg.get("FETCH_DETAILS_FOR_DATE", False)

# 全局配置
OUTPUT_FILE = "tech_news_summary.txt"
# KEYWORDS_RANK_MAP = {...}  # 您的关键词权重映射
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
        self.session = requests.Session()  # 添加共享的 Session 对象
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        self.base_url = ""
        self.articles = []
        self.news_index = 0

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

        # 定义分类规则
        categories = {
            "人工智能": [
                "ai",
                "intelligence",
                "learning",
                "neural",
                "gpt",
                "openai",
                "transformer",
                "robot",
            ],
            "产品类": [
                "product",
                "tesla",
                "apple",
                "google",
                "amazon",
                "chip",
                "device",
                "smart",
            ],
            "军工": [
                "missile",
                "warship",
                "drone",
                "darpa",
                "defense",
                "military",
                "unmanned",
            ],
            "社会": [
                "economic",
                "market",
                "work",
                "policy",
                "social",
                "climate",
                "sustainability",
            ],
            "科技": [],  # 默认分类
        }

        for cat, words in categories.items():
            if any(word in title_lower for word in words):
                return cat
        return "科技"

    def filter_and_store(self, keywords="科技"):
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

                # 写入数据库 (移除 Id 字段，让数据库自增)
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
        vectorizer = TfidfVectorizer()

        tfidf_matrix = vectorizer.fit_transform(texts)
        ##scikit-learn>1.0.x use this version
        feature_names = vectorizer.get_feature_names_out()
        print("test feature_names", feature_names)
        # Define a set of common words to filter out (stop words)
        # Filter out stop words and numbers from feature names
        filtered_feature_names = [
            feature
            for feature in feature_names
            if feature not in stop_words and not feature.isdigit()
        ]
        # Assuming we want to select the top N important feature names
        # For demonstration, let's say we want the top 3 features
        # You can replace this logic with your own importance criteria
        text = " ".join(texts)
        return self.compute_rank_from_map(text, keywords, fuzzy=True, threshold=0.7)
        # top_n = 6
        # important_feature_names = filtered_feature_names[:top_n]  # Select top N feature names
        # print("important_feature_names:{0}".format(important_feature_names));
        # keyword_indices = []
        # keyword_weights_sum = 0
        # for keyword in keywords:
        #     if keyword in filtered_feature_names:
        #         index = filtered_feature_names.index(keyword)
        #         keyword_indices.append(index)
        #         keyword_weights = tfidf_matrix[:, index].toarray()
        #         print("Keyword: {0}, Index: {1}, Weight: {2}".format(keyword, index, keyword_weights))
        #         keyword_weights_sum += keyword_weights.sum()
        # return keyword_weights_sum


class MitScraper(NewsScraper):
    """MIT Technology Review 爬虫"""

    def __init__(self):
        super().__init__("MIT Technology Review")

    def scrape(self):
        url = "https://www.technologyreview.com/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        news_elements = soup.find_all(
            class_="homepageStoryCard__wrapper--5d95dc382241d259dc249996a6e29782"
        )
        print(f"weight test")
        for news_element in news_elements:
            try:
                title_elem = news_element.find(
                    class_="homepageStoryCard__hed--92c78a74bbc694463e43e32aafbbdfd7"
                )
                link_elem = news_element.find("a")

                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = link_elem["href"]

                    # 确保URL是完整的
                    if not url.startswith("http"):
                        url = f"https://www.technologyreview.com{url}"

                    # 计算新闻权重
                    weight = self.calculate_weight(title)
                    if weight > 0:
                        print(f"weight is {weight}")
                        self.articles.append((title, url, weight))
            except Exception as e:
                print(f"处理文章时出错: {str(e)}")

        return self.filter_and_store("MIT科技评论")


class HackerNewsScraper(NewsScraper):
    """Hacker News 爬虫"""

    def __init__(self):
        # super().__init__("Hacker News")
        super().__init__("Hacker News")
        self.base_url = "https://hacker-news.firebaseio.com/v0"

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
                story_response = self.session.get(
                    f"{self.base_url}/item/{story_id}.json"
                )
                story_data = story_response.json()

                if story_data and story_data.get("url"):
                    article = {
                        "title": story_data.get("title", ""),
                        "url": story_data.get("url", ""),
                        "summary": f"Hacker News热门文章，得分：{story_data.get('score', 0)}",
                        "source": self.source_name,
                        "author": story_data.get("by", ""),
                        "tags": "Tech,News",
                        "publish_time": datetime.fromtimestamp(
                            story_data.get("time", 0)
                        ),
                        "views": story_data.get("score", 0),
                        "likes": story_data.get("descendants", 0),
                    }
                    # 计算新闻权重
                    weight = self.calculate_weight(article["title"])
                    self.articles.append((article["title"], article["url"], weight))

            print(f"成功爬取 {len(self.articles)} 篇 Hacker News 文章")
            return self.filter_and_store("Hacker News")

        except Exception as e:
            print(f"爬取 Hacker News 失败: {e}")
            return []


class GitHubTrendingScraper(NewsScraper):
    """GitHub Trending 爬虫包装器"""

    def __init__(self):
        super().__init__("GitHub Trending")
        self.scraper = scrapers.GitHubTrendingScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("GitHub")
        except Exception as e:
            print(f"GitHub 爬取失败: {e}")
            return []


class RedditScraper(NewsScraper):
    """Reddit 爬虫包装器"""

    def __init__(self):
        super().__init__("Reddit Programming")
        self.scraper = scrapers.RedditScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("Reddit")
        except Exception as e:
            print(f"Reddit 爬取失败: {e}")
            return []


class DevToScraper(NewsScraper):
    """Dev.to 爬虫包装器"""

    def __init__(self):
        super().__init__("Dev.to")
        self.scraper = scrapers.DevToScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("Dev.to")
        except Exception as e:
            print(f"Dev.to 爬取失败: {e}")
            return []


class AITopicsScraper(NewsScraper):
    """AI Topics 爬虫包装器"""

    def __init__(self):
        super().__init__("AI Topics")
        self.scraper = scrapers.AITopicsScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("人工智能")
        except Exception as e:
            print(f"AI Topics 爬取失败: {e}")
            return []


class MediumScraper(NewsScraper):
    """Medium 爬虫包装器"""

    def __init__(self):
        super().__init__("Medium Technology")
        self.scraper = scrapers.MediumScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("Medium")
        except Exception as e:
            print(f"Medium 爬取失败: {e}")
            return []


class TechCrunchScraper(NewsScraper):
    """TechCrunch 爬虫包装器"""

    def __init__(self):
        super().__init__("TechCrunch")
        self.scraper = scrapers.TechCrunchScraper()

    def scrape(self, limit=10):
        try:
            articles = self.scraper.scrape_articles(limit=limit)
            for art in articles:
                weight = self.calculate_weight(art["title"])
                self.articles.append((art["title"], art["url"], weight))
            return self.filter_and_store("TechCrunch")
        except Exception as e:
            print(f"TechCrunch 爬取失败: {e}")
            return []


class TechNewsAggregator:
    """科技新闻聚合器"""

    def __init__(self):
        self.scrapers = [
            MitScraper(),
            GitHubTrendingScraper(),
            AITopicsScraper(),
            DevToScraper(),
            RedditScraper(),
            HackerNewsScraper(),
            MediumScraper() if "MediumScraper" in globals() else None,
            TechCrunchScraper() if "TechCrunchScraper" in globals() else None,
        ]
        # 过滤掉未定义的爬虫
        self.scrapers = [s for s in self.scrapers if s is not None]

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
        with open(filename, "w", encoding="utf-8") as f:
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

    _pwd = encrypt_and_verify_url.decrypt_getKey(
        "dm1wbmFmYmxsdnR0YmJlXX==".encode("utf-8")
    )
    # 读取文本文件内容
    with open(txt_file, "r", encoding="utf-8") as f:
        news_content = f.read()

    # 邮件配置
    sender = "840056598@qq.com"
    password = _pwd
    subject = f"每日科技新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}"

    # 创建邮件
    msg = MIMEMultipart()
    msg["From"] = sender
    receiver = recipient
    msg["To"] = formataddr(["亲爱的用户", receiver])  # 括号里的对应收件人邮箱
    msg["Subject"] = subject

    # 添加文本内容
    msg.attach(MIMEText(news_content, "plain", "utf-8"))
    print(f"send subject {subject}")
    # 创建安全上下文（解决SSL验证问题）
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # 发送邮件
    try:
        # with smtplib.SMTP_SSL('smtp.qq.com', 465, context) as server:
        # server.login(sender, _pwd.decode("utf-8"))
        # print("login email OK\n")
        # server.sendmail(sender, [receiver,], msg.as_string())
        server = smtplib.SMTP_SSL(
            "smtp.qq.com", 465
        )  # 发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
        server.login(sender, _pwd.decode("utf-8"))  # 括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(
            sender,
            [
                receiver,
            ],
            msg.as_string(),
        )  # 括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        print(f"📧 邮件已成功发送至 {recipient}")
        print("SEND NEWS AND IMG OK")
        server.quit()  # 这句是关闭连接
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
    with open("./tech_key_config_map.json") as j:

        KEYWORDS_RANK_MAP = json.load(j)["KEYWORDS_RANK_MAP"]

    # 创建聚合器并收集新闻
    aggregator = TechNewsAggregator()
    articles = aggregator.collect_news()

    # 保存到文本文件
    txt_file = aggregator.save_to_txt(articles)

    # 发送邮件（除非 dry-run）
    # if args.dry_run:
    # print("--dry-run: 跳过发送邮件")
    # else:
    send_news_email(txt_file, "840056598@qq.com")

    # 可选：清理临时文件
    # os.remove(txt_file)

