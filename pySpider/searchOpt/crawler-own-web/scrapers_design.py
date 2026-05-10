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
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })

    def get_random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())

    def extract_publish_time(self, time_str: str) -> Optional[datetime]:
        """提取发布时间"""
        try:
            if not time_str:
                return None

            # 尝试提取日期 (simple regex for YYYY-MM-DD or similar)
            match = re.search(r'(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})', time_str)
            if match:
                try:
                    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    pass
            return None
        except:
            return None

    def extract_image_url(self, soup, selectors: List[str]) -> Optional[str]:
        """从页面提取图片URL"""
        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                return img.get('src') or img.get('data-src')
        return None


class RedDotScraper(DesignScraper):
    """红点设计奖爬虫 (优化版)"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.red-dot.org/magazine"
        self.source = "Red Dot Award"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 使用更广泛的选择器匹配文章卡片
            items = soup.select('article, .card, .teaser-item, .o-teaser')[:limit]

            for item in items:
                try:
                    # 尝试寻找链接
                    link = item.find('a')
                    if not link: continue

                    # 尝试寻找标题
                    title_elem = item.select_one('h2, h3, h4, .headline, .teaser__headline')
                    if not title_elem:
                        # 如果没有标题元素，尝试链接的文本或title属性
                        title = link.get_text(strip=True) or link.get('title')
                    else:
                        title = title_elem.get_text(strip=True)

                    if not title: continue
                    title = self.clean_text(title)

                    url = link.get('href', '')
                    if not url.startswith('http'):
                        url = f"https://www.red-dot.org{url}"

                    # 提取图片
                    image_url = self.extract_image_url(item, ['img', '[data-src]']) or ''

                    # 避免重复和无效链接
                    if len(title) > 10 and url and 'red-dot.org' in url:
                        articles.append({
                            'title': title[:100],
                            'url': url,
                            'summary': f'红点设计资讯: {title[:80]}',
                            'source': self.source,
                            'publish_time': self.extract_publish_time(title) or datetime.now(),
                            'created_at': datetime.now(),
                            'image_url': image_url
                        })
                except Exception: continue

            print(f"红点设计奖获取 {len(articles)} 个项目")
        except Exception as e: print(f"Red Dot error: {e}")
        return articles


class LeManooshScraper(DesignScraper):
    """leManoosh 爬虫 - 工业设计情绪板/CMF"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://lemanoosh.com/"
        self.source = "leManoosh"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # 访问博客或主页
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')

            # leManoosh 通常是网格布局
            items = soup.select('.post-item, article, .grid-item')[:limit]

            for item in items:
                try:
                    title_elem = item.select_one('h2, h3, .post-title')
                    link = item.select_one('a')

                    if not link: continue

                    url = link.get('href', '')
                    if not title_elem:
                        # 尝试从链接文本获取
                        title = link.get_text(strip=True)
                    else:
                        title = title_elem.get_text(strip=True)

                    title = self.clean_text(title)
                    if not title:
                        # 有时候是个纯图片链接，尝试从 alt 获取
                        img = item.find('img')
                        if img:
                            title = img.get('alt', '')

                    if not title: title = "leManoosh Design Inspiration"

                    # 提取图片 (leManoosh 图片很重要)
                    image_url = self.extract_image_url(item, ['img', '.post-thumbnail img']) or ''

                    # 处理懒加载图片
                    if not image_url and item.find('div', class_='bg-image'):
                         style = item.find('div', class_='bg-image').get('style', '')
                         match = re.search(r'url\((.*?)\)', style)
                         if match:
                             image_url = match.group(1).strip("'\"")

                    articles.append({
                        'title': title,
                        'url': url,
                        'summary': f'leManoosh 灵感: {title[:80]}',
                        'source': self.source,
                        'publish_time': datetime.now(),
                        'created_at': datetime.now(),
                        'image_url': image_url
                    })
                except Exception: continue

            print(f"leManoosh 获取 {len(articles)} 个灵感")
        except Exception as e: print(f"leManoosh error: {e}")
        return articles


class BehanceScraper(DesignScraper):
    """Behance 爬虫 (工业设计)"""
    def __init__(self):
        super().__init__()
        # 使用工业设计分类的搜索页面
        self.base_url = "https://www.behance.net/galleries/industrial-design/product-design"
        self.source = "Behance"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            # Behance 也是重前端，尝试模拟
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.behance.net/'
            })
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 尝试抓取项目卡片
            items = soup.select('.ProjectCover-root-s3g, .ContentGrid-gridItem-W_3, li.rf-project-cover')

            # 如果是 CSR，可能找不到 items。尝试从 script 标签粗暴匹配
            if not items:
                # 这是一个非常粗暴的正则匹配来寻找项目数据，仅作最后的尝试
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and '"projects":' in script.string:
                        try:
                            # 提取项目信息的片段... 这通常很复杂，暂时通过简单的正则寻找 url 和 title
                            # 仅作演示，实际可能不稳定
                            matches = re.findall(r'"url":"(https://www.behance.net/gallery/[^"]+)","title":"([^"]+)"', script.string)
                            for m_url, m_title in matches[:limit]:
                                if 'behance.net' in m_url:
                                    articles.append({
                                        'title': self.clean_text(m_title),
                                        'url': m_url.replace('\\/', '/'),
                                        'summary': f'Behance 设计: {self.clean_text(m_title)}',
                                        'source': self.source,
                                        'publish_time': datetime.now(),
                                        'created_at': datetime.now(),
                                        'image_url': '' # 图片URL在脚本里提取比较麻烦
                                    })
                        except: pass
                        break

            # 正常的 DOM 解析
            for item in items[:limit]:
                try:
                    title_elem = item.select_one('.ProjectCover-details-title, .Title-title-3nk, h3')
                    link = item.select_one('a.ProjectCover-cover-link, a')

                    if not link: continue

                    if not title_elem:
                         title = link.get('title') or link.get_text(strip=True)
                    else:
                         title = title_elem.get_text(strip=True)

                    if not title: continue
                    title = self.clean_text(title)

                    url = link.get('href', '')
                    if not url.startswith('http'): url = f"https://www.behance.net{url}"

                    image_url = self.extract_image_url(item, ['img.ProjectCover-image-3mz', 'img']) or ''

                    articles.append({
                        'title': title,
                        'url': url,
                        'summary': f'Behance 作品: {title[:80]}',
                        'source': self.source,
                        'publish_time': datetime.now(),
                        'created_at': datetime.now(),
                        'image_url': image_url
                    })
                except Exception: continue

            print(f"Behance 获取 {len(articles)} 个项目")
        except Exception as e: print(f"Behance error: {e}")
        return articles


class IDEAScraper(DesignScraper):
    """IDEA 设计奖爬虫 (IDSA)"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.idsa.org/awards/idea/gallery"
        self.source = "IDEA Awards"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            })
            # 如果 gallery 页面是空白或JS渲染，尝试 news 或 finalists
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 常见图库卡片类名
            items = soup.select('.views-row, .gallery-item, article')[:limit]

            for item in items:
                try:
                    title_elem = item.select_one('h2, h3, .title, .views-field-title a')
                    link = item.select_one('a')

                    # 优先使用 title_elem 中的链接，如果存在
                    if title_elem and title_elem.name == 'a':
                        link = title_elem
                    elif title_elem:
                        link = title_elem.find('a') or item.find('a')

                    if not title_elem or not link: continue

                    title = self.clean_text(title_elem.get_text())
                    url = link.get('href', '')
                    if not url.startswith('http'): url = f"https://www.idsa.org{url}"

                    image_url = self.extract_image_url(item, ['img']) or ''

                    articles.append({
                        'title': title,
                        'url': url,
                        'summary': f'IDEA 获奖作品: {title[:80]}',
                        'source': self.source,
                        'publish_time': datetime.now(),
                        'created_at': datetime.now(),
                        'image_url': image_url
                    })
                except Exception: continue

            print(f"IDEA Awards 获取 {len(articles)} 个项目")
        except Exception as e: print(f"IDEA error: {e}")
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
            soup = BeautifulSoup(response.content, 'html.parser')
            # 改进选择器
            items = soup.find_all(['div', 'article'], class_=re.compile('grid-item|card|teaser'))[:limit]
            for item in items:
                link = item.find('a')
                if not link: continue
                title_elem = item.find(['h2', 'h3', 'p'])
                if not title_elem: continue
                title = self.clean_text(title_elem.text)
                url = link.get('href', '')
                if not url.startswith('http'): url = f"https://ifdesign.com{url}"
                if title and url:
                    articles.append({
                        'title': title, 'url': url, 'summary': f'iF设计动态: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': ''
                    })
            print(f"iF设计奖获取 {len(articles)} 个项目")
        except Exception as e: print(f"iF error: {e}")
        return articles


class MakezineScraper(DesignScraper):
    """Make: Magazine - 极客/DIY硬件 (优化版)"""
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
                tags = [tag.get('term', '').lower() for tag in entry.get('tags', [])]
                is_target = any(t in ['technology', 'workshop', 'electronics', 'robotics', 'digital fabrication'] for t in tags)

                # 放宽条件保留更多优质 Diy 内容
                if is_target or True:
                    image_url = ''
                    if 'media_content' in entry:
                        image_url = entry.media_content[0]['url']
                    elif 'description' in entry:
                         # 尝试从 description 的 img 标签中提取
                         match = re.search(r'src="([^"]+)"', entry.description)
                         if match:
                             image_url = match.group(1)

                    summary = self.clean_text(re.sub(r'<[^>]+>', '', entry.get('summary', '')[:300]))

                    articles.append({
                        'title': entry.get('title', ''),
                        'url': entry.get('link', ''),
                        'summary': summary,
                        'source': self.source,
                        'publish_time': datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else datetime.now(),
                        'created_at': datetime.now(),
                        'image_url': image_url
                    })
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
            self.session.headers.update({'Referer': 'https://www.infoq.cn/'})
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            # 2026 版选择器
            items = soup.select('div[class*="article-item"], .com-article-title')[:limit]
            for item in items:
                link = item.find('a')
                if not link: continue
                title = self.clean_text(link.get_text())
                url = link.get('href', '')
                if not url.startswith('http'): url = f"https://www.infoq.cn{url}"
                if title and url:
                    articles.append({
                        'title': title, 'url': url, 'summary': f'InfoQ精选: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': ''
                    })
            print(f"InfoQ 获取 {len(articles)} 篇文章")
        except Exception as e: print(f"InfoQ error: {e}")
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
                image_url = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')
                articles.append({
                    'title': entry.get('title', ''), 'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')[:200]),
                    'source': self.source,
                    'publish_time': datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now(),
                    'image_url': image_url
                })
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
                image_url = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')
                articles.append({
                    'title': entry.get('title', ''), 'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')[:200]),
                    'source': self.source,
                    'publish_time': datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now(),
                    'image_url': image_url
                })
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
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.select('.news-list-item, article, .item-news')[:limit]
            for item in items:
                try:
                    title_elem = item.select_one('h2, h3, .title, .news-title')
                    link = item.select_one('a')
                    if not title_elem or not link: continue
                    title = self.clean_text(title_elem.text)
                    url = link.get('href', '')
                    if not url.startswith('http'): url = f"https://www.lvmh.com{url}"
                    image_url = self.extract_image_url(item, ['img'])
                    articles.append({
                        'title': title, 'url': url, 'summary': f'LVMH 官方动态: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': image_url or ''
                    })
                except Exception: continue
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
                title = entry.get('title', '')
                if any(w in title.lower() for w in ['concept', 'supercar', 'hypercar', 'vision']):
                    articles.append({
                        'title': title, 'url': entry.get('link', ''),
                        'summary': entry.get('summary', '')[:200],
                        'source': self.source,
                        'publish_time': datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else datetime.now(),
                        'image_url': ''
                    })
            print(f"CarBuzz 获取 {len(articles)} 篇概念车文章")
        except Exception as e: print(f"CarBuzz error: {e}")
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
            self.session.headers.update({'Referer': 'https://www.google.com/'})
            response = self.session.get(self.base_url, timeout=20)
            soup = BeautifulSoup(response.content, 'html.parser')

            # PH 2026 可能使用的通用选择器
            product_items = soup.select('[data-test="post-item"]')[:limit]
            if not product_items:
                product_items = soup.select('.postItem_')[:limit]

            for item in product_items:
                try:
                    title_elem = item.select_one('[data-test="post-name"], h3')
                    link = item.select_one('a[href^="/posts/"]')
                    if not title_elem or not link: continue

                    title = self.clean_text(title_elem.text)
                    url = f"{self.base_url}{link['href']}"
                    image_url = self.extract_image_url(item, ['img'])

                    articles.append({
                        'title': title, 'url': url, 'summary': f'Product Hunt 每日精选: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': image_url or ''
                    })
                except Exception: continue
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
                soup = BeautifulSoup(response.content, 'html.parser')
                items = soup.select('article, .news-item, .post')[:limit//2]
                for item in items:
                    title_elem = item.select_one('h2, h3, .title')
                    link = item.select_one('a')
                    if not title_elem or not link: continue
                    title = f"[{channel[1:].upper()}] {self.clean_text(title_elem.text)}"
                    url_art = link.get('href', '')
                    if url_art and not url_art.startswith('http'): url_art = f"{self.base_url}{url_art}"
                    image_url = self.extract_image_url(item, ['img'])
                    articles.append({
                        'title': title, 'url': url_art, 'summary': f'汽车设计动态: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': image_url or ''
                    })
            except Exception: continue
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
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.select('.news-list__item, .card-news, article')[:limit]
            for item in items:
                try:
                    title_elem = item.select_one('h2, h3, .card-news__title')
                    link = item.select_one('a')
                    if not title_elem or not link: continue
                    title = self.clean_text(title_elem.text)
                    url = link.get('href', '')
                    if not url.startswith('http'): url = f"https://www.kering.com{url}"
                    image_url = self.extract_image_url(item, ['img'])
                    articles.append({
                        'title': title, 'url': url, 'summary': f'Kering 官方新闻: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': image_url or ''
                    })
                except Exception: continue
            print(f"Kering 获取 {len(articles)} 篇文章")
        except Exception as e:
            print(f"Kering error: {e}")
        return articles


class CarAndDriverScraper(DesignScraper):
    """Car and Driver - Concept Cars"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.caranddriver.com/news/g15076135/concept-cars-future-cars/"
        self.source = "Car and Driver"

    def scrape_articles(self, limit: int = 10) -> List[Dict]:
        articles = []
        try:
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.select('.listicle-item, .slide-title')[:limit]
            for item in items:
                try:
                    title_elem = item.select_one('.listicle-item-hed, .slide-title')
                    if not title_elem: continue
                    title = self.clean_text(title_elem.text)
                    link = item.select_one('a')
                    url = link.get('href', '') if link else self.base_url
                    if url and not url.startswith('http'): url = f"https://www.caranddriver.com{url}"
                    image_url = self.extract_image_url(item, ['img'])
                    articles.append({
                        'title': title, 'url': url, 'summary': f'Car and Driver 概念车: {title[:80]}',
                        'source': self.source, 'publish_time': datetime.now(), 'image_url': image_url or ''
                    })
                except Exception: continue
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
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
            })
            response = self.session.get(self.base_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 灵活匹配选择器：从 a.enk2x9t2 放宽到通用文章标题选择器
            items = soup.find_all('a', class_=re.compile(r'enk2x9t2|item-title|content-title|headline'))
            if not items:
                # 最后的兜底：查找包含较长文本的 a 标签
                items = [a for a in soup.find_all('a', href=re.compile(r'/(adventure|science|military|technology|engineering)/')) if len(a.text.strip()) > 20]

            seen_urls = set()
            for item in items[:limit*3]:
                if len(articles) >= limit: break
                try:
                    title = self.clean_text(item.text)
                    if not title or len(title) < 15 or 'advertisement' in title.lower():
                        continue

                    url = item.get('href', '')
                    if not url: continue
                    if not url.startswith('http'):
                        url = f"https://www.popularmechanics.com{url}"

                    if url in seen_urls: continue
                    seen_urls.add(url)

                    # 提取缩略图
                    image_url = self.extract_image_url(item.parent.parent, ['img'])

                    articles.append({
                        'title': title,
                        'url': url,
                        'summary': f'Popular Mechanics 科技精选: {title[:80]}',
                        'source': self.source,
                        'publish_time': datetime.now(),
                        'image_url': image_url or ''
                    })
                except Exception: continue
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
                image_url = ''
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')

                articles.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')[:200]),
                    'source': self.source,
                    'publish_time': datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now(),
                    'image_url': image_url
                })
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
                image_url = ''
                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url', '')

                articles.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')[:200]),
                    'source': self.source,
                    'publish_time': datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now(),
                    'image_url': image_url
                })
        except Exception as e:
            print(f"Core77 scrape error: {e}")
        return articles
