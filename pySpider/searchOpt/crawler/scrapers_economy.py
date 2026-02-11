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

    def extract_publish_time(self, time_str: str) -> Optional[datetime]:
        """提取发布时间"""
        try:
            if not time_str:
                return None

            # 尝试提取日期 (simple regex for YYYY-MM-DD or similar)
            match = re.search(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})", time_str)
            if match:
                try:
                    return datetime(
                        int(match.group(1)), int(match.group(2)), int(match.group(3))
                    )
                except ValueError:
                    pass
            return None
        except:
            return None

    def extract_rss_image(self, entry) -> str:
        """从 RSS 条目中提取图片链接"""
        image_url = ""
        if "media_content" in entry:
            image_url = entry["media_content"][0]["url"]
        elif "links" in entry:
            for link in entry["links"]:
                if link.get("type", "").startswith("image/"):
                    image_url = link.get("href", "")
                    break
        return image_url

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
                        "created_at": datetime.now(),
                        "image_url": self.extract_rss_image(entry),
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
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "created_at": datetime.now(),
                        "image_url": self.extract_rss_image(entry),
                    }
                )
        except Exception as e:
            print(f"CNBC scrape error: {e}")
        return articles


class FinancialTimesScraper(EconomyScraper):
    """Financial Times Scraper via RSS"""

    def __init__(self):
        super().__init__()
        # Global Economy RSS
        self.rss_url = "https://www.ft.com/global-economy?format=rss"
        self.source = "Financial Times"

    def scrape_articles(self, limit: int = 15) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"Financial Times RSS返回 {len(feed.entries)} 条目")
            for entry in feed.entries[:limit]:
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "created_at": datetime.now(),
                        "image_url": self.extract_rss_image(entry),
                    }
                )
        except Exception as e:
            print(f"FT scrape error: {e}")
        return articles

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
                        "created_at": datetime.now(),
                        "image_url": self.extract_rss_image(entry),
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
                        "created_at": datetime.now(),
                        "image_url": self.extract_rss_image(entry),
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
                        "created_at": datetime.now(),
                    }
                )
        except Exception as e:
            print(f"Financial Times scrape error: {e}")
            import traceback

            traceback.print_exc()
        return articles


class SinaFinanceScraper(EconomyScraper):
    """新浪财经爬虫 - 综合财经资讯"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://finance.sina.com.cn"
        self.rss_url = "https://finance.sina.com.cn/roll/index.d.html"  # 滚动新闻页面
        self.source = "新浪财经"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 尝试从滚动新闻页面获取
            response = self.session.get(self.rss_url, timeout=15)
            response.encoding = "gb2312"  # 新浪财经使用gb2312编码
            soup = BeautifulSoup(response.content, "html.parser")

            # 更精确的选择器 - 新浪财经滚动新闻
            news_items = soup.select(
                ".list_009 li a, .feed-card-title-link, .news-item a"
            )[:100]

            seen_urls = set()
            for item in news_items:
                try:
                    title = self.clean_text(item.text)
                    url = item.get("href", "")

                    if not title or len(title) < 10 or len(title) > 200:
                        continue

                    # URL处理
                    if url and not url.startswith("http"):
                        if url.startswith("//"):
                            url = f"https:{url}"
                        elif url.startswith("/"):
                            url = f"https://finance.sina.com.cn{url}"
                        else:
                            continue

                    # 确保是新浪财经的文章链接
                    if (
                        url
                        and url not in seen_urls
                        and "sina.com.cn" in url
                        and len(url) < 500
                    ):
                        # 过滤非文章链接
                        if any(
                            x in url
                            for x in [
                                "/video/",
                                "/photo/",
                                "/search",
                                ".jpg",
                                ".png",
                                "/tag/",
                                "/api/",
                            ]
                        ):
                            continue

                        # 确保是财经相关的URL
                        if (
                            "finance.sina.com.cn" in url
                            or "money.sina.com.cn" in url
                            or "stock.finance.sina.com.cn" in url
                        ):
                            seen_urls.add(url)

                            articles.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "summary": f"新浪财经报道: {title[:80]}",
                                    "source": self.source,
                                    "publish_time": datetime.now(),  # 滚动新闻默认为当前时间
                                    "created_at": datetime.now(),
                                    "image_url": "",
                                }
                            )

                            if len(articles) >= limit:
                                break
                except Exception as e:
                    continue

            # 如果滚动新闻获取失败，尝试首页
            if len(articles) < limit:
                try:
                    response = self.session.get(self.base_url, timeout=15)
                    response.encoding = "utf-8"
                    soup = BeautifulSoup(response.content, "html.parser")

                    # 首页新闻链接
                    news_items = soup.select('a[href*="finance.sina.com.cn"]')[:100]

                    for item in news_items:
                        if len(articles) >= limit:
                            break
                        try:
                            title = self.clean_text(item.text)
                            url = item.get("href", "")

                            if not title or len(title) < 10 or url in seen_urls:
                                continue

                            if "finance.sina.com.cn" in url and not any(
                                x in url for x in ["/video/", "/photo/", ".jpg"]
                            ):
                                seen_urls.add(url)
                                articles.append(
                                    {
                                        "title": title,
                                        "url": url,
                                        "summary": f"新浪财经: {title[:80]}",
                                        "source": self.source,
                                        "publish_time": datetime.now(),
                                        "created_at": datetime.now(),
                                        "image_url": "",
                                    }
                                )
                        except:
                            continue
                except Exception as e:
                    print(f"新浪财经首页抓取失败: {e}")

            print(f"新浪财经获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"新浪财经 scrape error: {e}")
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

                        # 提取图片
                        image_url = ""
                        img_tag = (
                            item.find_next("img")
                            if hasattr(item, "find_next")
                            else None
                        )
                        if not img_tag:
                            parent = item.find_parent()
                            img_tag = parent.find("img") if parent else None
                        if img_tag:
                            image_url = img_tag.get("src", "")

                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"财新网深度报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": self.extract_publish_time(title)
                                or datetime.now(),
                                "created_at": datetime.now(),
                                "image_url": image_url,
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

                        # 提取图片
                        image_url = ""
                        img_tag = (
                            item.find_next("img")
                            if hasattr(item, "find_next")
                            else None
                        )
                        if img_tag:
                            image_url = img_tag.get("src", "")

                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"东方财富网报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": self.extract_publish_time(title)
                                or datetime.now(),
                                "created_at": datetime.now(),
                                "image_url": image_url,
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

                        # 提取图片
                        image_url = ""
                        img_tag = (
                            item.find_next("img")
                            if hasattr(item, "find_next")
                            else None
                        )
                        if img_tag:
                            image_url = img_tag.get("src", "")

                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"新浪财经报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": self.extract_publish_time(title)
                                or datetime.now(),
                                "created_at": datetime.now(),
                                "image_url": image_url,
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


class PhoenixFinanceScraper(EconomyScraper):
    """凤凰财经爬虫 - 综合财经资讯平台"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://finance.ifeng.com"
        self.source = "凤凰财经"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            # 凤凰财经的新闻链接
            news_items = soup.select(
                'a[href*="finance.ifeng.com"], .news-stream a, .news_item a, h3 a, h2 a'
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
                        and "ifeng.com" in url
                        and len(url) < 450
                    ):
                        # 过滤非文章链接
                        if any(
                            x in url
                            for x in [
                                "/video/",
                                "/photo/",
                                "/search",
                                ".jpg",
                                ".png",
                                "/tag/",
                            ]
                        ):
                            continue

                        seen_urls.add(url)

                        # 提取图片
                        image_url = ""
                        img_tag = (
                            item.find_next("img")
                            if hasattr(item, "find_next")
                            else None
                        )
                        if not img_tag:
                            parent = item.find_parent()
                            img_tag = parent.find("img") if parent else None
                        if img_tag:
                            image_url = img_tag.get("src", "") or img_tag.get(
                                "data-src", ""
                            )

                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "summary": f"凤凰财经报道: {title[:80]}",
                                "source": self.source,
                                "publish_time": self.extract_publish_time(title)
                                or datetime.now(),
                                "created_at": datetime.now(),
                                "image_url": image_url,
                            }
                        )

                        if len(articles) >= limit:
                            break
                except Exception as e:
                    continue

            print(f"凤凰财经获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"凤凰财经 scrape error: {e}")
        return articles


class ShanghaiSecuritiesNewsScraper(EconomyScraper):
    """上海证券报爬虫 - 权威证券资讯"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://news.cnstock.com"
        self.source = "上海证券报"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 使用news.cnstock.com首页
            response = self.session.get(self.base_url, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            # 查找所有a标签（不限制在li中）
            news_items = soup.select("a[href]")[:300]

            seen_urls = set()
            for item in news_items:
                try:
                    title = self.clean_text(item.text)
                    url = item.get("href", "")

                    # 更宽松的标题长度要求
                    if not title or len(title) < 8 or len(title) > 200:
                        continue

                    # URL处理 - 上海证券报使用相对路径
                    if url and not url.startswith("http"):
                        if url.startswith("//"):
                            url = f"https:{url}"
                        elif url.startswith("/"):
                            # 判断是哪个域名的路径
                            if url.startswith("/commonDetail/") or url.startswith(
                                "/news/"
                            ):
                                url = f"https://news.cnstock.com{url}"
                            else:
                                # 跳过非新闻类路径
                                if url.startswith("/html/") or url.startswith("/about"):
                                    continue
                                url = f"https://www.cnstock.com{url}"
                        else:
                            continue

                    # 确保是中国证券网的文章
                    if url and url not in seen_urls and "cnstock.com" in url:
                        # 过滤非文章链接
                        if any(
                            x in url
                            for x in [
                                "/video/",
                                "/photo/",
                                "/search",
                                ".jpg",
                                ".png",
                                "/html/",
                                "/about",
                                "/cooperation",
                            ]
                        ):
                            continue

                        # 确保是新闻文章URL（commonDetail是文章详情页）
                        if (
                            "/commonDetail/" in url
                            or "/news/" in url
                            or "/company/" in url
                            or "/stock/" in url
                            or url.count("/") >= 4
                        ):
                            seen_urls.add(url)

                            articles.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "summary": f"上海证券报: {title[:80]}",
                                    "source": self.source,
                                    "publish_time": datetime.now(),
                                    "created_at": datetime.now(),
                                    "image_url": "",
                                }
                            )

                            if len(articles) >= limit:
                                break
                except Exception as e:
                    continue

            print(f"上海证券报获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"上海证券报 scrape error: {e}")
            import traceback

            traceback.print_exc()
        return articles
