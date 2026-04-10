import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
import time
import random
from fake_useragent import UserAgent
from typing import List, Dict, Optional
import re


class EconomyScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )

    def get_random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    def resolve_google_news_link(self, url: str) -> str:
        """Resolve Google News redirect URLs to original source"""
        if "news.google.com" not in url and "google.com/news" not in url:
            return url
        try:
            resp = self.session.get(url, allow_redirects=True, timeout=10)
            return resp.url
        except Exception:
            return url


class BloombergScraper(EconomyScraper):
    """Bloomberg Scraper (direct RSS)"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.bloomberg.com/feed/podcast/etf-report.xml"
        self.source = "Bloomberg"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                original_url = self.resolve_google_news_link(entry.link)
                articles.append(
                    {
                        "title": entry.title,
                        "url": original_url,
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed")
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"Bloomberg scrape error: {e}")
        return articles


class CNBCScraper(EconomyScraper):
    """CNBC Scraper via RSS"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"  # Finance
        self.source = "CNBC"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.title,
                        "url": entry.link,
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed")
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"CNBC scrape error: {e}")
        return articles


class EconomistScraper(EconomyScraper):
    """The Economist Scraper (direct RSS)"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.economist.com/rss"
        self.source = "The Economist"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                original_url = self.resolve_google_news_link(entry.link)
                articles.append(
                    {
                        "title": entry.title,
                        "url": original_url,
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed")
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"The Economist scrape error: {e}")
        return articles


class GartnerScraper(EconomyScraper):
    """Gartner Scraper (direct website access)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.gartner.com/en"
        self.source = "Gartner"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 直接访问Gartner的新闻页面
            news_url = f"{self.base_url}/newsroom"
            response = self.session.get(news_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找新闻文章
            news_items = soup.select("article.gartner-card, .news-item, .article-card")[
                :limit
            ]

            for item in news_items:
                try:
                    title_elem = item.select_one("h2 a, h3 a, .title a, a.headline")
                    if not title_elem:
                        continue

                    title = self.clean_text(title_elem.text)
                    url = title_elem.get("href", "")
                    if url and not url.startswith("http"):
                        url = f"https://www.gartner.com{url}"

                    summary_elem = item.select_one("p, .summary, .description")
                    summary = self.clean_text(summary_elem.text) if summary_elem else ""

                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": summary or "Gartner研究报告",
                            "source": self.source,
                            "publish_time": datetime.now(),
                        }
                    )
                except Exception as e:
                    print(f"解析Gartner文章失败: {e}")
                    continue

        except Exception as e:
            print(f"Gartner scrape error: {e}")
        return articles


class SinaFinanceScraper(EconomyScraper):
    """Sina Finance Scraper via RSS"""

    def __init__(self):
        super().__init__()
        self.rss_url = "http://rss.sina.com.cn/roll/finance/hot_roll.xml"
        self.source = "Sina Finance"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.title,
                        "url": entry.link,
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed")
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"Sina Finance scrape error: {e}")
        return articles
