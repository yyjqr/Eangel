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
        self.session.headers.update({
            'User-Agent': self.ua.random
        })
        
    def get_random_delay(self, min_delay=1, max_delay=3):
        """随机延迟，避免被反爬"""
        time.sleep(random.uniform(min_delay, max_delay))
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def extract_publish_time(self, time_str: str) -> Optional[datetime]:
        """提取发布时间"""
        try:
            if not time_str:
                return None
            # 这里可以根据不同网站的时间格式进行解析
            return datetime.now()  # 简化处理
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
                story_response = self.session.get(f"{self.base_url}/item/{story_id}.json")
                story_data = story_response.json()
                
                if story_data and story_data.get('url'):
                    article = {
                        'title': story_data.get('title', ''),
                        'url': story_data.get('url', ''),
                        'summary': f"Hacker News热门文章，得分：{story_data.get('score', 0)}",
                        'source': self.source,
                        'author': story_data.get('by', ''),
                        'tags': 'Tech,News',
                        'publish_time': datetime.fromtimestamp(story_data.get('time', 0)),
                        'views': story_data.get('score', 0),
                        'likes': story_data.get('descendants', 0)
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
            
            for post in data['data']['children']:
                post_data = post['data']
                
                if not post_data.get('is_self') and post_data.get('url'):
                    article = {
                        'title': post_data.get('title', ''),
                        'url': post_data.get('url', ''),
                        'summary': post_data.get('selftext', '')[:200] or f"Reddit热门编程文章，赞数：{post_data.get('ups', 0)}",
                        'source': self.source,
                        'author': post_data.get('author', ''),
                        'tags': 'Programming,Reddit',
                        'publish_time': datetime.fromtimestamp(post_data.get('created_utc', 0)),
                        'views': post_data.get('ups', 0),
                        'likes': post_data.get('num_comments', 0)
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
            soup = BeautifulSoup(response.content, 'html.parser')
            
            repos = soup.find_all('article', class_='Box-row')[:limit]
            
            for repo in repos:
                try:
                    title_elem = repo.find('h2', class_='h3')
                    if not title_elem:
                        continue
                    
                    repo_link = title_elem.find('a')
                    repo_name = self.clean_text(repo_link.text)
                    repo_url = urljoin(self.base_url, repo_link.get('href', ''))
                    
                    desc_elem = repo.find('p', class_='col-9')
                    description = self.clean_text(desc_elem.text) if desc_elem else ""
                    
                    stars_elem = repo.find('a', href=lambda x: x and 'stargazers' in x)
                    stars = self.clean_text(stars_elem.text) if stars_elem else "0"
                    
                    language_elem = repo.find('span', {'itemprop': 'programmingLanguage'})
                    language = self.clean_text(language_elem.text) if language_elem else "Unknown"
                    
                    article = {
                        'title': f"{repo_name} - GitHub Trending项目",
                        'url': repo_url,
                        'summary': description or f"GitHub热门{language}项目，Star数：{stars}",
                        'source': self.source,
                        'author': repo_name.split('/')[0] if '/' in repo_name else '',
                        'tags': f'GitHub,{language},OpenSource',
                        'publish_time': datetime.now(),
                        'views': int(re.sub(r'[^\d]', '', stars) or 0),
                        'likes': 0
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
            
            for article_data in data:
                article = {
                    'title': article_data.get('title', ''),
                    'url': article_data.get('url', ''),
                    'summary': article_data.get('description', ''),
                    'source': self.source,
                    'author': article_data.get('user', {}).get('name', ''),
                    'tags': ','.join([tag.get('name', '') for tag in article_data.get('tag_list', [])]),
                    'publish_time': datetime.fromisoformat(article_data.get('published_at', '').replace('Z', '+00:00')),
                    'views': article_data.get('page_views_count', 0),
                    'likes': article_data.get('public_reactions_count', 0)
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
                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')),
                    'source': self.source,
                    'author': entry.get('author', ''),
                    'tags': 'Technology,Medium',
                    'publish_time': datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.now(),
                    'views': random.randint(100, 1000),  # Medium不提供具体数据
                    'likes': random.randint(10, 100)
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
                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'summary': self.clean_text(entry.get('summary', '')),
                    'source': self.source,
                    'author': entry.get('author', ''),
                    'tags': 'Tech News,Startup',
                    'publish_time': datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else datetime.now(),
                    'views': random.randint(500, 5000),
                    'likes': random.randint(20, 200)
                }
                articles.append(article)
            
            print(f"成功爬取 {len(articles)} 篇 TechCrunch 文章")
            return articles
            
        except Exception as e:
            print(f"爬取 TechCrunch 失败: {e}")
            return [] 