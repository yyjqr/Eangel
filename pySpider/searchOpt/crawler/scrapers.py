import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta
import time
import random
from fake_useragent import UserAgent
from typing import List, Dict, Optional
import re
import json
from urllib.parse import urljoin, urlparse


class TechScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.ua.random})

    def get_random_delay(self, min_delay=1, max_delay=3):
        """随机延迟，避免被反爬"""
        time.sleep(random.uniform(min_delay, max_delay))

    def clean_text(self, text: str) -> str:
        """清理文本"""
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


class HackerNewsScraper(TechScraper):
    """Hacker News 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.source = "Hacker News"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
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
                        "source": self.source,
                        "author": story_data.get("by", ""),
                        "tags": "Tech,News",
                        "publish_time": datetime.fromtimestamp(
                            story_data.get("time", 0)
                        ),
                        "created_at": datetime.now(),
                        "views": story_data.get("score", 0),
                        "likes": story_data.get("descendants", 0),
                        "image_url": "",  # HN usually doesn't have images
                    }
                    articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 Hacker News 文章")
            return articles

        except Exception as e:
            print(f"爬取 Hacker News 失败: {e}")
            return []


class RedditScraper(TechScraper):
    """Reddit Programming 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.reddit.com"
        self.source = "Reddit"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 Reddit r/programming 热门文章"""
        articles = []
        try:
            url = f"{self.base_url}/r/programming/hot.json?limit={limit}"
            response = self.session.get(url)
            data = response.json()

            for post in data["data"]["children"]:
                post_data = post["data"]

                if not post_data.get("is_self") and post_data.get("url"):
                    # 提取图片链接
                    image_url = ""
                    if post_data.get("thumbnail") and post_data.get(
                        "thumbnail"
                    ).startswith("http"):
                        image_url = post_data.get("thumbnail")
                    elif post_data.get("preview") and "images" in post_data["preview"]:
                        try:
                            image_url = post_data["preview"]["images"][0]["source"][
                                "url"
                            ].replace("&amp;", "&")
                        except:
                            pass

                    article = {
                        "title": post_data.get("title", ""),
                        "url": post_data.get("url", ""),
                        "summary": post_data.get("selftext", "")[:200]
                        or f"Reddit热门编程文章，赞数：{post_data.get('ups', 0)}",
                        "source": self.source,
                        "author": post_data.get("author", ""),
                        "tags": "Programming,Reddit",
                        "publish_time": datetime.fromtimestamp(
                            post_data.get("created_utc", 0)
                        ),
                        "created_at": datetime.now(),
                        "views": post_data.get("ups", 0),
                        "likes": post_data.get("num_comments", 0),
                        "image_url": image_url,
                    }
                    articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 Reddit 文章")
            return articles

        except Exception as e:
            print(f"爬取 Reddit 失败: {e}")
            return []


class GitHubTrendingScraper(TechScraper):
    """GitHub Trending 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://github.com"
        self.source = "GitHub"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 GitHub Trending 项目"""
        articles = []
        try:
            url = f"{self.base_url}/trending"
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, "html.parser")

            # 尝试多种可能的选择器
            repos = soup.select("article.Box-row")
            if not repos:
                repos = soup.select(".repo-list li")

            repos = repos[:limit]

            for repo in repos:
                try:
                    # 提取标题和链接
                    title_elem = repo.select_one("h2 a") or repo.select_one("h1 a")
                    if not title_elem:
                        continue

                    repo_name = self.clean_text(title_elem.text)
                    repo_url = urljoin(self.base_url, title_elem.get("href", ""))

                    # 提取描述
                    desc_elem = repo.select_one("p")
                    description = self.clean_text(desc_elem.text) if desc_elem else ""

                    # 提取语言
                    language_elem = repo.select_one('[itemprop="programmingLanguage"]')
                    language = (
                        self.clean_text(language_elem.text)
                        if language_elem
                        else "Unknown"
                    )

                    # 提取 Star 数
                    stars_elem = repo.select_one('a[href*="stargazers"]')
                    stars_text = self.clean_text(stars_elem.text) if stars_elem else "0"
                    stars_count = int(re.sub(r"[^\d]", "", stars_text) or 0)

                    # 提取 GitHub 头像作为预览图
                    image_url = ""
                    img_elem = repo.select_one("img.avatar")
                    if img_elem:
                        image_url = img_elem.get("src", "")

                    article = {
                        "title": f"{repo_name} - GitHub Trending项目",
                        "url": repo_url,
                        "summary": description
                        or f"GitHub热门{language}项目，Star数：{stars_text}",
                        "source": self.source,
                        "author": repo_name.split("/")[0] if "/" in repo_name else "",
                        "tags": f"GitHub,{language},OpenSource",
                        "publish_time": datetime.now(),
                        "created_at": datetime.now(),
                        "views": stars_count,
                        "likes": 0,
                        "image_url": image_url,
                    }
                    articles.append(article)

                except Exception as e:
                    print(f"解析GitHub项目失败: {e}")
                    continue

            print(f"成功爬取 {len(articles)} 个 GitHub Trending 项目")
            return articles

        except Exception as e:
            print(f"爬取 GitHub Trending 失败: {e}")
            return []


class AITopicsScraper(TechScraper):
    """AI topics Trending 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://aitopics.org/search"
        self.source = "aitopics"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 AI topics 文章"""
        articles = []
        try:
            response = self.session.get(self.base_url)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            # 使用用户提供的选择器 .searchtitle a
            news_links = soup.select(".searchtitle a")[:limit]

            for news in news_links:
                title = self.clean_text(news.text)
                url = news.get("href")

                if url and not url.startswith("http"):
                    url = urljoin("https://aitopics.org", url)

                if title and url:
                    # 尝试从所属容器中寻找图片
                    image_url = ""
                    parent = news.find_parent("div")
                    if parent:
                        img = parent.find("img")
                        if img:
                            image_url = img.get("src", "")

                    article = {
                        "title": title,
                        "url": url,
                        "summary": f"AI Topics 搜索结果: {title}",
                        "source": self.source,
                        "author": "AI Topics",
                        "tags": "AI,Machine Learning",
                        "publish_time": self.extract_publish_time(title)
                        or datetime.now(),
                        "created_at": datetime.now(),
                        "views": 0,
                        "likes": 0,
                        "image_url": image_url,
                    }
                    articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 AI Topics 文章")
            return articles

        except Exception as e:
            print(f"爬取 AI Topics 失败: {e}")
            return []


class DevToScraper(TechScraper):
    """Dev.to 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://dev.to"
        self.source = "Dev.to"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 Dev.to 热门文章"""
        articles = []
        try:
            url = f"{self.base_url}/api/articles?per_page={limit}&top=7"
            response = self.session.get(url)
            data = response.json()

            if not isinstance(data, list):
                print(f"Dev.to API 返回格式异常: {type(data)}")
                return []

            for article_data in data:
                if not isinstance(article_data, dict):
                    continue

                image_url = (
                    article_data.get("cover_image")
                    or article_data.get("social_image")
                    or ""
                )

                article = {
                    "title": article_data.get("title", ""),
                    "url": article_data.get("url", ""),
                    "summary": article_data.get("description", ""),
                    "source": self.source,
                    "author": article_data.get("user", {}).get("name", "")
                    if isinstance(article_data.get("user"), dict)
                    else "",
                    "tags": ",".join(article_data.get("tag_list", []))
                    if isinstance(article_data.get("tag_list"), list)
                    else "",
                    "publish_time": datetime.fromisoformat(
                        article_data.get("published_at", "").replace("Z", "+00:00")
                    )
                    if article_data.get("published_at")
                    else datetime.now(),
                    "created_at": datetime.now(),
                    "views": article_data.get("page_views_count", 0),
                    "likes": article_data.get("public_reactions_count", 0),
                    "image_url": image_url,
                }
                articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 Dev.to 文章")
            return articles

        except Exception as e:
            print(f"爬取 Dev.to 失败: {e}")
            return []


class MediumScraper(TechScraper):
    """Medium Technology 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://medium.com"
        self.source = "Medium"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 Medium 技术文章"""
        articles = []
        try:
            # Medium的RSS feed
            url = "https://medium.com/feed/topic/technology"
            feed = feedparser.parse(url)

            for entry in feed.entries[:limit]:
                # 尝试从 RSS 中提取图片
                image_url = ""
                if "media_content" in entry:
                    image_url = entry["media_content"][0]["url"]
                elif "links" in entry:
                    for link in entry["links"]:
                        if link.get("type", "").startswith("image/"):
                            image_url = link.get("href", "")
                            break

                article = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": self.clean_text(entry.get("summary", "")),
                    "source": self.source,
                    "author": entry.get("author", ""),
                    "tags": "Technology,Medium",
                    "publish_time": datetime(*entry.published_parsed[:6])
                    if entry.get("published_parsed")
                    else datetime.now(),
                    "created_at": datetime.now(),
                    "views": random.randint(100, 1000),  # Medium不提供具体数据
                    "likes": random.randint(10, 100),
                    "image_url": image_url,
                }
                articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 Medium 文章")
            return articles

        except Exception as e:
            print(f"爬取 Medium 失败: {e}")
            return []


class TechCrunchScraper(TechScraper):
    """TechCrunch 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://techcrunch.com"
        self.source = "TechCrunch"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 TechCrunch 文章"""
        articles = []
        try:
            # TechCrunch RSS feed
            url = "https://techcrunch.com/feed/"
            feed = feedparser.parse(url)

            for entry in feed.entries[:limit]:
                # 尝试提取图片逻辑同 Medium
                image_url = ""
                if "media_content" in entry:
                    image_url = entry["media_content"][0]["url"]
                elif "links" in entry:
                    for link in entry["links"]:
                        if link.get("type", "").startswith("image/"):
                            image_url = link.get("href", "")
                            break

                article = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": self.clean_text(entry.get("summary", "")),
                    "source": self.source,
                    "author": entry.get("author", ""),
                    "tags": "Tech News,Startup",
                    "publish_time": datetime(*entry.published_parsed[:6])
                    if entry.get("published_parsed")
                    else datetime.now(),
                    "created_at": datetime.now(),
                    "views": random.randint(500, 5000),
                    "likes": random.randint(20, 200),
                    "image_url": image_url,
                }
                articles.append(article)

            print(f"成功爬取 {len(articles)} 篇 TechCrunch 文章")
            return articles

        except Exception as e:
            print(f"爬取 TechCrunch 失败: {e}")
            return []


class ThirtySixKrScraper(TechScraper):
    """36Kr RSS 爬虫"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://36kr.com"
        self.rss_url = "https://www.36kr.com/feed"
        self.source = "36Kr"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        """爬取 36Kr 文章"""
        articles = []
        try:
            feed = feedparser.parse(self.rss_url)

            for entry in feed.entries[:limit]:
                image_url = ""
                if "media_content" in entry and entry["media_content"]:
                    image_url = entry["media_content"][0].get("url", "")
                elif "links" in entry:
                    for link in entry["links"]:
                        if link.get("type", "").startswith("image/"):
                            image_url = link.get("href", "")
                            break

                articles.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "summary": self.clean_text(
                            entry.get("summary", "") or entry.get("description", "")
                        ),
                        "source": self.source,
                        "author": entry.get("author", "36Kr"),
                        "tags": "科技,创业,36Kr",
                        "publish_time": datetime(*entry.published_parsed[:6])
                        if entry.get("published_parsed")
                        else datetime.now(),
                        "created_at": datetime.now(),
                        "views": random.randint(300, 3000),
                        "likes": random.randint(20, 300),
                        "image_url": image_url,
                    }
                )

            print(f"成功爬取 {len(articles)} 篇 36Kr 文章")
            return articles

        except Exception as e:
            print(f"爬取 36Kr 失败: {e}")
            return []
