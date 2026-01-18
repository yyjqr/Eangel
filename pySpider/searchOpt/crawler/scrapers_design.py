import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
import time
import random
from fake_useragent import UserAgent
from typing import List, Dict, Optional
import re
import json


class DesignScraper:
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

    def extract_image_url(self, soup, selectors: List[str]) -> Optional[str]:
        """从页面提取图片URL"""
        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                return img.get("src") or img.get("data-src")
        return None


class RedDotScraper(DesignScraper):
    """红点设计奖爬虫 (尝试通过新闻列表)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.red-dot.org/about-red-dot/magazine"
        self.source = "Red Dot Award"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 增加 headers
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")
            # 尝试更宽泛的选择器
            items = soup.find_all(
                ["article", "div"], class_=re.compile("teaser|card|magazine|news")
            )[:limit]
            for item in items:
                try:
                    link = item.find("a")
                    if not link:
                        continue
                    title = self.clean_text(item.get_text())
                    url = link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://www.red-dot.org{url}"
                    if len(title) > 10 and url:
                        articles.append(
                            {
                                "title": title[:100],
                                "url": url,
                                "summary": f"红点设计资讯: {title[:80]}",
                                "source": self.source,
                                "publish_time": datetime.now(),
                                "image_url": "",
                            }
                        )
                except Exception:
                    continue
            print(f"红点设计奖获取 {len(articles)} 个项目")
        except Exception as e:
            print(f"Red Dot error: {e}")
        return articles


class IFDesignScraper(DesignScraper):
    """IF设计奖爬虫 (尝试通过官网 RSS 或 备用搜索)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://ifdesign.com/en/magazine"
        self.source = "iF Design Award"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            # 改进选择器
            items = soup.find_all(
                ["div", "article"], class_=re.compile("grid-item|card|teaser")
            )[:limit]
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title_elem = item.find(["h2", "h3", "p"])
                if not title_elem:
                    continue
                title = self.clean_text(title_elem.text)
                url = link.get("href", "")
                if not url.startswith("http"):
                    url = f"https://ifdesign.com{url}"
                if title and url:
                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"iF设计动态: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": "",
                        }
                    )
            print(f"iF设计奖获取 {len(articles)} 个项目")
        except Exception as e:
            print(f"iF error: {e}")
        return articles


class MakezineScraper(DesignScraper):
    """Make: Magazine - 极客/DIY硬件"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://makezine.com/feed/"
        self.source = "Make: Magazine"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                # 过滤分类，关注 Technology 和 Workshop
                tags = [tag.get("term", "").lower() for tag in entry.get("tags", [])]
                is_target = any(
                    t in ["technology", "workshop", "electronics", "robotics"]
                    for t in tags
                )

                if is_target or True:  # 适当放宽
                    image_url = ""
                    if "media_content" in entry:
                        image_url = entry.media_content[0]["url"]
                    articles.append(
                        {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "summary": entry.get("summary", "")[:200],
                            "source": self.source,
                            "publish_time": datetime(*entry.published_parsed[:6])
                            if "published_parsed" in entry
                            else datetime.now(),
                            "image_url": image_url,
                        }
                    )
            print(f"Makezine 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Makezine error: {e}")
        return articles


class InfoQProductScraper(DesignScraper):
    """InfoQ.cn 产品经理频道 - 尝试通过其搜索或推荐接口 (简易版)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.infoq.cn/topic/product"
        self.source = "InfoQ Product"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # InfoQ 可能需要特定 Header
            self.session.headers.update({"Referer": "https://www.infoq.cn/"})
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            # 2026 版选择器
            items = soup.select('div[class*="article-item"], .com-article-title')[
                :limit
            ]
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title = self.clean_text(link.get_text())
                url = link.get("href", "")
                if not url.startswith("http"):
                    url = f"https://www.infoq.cn{url}"
                if title and url:
                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"InfoQ精选: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": "",
                        }
                    )
            print(f"InfoQ 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"InfoQ error: {e}")
        return articles


class DesignboomScraper(DesignScraper):
    """Designboom 设计门户"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.designboom.com/design/feed/"
        self.source = "Designboom"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                image_url = ""
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": self.clean_text(entry.get("summary", "")[:200]),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "image_url": image_url,
                    }
                )
            print(f"Designboom 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Designboom error: {e}")
        return articles


class DezeenScraper(DesignScraper):
    """Dezeen 设计杂志"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.dezeen.com/design/feed/"
        self.source = "Dezeen"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                image_url = ""
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")
                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": self.clean_text(entry.get("summary", "")[:200]),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "image_url": image_url,
                    }
                )
            print(f"Dezeen 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Dezeen error: {e}")
        return articles


class LVMHScraper(DesignScraper):

    """LVMH Newsroom - 奢侈品/CMF/空间设计"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.lvmh.com/en/news-lvmh"
        self.source = "LVMH"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.select(".news-list-item, article, .item-news")[:limit]
            for item in items:
                try:
                    title_elem = item.select_one("h2, h3, .title, .news-title")
                    link = item.select_one("a")
                    if not title_elem or not link:
                        continue
                    title = self.clean_text(title_elem.text)
                    url = link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://www.lvmh.com{url}"
                    image_url = self.extract_image_url(item, ["img"])
                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"LVMH 官方动态: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
                except Exception:
                    continue
            print(f"LVMH 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"LVMH error: {e}")
        return articles


class CarBuzzScraper(DesignScraper):
    """CarBuzz - 概念车 (尝试 RSS 或备用页)"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://carbuzz.com/feed/"
        self.source = "CarBuzz"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                if any(
                    w in title.lower()
                    for w in ["concept", "supercar", "hypercar", "vision"]
                ):
                    articles.append(
                        {
                            "title": title,
                            "url": entry.get("link", ""),
                            "summary": entry.get("summary", "")[:200],
                            "source": self.source,
                            "publish_time": datetime(*entry.published_parsed[:6])
                            if "published_parsed" in entry
                            else datetime.now(),
                            "image_url": "",
                        }
                    )
            print(f"CarBuzz 获取 {len(articles)} 篇概念车文章")
        except Exception as e:
            print(f"CarBuzz error: {e}")
        return articles


class ProductHuntScraper(DesignScraper):
    """Product Hunt - 产品发现平台 (使用每日榜单首页)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.producthunt.com"
        self.source = "Product Hunt"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 尝试抓取每日 Top 10 的 DOM，PH 反爬较严，增加 UA
            self.session.headers.update({"Referer": "https://www.google.com/"})
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, "html.parser")

            # PH 2026 可能使用的通用选择器
            product_items = soup.select('[data-test="post-item"]')[:limit]
            if not product_items:
                product_items = soup.select(".postItem_")[:limit]

            for item in product_items:
                try:
                    title_elem = item.select_one('[data-test="post-name"], h3')
                    link = item.select_one('a[href^="/posts/"]')
                    if not title_elem or not link:
                        continue

                    title = self.clean_text(title_elem.text)
                    url = f"{self.base_url}{link['href']}"
                    image_url = self.extract_image_url(item, ["img"])

                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"Product Hunt 每日精选: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
                except Exception:
                    continue
            print(f"Product Hunt 获取 {len(articles)} 个产品")
        except Exception as e:
            print(f"Product Hunt error: {e}")
        return articles


class CarDesignNewsScraper(DesignScraper):
    """Car Design News - 汽车设计 (包含 Concept 与 CMF)"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.cardesignnews.com"
        self.source = "Car Design News"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        channels = ["/cars/concepts", "/cmf"]
        for channel in channels:
            try:
                url = f"{self.base_url}{channel}"
                response = self.session.get(url, timeout=15)
                soup = BeautifulSoup(response.content, "html.parser")
                items = soup.select("article, .news-item, .post")[: limit // 2]
                for item in items:
                    title_elem = item.select_one("h2, h3, .title")
                    link = item.select_one("a")
                    if not title_elem or not link:
                        continue
                    title = (
                        f"[{channel[1:].upper()}] {self.clean_text(title_elem.text)}"
                    )
                    url_art = link.get("href", "")
                    if url_art and not url_art.startswith("http"):
                        url_art = f"{self.base_url}{url_art}"
                    image_url = self.extract_image_url(item, ["img"])
                    articles.append(
                        {
                            "title": title,
                            "url": url_art,
                            "summary": f"汽车设计动态: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
            except Exception:
                continue
        print(f"Car Design News 获取 {len(articles)} 篇文章")
        return articles


class KeringScraper(DesignScraper):
    """Kering Group - 奢侈品/可持续设计"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.kering.com/en/news/"
        self.source = "Kering"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.select(".news-list__item, .card-news, article")[:limit]
            for item in items:
                try:
                    title_elem = item.select_one("h2, h3, .card-news__title")
                    link = item.select_one("a")
                    if not title_elem or not link:
                        continue
                    title = self.clean_text(title_elem.text)
                    url = link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://www.kering.com{url}"
                    image_url = self.extract_image_url(item, ["img"])
                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"Kering 官方新闻: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
                except Exception:
                    continue
            print(f"Kering 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Kering error: {e}")
        return articles


class CarAndDriverScraper(DesignScraper):
    """Car and Driver - Concept Cars"""

    def __init__(self):
        super().__init__()
        self.base_url = (
            "https://www.caranddriver.com/news/g15076135/concept-cars-future-cars/"
        )
        self.source = "Car and Driver"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            items = soup.select(".listicle-item, .slide-title")[:limit]
            for item in items:
                try:
                    title_elem = item.select_one(".listicle-item-hed, .slide-title")
                    if not title_elem:
                        continue
                    title = self.clean_text(title_elem.text)
                    link = item.select_one("a")
                    url = link.get("href", "") if link else self.base_url
                    if url and not url.startswith("http"):
                        url = f"https://www.caranddriver.com{url}"
                    image_url = self.extract_image_url(item, ["img"])
                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"Car and Driver 概念车: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
                except Exception:
                    continue
            print(f"Car and Driver 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Car and Driver error: {e}")
        return articles


class PopularMechanicsScraper(DesignScraper):
    """Popular Mechanics - 机械/极客/科技产品"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.popularmechanics.com"
        self.source = "Popular Mechanics"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 模拟参考代码的 headers
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
                }
            )
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")

            # 灵活匹配选择器：从 a.enk2x9t2 放宽到通用文章标题选择器
            items = soup.find_all(
                "a", class_=re.compile(r"enk2x9t2|item-title|content-title|headline")
            )
            if not items:
                # 最后的兜底：查找包含较长文本的 a 标签
                items = [
                    a
                    for a in soup.find_all(
                        "a",
                        href=re.compile(
                            r"/(adventure|science|military|technology|engineering)/"
                        ),
                    )
                    if len(a.text.strip()) > 20
                ]

            seen_urls = set()
            for item in items[: limit * 3]:
                if len(articles) >= limit:
                    break
                try:
                    title = self.clean_text(item.text)
                    if not title or len(title) < 15 or "advertisement" in title.lower():
                        continue

                    url = item.get("href", "")
                    if not url:
                        continue
                    if not url.startswith("http"):
                        url = f"https://www.popularmechanics.com{url}"

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # 提取缩略图
                    image_url = self.extract_image_url(item.parent.parent, ["img"])

                    articles.append(
                        {
                            "title": title,
                            "url": url,
                            "summary": f"Popular Mechanics 科技精选: {title[:80]}",
                            "source": self.source,
                            "publish_time": datetime.now(),
                            "image_url": image_url or "",
                        }
                    )
                except Exception:
                    continue
            print(f"Popular Mechanics 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Popular Mechanics error: {e}")
        return articles


class YankoDesignScraper(DesignScraper):

    """Yanko Design - 现代产品设计"""

    def __init__(self):
        super().__init__()
        self.rss_url = "https://www.yankodesign.com/feed/"
        self.source = "Yanko Design"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"Yanko Design RSS返回 {len(feed.entries)} 条目")

            for entry in feed.entries[:limit]:
                image_url = ""
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": self.clean_text(entry.get("summary", "")[:200]),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "image_url": image_url,
                    }
                )
        except Exception as e:
            print(f"Yanko Design scrape error: {e}")
        return articles


class CoreDesignScraper(DesignScraper):
    """Core77 - 工业设计社区"""

    def __init__(self):
        super().__init__()
        self.rss_url = "http://feeds.feedburner.com/core77/blog"
        self.source = "Core77"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)
            print(f"Core77 RSS返回 {len(feed.entries)} 条目")

            for entry in feed.entries[:limit]:
                image_url = ""
                if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url", "")

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": self.clean_text(entry.get("summary", "")[:200]),
                        "source": self.source,
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now(),
                        "image_url": image_url,
                    }
                )
        except Exception as e:
            print(f"Core77 scrape error: {e}")
        return articles
