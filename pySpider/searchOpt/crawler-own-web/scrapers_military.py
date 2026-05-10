import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
import time
import random
from fake_useragent import UserAgent
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse


class MilitaryScraperBase:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def get_random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        return re.sub(r'\s+', ' ', text.strip())

    def fetch_article_summary(self, url: str, max_sentences: int = 3) -> str:
        """访问文章页面，提取正文前几段作为真实摘要"""
        try:
            resp = self.request_url(url, timeout=10)
            if not resp:
                return ''
            resp.encoding = resp.encoding or 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 移除无关标签
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                tag.decompose()
            # 尝试从常见正文容器中提取
            article_body = (
                soup.find('article') or
                soup.find('div', class_=re.compile(r'article|content|post|entry|story|body', re.I)) or
                soup.find('div', id=re.compile(r'article|content|post|entry|story|body', re.I)) or
                soup
            )
            paragraphs = article_body.find_all('p')
            sentences = []
            for p in paragraphs:
                text = self.clean_text(p.get_text(' ', strip=True))
                if len(text) < 20:
                    continue
                sentences.append(text)
                if len(sentences) >= max_sentences:
                    break
            return ' '.join(sentences)[:500]
        except Exception:
            return ''

    def request_url(self, url: str, timeout: int = 12) -> Optional[requests.Response]:
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f'请求失败 {url}: {e}')
            return None

    def build_article(self, title: str, url: str, summary: str = '', author: str = '', tags: str = '', publish_time=None, image_url: str = '') -> Dict:
        return {
            'title': self.clean_text(title),
            'url': url,
            'summary': self.clean_text(summary)[:240],
            'source': self.source,
            'author': author or self.source,
            'tags': tags,
            'publish_time': publish_time or datetime.now(),
            'created_at': datetime.now(),
            'views': random.randint(100, 3000),
            'likes': random.randint(10, 300),
            'image_url': image_url,
        }

    def scrape_links_from_page(self, page_url: str, selectors: List[str], limit: int, tags: str, summary_prefix: str = '', allow_patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None) -> List[Dict]:
        articles = []
        seen = set()
        response = self.request_url(page_url)
        if not response:
            return articles

        response.encoding = response.encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        candidates = []

        for selector in selectors:
            candidates.extend(soup.select(selector))

        if not candidates:
            candidates = soup.find_all('a', href=True)

        parsed_page = urlparse(page_url)
        exclude_patterns = [p.lower() for p in (exclude_patterns or [])]
        allow_patterns = [p.lower() for p in (allow_patterns or [])]

        for node in candidates:
            if len(articles) >= limit:
                break

            anchor = node if getattr(node, 'name', '') == 'a' else node.find('a', href=True)
            if not anchor:
                continue

            title = self.clean_text(anchor.get_text(' ', strip=True))
            href = anchor.get('href', '').strip()
            if not title or len(title) < 12 or not href:
                continue

            url = urljoin(page_url, href)
            url_lower = url.lower()
            url_host = urlparse(url).netloc.lower()

            if url in seen:
                continue
            if url.startswith('javascript:') or url.startswith('mailto:'):
                continue
            if parsed_page.netloc not in url_host and 'ifeng.com' not in url_host and 'huanqiu.com' not in url_host:
                continue
            if any(pattern in url_lower for pattern in exclude_patterns):
                continue
            if allow_patterns and not any(pattern in url_lower for pattern in allow_patterns):
                continue

            image_url = ''
            img = node.find('img') if getattr(node, 'find', None) else None
            if img:
                image_url = img.get('src', '') or img.get('data-src', '')
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = urljoin(page_url, image_url)

            seen.add(url)
            # 访问文章页面提取真实摘要
            summary = self.fetch_article_summary(url)
            if not summary or summary.strip() == title.strip():
                summary = f'{summary_prefix}{title}' if summary_prefix else title
            articles.append(self.build_article(title, url, summary=summary, tags=tags, image_url=image_url))
            self.get_random_delay(0.5, 1.5)

        return articles


class TWZScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.base_url = 'https://www.twz.com'
        self.source = 'The War Zone'
        self.rss_url = 'https://www.twz.com/feed'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.request_url(self.rss_url)
            if not response:
                return []
            feed = feedparser.parse(response.text)
            for entry in feed.entries[:limit]:
                image_url = ''
                if 'media_content' in entry and len(entry['media_content']) > 0:
                    image_url = entry['media_content'][0].get('url', '')
                elif 'links' in entry:
                    for link in entry['links']:
                        if link.get('type', '').startswith('image/'):
                            image_url = link.get('href', '')
                            break

                articles.append(self.build_article(
                    entry.get('title', ''),
                    entry.get('link', ''),
                    summary=entry.get('summary', ''),
                    author=entry.get('author', 'TWZ'),
                    tags='Military,Aviation,Defense',
                    publish_time=datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.now(),
                    image_url=image_url,
                ))
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []


class MilitaryComScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.source = 'Military.com'
        self.base_url = 'https://www.military.com/daily-news'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        try:
            articles = self.scrape_links_from_page(
                self.base_url,
                selectors=['a[href*="/daily-news/"]', 'article a', 'h2 a', 'h3 a'],
                limit=limit,
                tags='US Military,Defense',
                summary_prefix='Military.com: ',
                allow_patterns=['/daily-news/'],
                exclude_patterns=['/video', '/author/', '/topic/', '/search', '/benefits', '/off-duty'],
            )
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []


class DefenseNewsScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.source = 'Defense News'
        self.base_url = 'https://www.defensenews.com/'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        try:
            articles = self.scrape_links_from_page(
                self.base_url,
                selectors=['a[href*="/global/"]', 'a[href*="/air/"]', 'a[href*="/naval/"]', 'a[href*="/land/"]', 'article a', 'h2 a'],
                limit=limit,
                tags='Global Defense,Military',
                summary_prefix='Defense News: ',
                allow_patterns=['/global/', '/air/', '/naval/', '/land/', '/space/', '/pentagon/'],
                exclude_patterns=['/video', '/author/', '/tag/', '/topic/', '/search'],
            )
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []


class BreakingDefenseScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.source = 'Breaking Defense'
        self.base_url = 'https://breakingdefense.com/'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        try:
            articles = self.scrape_links_from_page(
                self.base_url,
                selectors=['article a', 'h2 a', 'h3 a'],
                limit=limit,
                tags='Defense Industry,Military Tech',
                summary_prefix='Breaking Defense: ',
                allow_patterns=['/20'],
                exclude_patterns=['/video', '/tag/', '/author/', '/category/', '/events/'],
            )
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []


class IfengMilitaryScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.source = '凤凰军事'
        self.base_url = 'https://mil.ifeng.com/'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        try:
            articles = self.scrape_links_from_page(
                self.base_url,
                selectors=['a[href*="ifeng.com/c/"]', 'a[href*="mil.ifeng.com/"]', 'h1 a', 'h2 a', 'h3 a'],
                limit=limit,
                tags='军事,国内军事,国际军事',
                summary_prefix='凤凰军事：',
                allow_patterns=['ifeng.com/c/', 'mil.ifeng.com/'],
                exclude_patterns=['/special/', '/video', '/slide', '/opinion', '/search'],
            )
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []


class HuanqiuMilitaryScraper(MilitaryScraperBase):
    def __init__(self):
        super().__init__()
        self.source = '环球军事'
        self.base_url = 'https://mil.huanqiu.com/'

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        try:
            articles = self.scrape_links_from_page(
                self.base_url,
                selectors=['a[href*="huanqiu.com/article/"]', 'a[href*="mil.huanqiu.com/article/"]', 'h2 a', 'h3 a'],
                limit=limit,
                tags='军事,国际军事,防务',
                summary_prefix='环球军事：',
                allow_patterns=['huanqiu.com/article/'],
                exclude_patterns=['/video', '/topic/', '/search', '/opinion'],
            )
            print(f'成功爬取 {len(articles)} 篇 {self.source} 文章')
            return articles
        except Exception as e:
            print(f'爬取 {self.source} 失败: {e}')
            return []
