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
        self.rss_url = "https://feeds.bloomberg.com/markets/news.rss"
        self.source = "Bloomberg"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"Bloomberg RSS返回 {len(feed.entries)} 条目")
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")
                        or entry.get("description", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"Bloomberg scrape error: {e}")
            import traceback

            traceback.print_exc()
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
        self.rss_url = "https://www.economist.com/the-world-this-week/rss.xml"
        self.source = "The Economist"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"The Economist RSS返回 {len(feed.entries)} 条目")
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")
                        or entry.get("description", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"The Economist scrape error: {e}")
            import traceback

            traceback.print_exc()
        return articles


class GartnerScraper(EconomyScraper):
    """Financial Times Scraper (替代Gartner，因其网站有反爬保护)"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.ft.com/?format=rss"
        self.source = "Financial Times"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"Financial Times RSS返回 {len(feed.entries)} 条目")
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")
                        or entry.get("description", "")
                        or "Financial Times报道",
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"Financial Times scrape error: {e}")
            import traceback

            traceback.print_exc()
        return articles


class SinaFinanceScraper(EconomyScraper):
    """Sina Finance Scraper via MarketWatch RSS (fallback)"""

    def __init__(self):
        super().__init__()
        # Sina RSS不可用，使用MarketWatch作为替代
        self.rss_url = "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/"
        self.source = "MarketWatch"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"MarketWatch RSS返回 {len(feed.entries)} 条目")
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", "")
                        or entry.get("description", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                    }
                )
        except Exception as e:
            print(f"MarketWatch scrape error: {e}")
            import traceback

            traceback.print_exc()
        return articles


class CaixinScraper(EconomyScraper):
    """财新网爬虫 - 高质量深度调查报道"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.caixin.com"
        self.source = "财新网"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            # 更精确的选择器
            news_items = soup.select(".item_title a, .newslist a, h3 a, h2 a")[:50]

            seen_urls = set()
            for item in news_items:
                try:
                    title = self.clean_text(item.text)
                    url = item.get("href", "")

                    if not title or len(title) < 15 or len(title) > 150:
                        continue

                    if url and not url.startswith("http"):
                        if url.startswith("/"):
                            url = f"{self.base_url}{url}"
                        else:
                            continue

                    # 去重并确保是有效文章链接
                    if (
                        url
                        and url not in seen_urls
                        and "caixin.com" in url
                        and len(url) < 450
                    ):
                        # 过滤非文章链接
                        if any(
                            x in url for x in ["/video/", "/photo/", "/tag/", "/search"]
                        ):
                            continue

                        seen_urls.add(url)
                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"财新网深度报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": datetime.now(),
                            }
                        )

                        if len(articles) >= limit:
                            break
                except Exception as e:
                    continue

            print(f"财新网获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"财新网 scrape error: {e}")
        return articles


class WallStreetCNScraper(EconomyScraper):
    """东方财富网爬虫 - 专业财经资讯平台"""

    def __init__(self):
        super().__init__()
        self.base_url = "http://finance.eastmoney.com"
        self.source = "东方财富网"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.encoding = "gbk"
            soup = BeautifulSoup(response.content, "html.parser")

            # 东方财富网的新闻链接
            news_items = soup.select(
                'a[href*="finance.eastmoney.com"], .newsli a, .infotxt a'
            )[:50]

            seen_urls = set()
            for item in news_items:
                try:
                    title = self.clean_text(item.text)
                    url = item.get("href", "")

                    if not title or len(title) < 15 or len(title) > 150:
                        continue

                    if url and not url.startswith("http"):
                        if url.startswith("//"):
                            url = f"http:{url}"
                        elif url.startswith("/"):
                            url = f"{self.base_url}{url}"
                        else:
                            continue

                    if (
                        url
                        and url not in seen_urls
                        and "eastmoney.com" in url
                        and len(url) < 450
                    ):
                        if any(x in url for x in ["/video/", "/photo/", "/search"]):
                            continue

                        seen_urls.add(url)
                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"东方财富网报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": datetime.now(),
                            }
                        )

                        if len(articles) >= limit:
                            break
                except Exception as e:
                    continue

            print(f"东方财富网获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"东方财富网 scrape error: {e}")
        return articles


class TencentStockScraper(EconomyScraper):
    """新浪财经爬虫 - 股票财经资讯"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://finance.sina.com.cn"
        self.source = "新浪财经"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            # 新浪财经的新闻链接
            news_items = soup.select(
                'a[href*="finance.sina.com"], .feed-card-item a, .news-item a'
            )[:50]

            seen_urls = set()
            for item in news_items:
                try:
                    title = self.clean_text(item.text)
                    url = item.get("href", "")

                    if not title or len(title) < 15 or len(title) > 150:
                        continue

                    if url and not url.startswith("http"):
                        if url.startswith("//"):
                            url = f"https:{url}"
                        elif url.startswith("/"):
                            url = f"{self.base_url}{url}"
                        else:
                            continue

                    if (
                        url
                        and url not in seen_urls
                        and "sina.com" in url
                        and len(url) < 450
                    ):
                        if any(
                            x in url
                            for x in ["/video/", "/photo/", "/search", ".jpg", ".png"]
                        ):
                            continue

                        seen_urls.add(url)
                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"新浪财经报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": datetime.now(),
                            }
                        )

                        if len(articles) >= limit:
                            break
                except Exception as e:
                    continue

            print(f"新浪财经获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"新浪财经 scrape error: {e}")
        return articles
