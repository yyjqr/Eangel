## -*- coding: UTF-8 -*-
#@author: JACK YANG
#@date:
      # 2022.09 add rank map
      # 2024.10 scikit-learn
      # 2025.07 scraper类爬虫
# @Email: yyjqr789@sina.com

#!/usr/bin/python3

import requests
import argparse
import sys
from bs4 import BeautifulSoup
import os
from datetime import datetime
from typing import List, Dict, Optional

import encrypt_and_verify_url
from email.utils import formataddr
import ssl
import json
import re
import difflib
import time
try:
    # Silence insecure request warnings when fallback verify=False is used
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass

#from sklearn.feature_extraction.text import TfidfVectorizer

# 读取配置
with open(os.path.join(os.path.dirname(__file__), '.', 'tech_key_config_map.json')) as cfg_f:
    cfg = json.load(cfg_f)
KEYWORDS_RANK_MAP = cfg.get('KEYWORDS_RANK_MAP', {})
BLOCKED_DOMAINS = cfg.get('BLOCKED_DOMAINS', [])
CUSTOM_SITES = cfg.get('CUSTOM_SITES', [])
# 是否在必要时请求详情页面以提取发布时间（默认 False，避免大量额外请求）
FETCH_DETAILS_FOR_DATE = cfg.get('FETCH_DETAILS_FOR_DATE', False)

# 全局配置
OUTPUT_FILE = "tech_news_summary.txt"
# 默认阈值，可在配置中覆盖
kRankLevelValue = cfg.get('RANK_THRESHOLD', 0.5)
# Define a set of common words to filter out (stop words)
stop_words = set([
    "is", "the", "this", "and", "a", "to", "of", "in", "for", "on",
    "if", "has", "are", "was", "be", "by", "at", "that", "it", "its",
    "as","about",
    "an", "or", "but", "not", "from", "with", "which", "there", "when",
    "so", "all", "any", "some", "one", "two", "three", "four", "five"
])



class NewsScraper:
    """通用新闻爬虫基类"""
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = requests.Session()  # 添加共享的 Session 对象
        # 添加重试策略以提升嵌入式设备或不稳定网络下的健壮性
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry = Retry(total=3, backoff_factor=0.3, status_forcelist=(500,502,503,504))
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        except Exception:
            pass
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })
        self.base_url = ""
        self.articles = []
    def scrape(self):
        """子类需实现的具体爬取逻辑"""
        raise NotImplementedError("子类必须实现 scrape 方法")
    
    def filter_and_store(self):
        """过滤并存储符合条件的文章"""
        filtered_articles = []
        for item in self.articles:
            # 支持 (title,url,weight) 和 (title,url,weight,date)
            if not item or len(item) < 3:
                continue
            title = item[0]
            url = item[1]
            weight = item[2]
            date = item[3] if len(item) > 3 else None
            if weight > kRankLevelValue:
                filtered_articles.append((title, url, weight, date))
        return filtered_articles
    # 计算关键词权重
    def calculate_keyword_weights(self, texts, keywords):
        # 使用轻量模糊匹配计算权重，避免每次构建 TF-IDF
        text = ' '.join(texts)
        return compute_rank_from_map(text, keywords, fuzzy=True, threshold=0.7)


def compute_rank_from_map(text, key_map, fuzzy=False, threshold=0.8):
    if not text or not key_map:
        return 0.0
    text_lower = re.sub(r'\W+', ' ', text).lower()
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


def _parse_monthname_date(text: str) -> Optional[str]:
    # 支持像 "September 8, 2025" 或 "Sep 8, 2025"
    months = {
        'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12
    }
    m = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s*(20\d{2})', text)
    if m:
        mon = m.group(1).lower()[:3]
        d = int(m.group(2))
        y = int(m.group(3))
        monn = months.get(mon)
        if monn:
            try:
                return f"{y:04d}-{monn:02d}-{d:02d}"
            except Exception:
                return None
    return None


def extract_date_from_url_or_title(url: str, title: str, session: requests.Session = None, fetch_details: bool = False) -> Optional[str]:
    # 1) 从 URL 中匹配 /YYYY/MM/DD/ 或 /YYYY/MM/DD- 或 /YYYY/MM-DD 等常见格式
    try:
        if url:
            m = re.search(r'/([12]\d{3})[/-](\d{1,2})[/-](\d{1,2})/', url)
            if not m:
                # 有些 URL 形式为 /YYYY/MM/DD/slug 或 /YYYY/MM/DD
                m = re.search(r'/([12]\d{3})/([01]?\d)/([0-3]?\d)(?:/|$)', url)
            if m:
                y = int(m.group(1))
                mo = int(m.group(2))
                d = int(m.group(3))
                return f"{y:04d}-{mo:02d}-{d:02d}"
    except Exception:
        pass

    # 2) 从标题中解析 MonthName DD, YYYY
    if title:
        dt = _parse_monthname_date(title)
        if dt:
            return dt
        m2 = re.search(r'(20\d{2})', title)
        if m2:
            # 只找到年份，返回年份占位
            return f"{m2.group(1)}"

    # 3) 可选：请求详情页并从 meta 标签或 time 标签中读取
    if fetch_details and session and url:
        try:
            resp = session.get(url, timeout=6)
            if resp and getattr(resp, 'status_code', None) == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # common meta tags
                meta_props = [
                    ('property','article:published_time'),
                    ('name','article:published_time'),
                    ('name','pubdate'),
                    ('name','publishdate'),
                    ('name','publish_date'),
                    ('name','date'),
                    ('itemprop','datePublished')
                ]
                for attr, val in meta_props:
                    tag = soup.find('meta', attrs={attr: val})
                    if tag and tag.get('content'):
                        cont = tag.get('content')
                        m = re.search(r'(20\d{2})[-/](\d{1,2})[-/](\d{1,2})', cont)
                        if m:
                            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                # 查找 time 标签
                t = soup.find('time')
                if t:
                    # 优先 datetime 属性
                    dtstr = t.get('datetime') or t.get_text()
                    m = re.search(r'(20\d{2})[-/](\d{1,2})[-/](\d{1,2})', dtstr)
                    if m:
                        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass

    return None


class MitScraper(NewsScraper):
    """MIT Technology Review 爬虫"""
    def __init__(self):
        super().__init__("MIT Technology Review")
    
    def scrape(self):
        url = 'https://www.technologyreview.com/'
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        news_elements = soup.find_all(class_='homepageStoryCard__wrapper--5d95dc382241d259dc249996a6e29782')
        print(f"weight test")   
        for news_element in news_elements:
            try:
                title_elem = news_element.find(class_='homepageStoryCard__hed--92c78a74bbc694463e43e32aafbbdfd7')
                link_elem = news_element.find('a')
                
                if title_elem and link_elem:
                    title = title_elem.text.strip()
                    url = link_elem['href']
                    
                    # 确保URL是完整的
                    if not url.startswith('http'):
                        url = f"https://www.technologyreview.com{url}"
                    
                    # 尝试从 URL 或标题中提取发布日期（无需再请求详情页）
                    pubdate = extract_date_from_url_or_title(url, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                    # 计算新闻权重
                    weight = self.calculate_weight(title)
                    if weight > 0 :
                        print(f"{url},  ###weight is: {weight:.2f}")
                    self.articles.append((title, url, weight, pubdate))
            except Exception as e:
                print(f"处理文章时出错: {str(e)}")
        
        return self.filter_and_store()
    
    def calculate_weight(self, title):
        """计算新闻权重（简化版）"""
        # 这里使用您的实际权重计算逻辑
        return self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
        #return 0.3  # 示例值

class HackerNewsScraper(NewsScraper):
    """Hacker News 爬虫"""
    def __init__(self):
        #super().__init__("Hacker News")
        super().__init__("Hacker News")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.source = "Hacker News"
    def scrape(self, limit: int = 10) -> List[Dict]:
        """爬取 Hacker News 热门文章"""
        articles = []
        try:
            # 获取热门文章ID
            response = self.session.get(f"{self.base_url}/topstories.json")
            story_ids = response.json()[:limit]

            for story_id in story_ids:
                time.sleep(0.1)

                # 获取文章详情
                story_response = self.session.get(f"{self.base_url}/item/{story_id}.json", timeout=6)
                story_data = story_response.json()

                if story_data and story_data.get('url'):
                    title = story_data.get('title', '')
                    url = story_data.get('url', '')
                    # 尝试从 URL 或标题中提取发布日期
                    pubdate = extract_date_from_url_or_title(url, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                    # 计算新闻权重
                    weight = self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
                    self.articles.append((title, url, weight, pubdate))

            print(f"成功爬取 {len(self.articles)} 篇 Hacker News 文章")
            return self.filter_and_store()

        except Exception as e:
            print(f"爬取 Hacker News 失败: {e}")
            return []


class GitHubTrendingScraper(NewsScraper):
    """爬取 GitHub Trending 页面"""
    def __init__(self):
        super().__init__("GitHub Trending")

    def scrape(self):
        from urllib.parse import urljoin, urlparse
        url = 'https://github.com/trending'
        try:
            # 首先尝试正常请求
            resp = self.session.get(url, timeout=8)
            if resp is None or getattr(resp, 'status_code', None) != 200:
                raise Exception(f"非200响应: {getattr(resp, 'status_code', None)}")
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            print(f"GitHubTrendingScraper 初次请求失败: {e}")
            # 在受限环境（嵌入式设备）中，有时需要忽略证书或禁用 hostname 检查来尝试获取页面（仅作降级诊断）
            try:
                resp = self.session.get(url, timeout=8, verify=False)
                if resp is None or getattr(resp, 'status_code', None) != 200:
                    raise Exception(f"降级请求非200: {getattr(resp, 'status_code', None)}")
                soup = BeautifulSoup(resp.text, 'html.parser')
                print("GitHubTrendingScraper: 使用 verify=False 成功获取页面（降级模式）")
            except Exception as e2:
                print(f"GitHubTrendingScraper 降级请求也失败: {e2}")
                # 最后一招：尝试通过第三方文本代理服务获取页面（例如 r.jina.ai）——适用于本地 TLS/SNI 限制场景
                try:
                    proxy_url = f"https://r.jina.ai/http://github.com/trending"
                    print(f"尝试通过代理抓取: {proxy_url}")
                    proxy_resp = self.session.get(proxy_url, timeout=10)
                    if proxy_resp is None or getattr(proxy_resp, 'status_code', None) != 200:
                        raise Exception(f"代理非200: {getattr(proxy_resp, 'status_code', None)}")
                    soup = BeautifulSoup(proxy_resp.text, 'html.parser')
                    print("GitHubTrendingScraper: 通过代理成功获取页面")
                except Exception as e3:
                    print(f"GitHubTrendingScraper 代理也失败: {e3}")
                    return []

        # 解析 trending 项目（尽量不额外发起详情页请求，降低网络负担）
        items = soup.select('article.Box-row h1 a') or soup.select('h1.h3 a') or soup.select('article')
        for a in items:
            try:
                title = a.get_text(separator=' ', strip=True)
                href = a.get('href')
                if not href:
                    # 有时 a 是容器，需要在子元素查找
                    link_el = a.find('a') if hasattr(a, 'find') else None
                    href = link_el.get('href') if link_el is not None else None
                    if not href:
                        continue
                link = href if href.startswith('http') else urljoin('https://github.com', href)

                # 跳过被配置为阻断的域名
                parsed = urlparse(link)
                domain = parsed.netloc.lower() if parsed.netloc else ''
                skip = False
                for bd in BLOCKED_DOMAINS:
                    if bd and bd in domain:
                        skip = True
                        break
                if skip:
                    # 跳过已知受限域名
                    continue

                # 只使用标题文本进行权重计算（避免请求详情页）
                pubdate = extract_date_from_url_or_title(link, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                weight = self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
                self.articles.append((title, link, weight, pubdate))
            except Exception as e:
                print(f"GitHubTrendingScraper 解析单项失败: {e}")

        return self.filter_and_store()


class DevToScraper(NewsScraper):
    """爬取 Dev.to 热门文章"""
    def __init__(self):
        super().__init__("Dev.to")

    def scrape(self):
        url = 'https://dev.to/t/trending'
        try:
            resp = self.session.get(url, timeout=8)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('h2 a, h3 a, a.crayons-story__hidden-navigation')
            for a in items:
                title = a.get_text(strip=True)
                href = a.get('href')
                if not href:
                    continue
                if href.startswith('http'):
                    link = href
                else:
                    link = 'https://dev.to' + href
                pubdate = extract_date_from_url_or_title(link, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                weight = self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
                self.articles.append((title, link, weight, pubdate))
        except Exception as e:
            print(f"DevToScraper 失败: {e}")
        return self.filter_and_store()


class AITopicsScraper(NewsScraper):
    """爬取 AITopics 搜索结果"""
    def __init__(self):
        super().__init__("AITopics")

    def scrape(self):
        url = 'https://aitopics.org/search'
        try:
            resp = self.session.get(url, timeout=8)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.searchtitle a')
            for a in items:
                title = a.get_text(strip=True)
                href = a.get('href')
                if not href:
                    continue
                if href.startswith('http'):
                    link = href
                else:
                    link = 'https://aitopics.org' + href
                pubdate = extract_date_from_url_or_title(link, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                weight = self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
                self.articles.append((title, link, weight, pubdate))
        except Exception as e:
            print(f"AITopicsScraper 失败: {e}")
        return self.filter_and_store()


class GenericSiteScraper(NewsScraper):
    """基于配置的通用站点爬虫：支持 item/title/link 的 CSS 选择器

    配置字段示例 (CUSTOM_SITES 数组中的对象):
      - name: 名称
      - url: 站点首页或列表页 URL
      - item_selector: 列表项 CSS 选择器 (可选)
      - title_selector: 在 item 内提取标题的选择器 (可选)
      - link_selector: 在 item 内提取链接的选择器 (可选)
      - rate_limit_ms: 在请求前等待的毫秒数 (可选)
      - headers: 可选的 headers 对象，会临时合并到 session.headers
    """
    def __init__(self, source_name, site_cfg: dict):
        super().__init__(source_name)
        self.site_cfg = site_cfg

    def scrape(self):
        url = self.site_cfg.get('url')
        if not url:
            return []
        item_sel = self.site_cfg.get('item_selector')
        title_sel = self.site_cfg.get('title_selector')
        link_sel = self.site_cfg.get('link_selector')
        rate_limit_ms = int(self.site_cfg.get('rate_limit_ms', 0) or 0)
        site_headers = self.site_cfg.get('headers') or {}
        try:
            # 临时应用站点 headers
            original_headers = dict(self.session.headers)
            if isinstance(site_headers, dict) and site_headers:
                self.session.headers.update(site_headers)

            # rate limit
            if rate_limit_ms > 0:
                time.sleep(rate_limit_ms / 1000.0)

            resp = self.session.get(url, timeout=10)
            # 恢复原始 headers
            self.session.headers.clear()
            self.session.headers.update(original_headers)

            soup = BeautifulSoup(resp.text, 'html.parser')
            if item_sel:
                items = soup.select(item_sel)
            else:
                items = soup.select('article')
            for it in items:
                title = None
                link = None
                if title_sel:
                    t = it.select_one(title_sel)
                    if t:
                        title = t.get_text(strip=True)
                if not title:
                    a = it.find('a')
                    if a:
                        title = a.get_text(strip=True)
                if link_sel:
                    l = it.select_one(link_sel)
                    if l and l.get('href'):
                        link = l.get('href')
                if not link:
                    a = it.find('a')
                    if a and a.get('href'):
                        link = a.get('href')
                if link and link.startswith('/'):
                    base = url.rstrip('/')
                    link = base + link
                if title and link:
                    pubdate = extract_date_from_url_or_title(link, title, session=self.session, fetch_details=FETCH_DETAILS_FOR_DATE)
                    weight = self.calculate_keyword_weights([title], KEYWORDS_RANK_MAP)
                    self.articles.append((title, link, weight, pubdate))
        except Exception as e:
            print(f"GenericSiteScraper({self.source_name}) 失败: {e}")
        return self.filter_and_store()


class TechNewsAggregator:
    """科技新闻聚合器"""
    def __init__(self):
        # 内置爬虫
        self.scrapers = [
            MitScraper(),
            # 社区和平台
            HackerNewsScraper(),
            GitHubTrendingScraper() if 'GitHubTrendingScraper' in globals() else None,
            DevToScraper() if 'DevToScraper' in globals() else None,
            AITopicsScraper() if 'AITopicsScraper' in globals() else None,
        ]
        # 移除 None
        self.scrapers = [s for s in self.scrapers if s]
        # 加载配置中自定义站点
        for site in CUSTOM_SITES:
            try:
                gs = GenericSiteScraper(site.get('name', 'custom'), site)
                self.scrapers.append(gs)
            except Exception as e:
                print(f"加载自定义站点失败: {site} -> {e}")
    
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"每日科技新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"共收集到 {len(articles)} 篇高价值文章\n")
            f.write("=" * 60 + "\n\n")
            
            for idx, art in enumerate(articles, 1):
                # art is (title,url,weight,date)
                title = art[0]
                url = art[1]
                weight = art[2]
                date = art[3] if len(art) > 3 else None
                date_part = f" ({date})" if date else ""
                f.write(f"{idx}. [{weight:.2f}]{date_part} {title}\n")
                f.write(f"   🔗 {url}\n\n")
        
        print(f"💾 新闻已保存到 {os.path.abspath(filename)}")
        return filename

def send_news_email(txt_file, recipient):
    """发送包含新闻摘要的邮件"""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib
    _pwd =encrypt_and_verify_url.decrypt_getKey("dm1wbmFmYmxsdnR0YmJlaQ==".encode("utf-8"))
    # 读取文本文件内容
    with open(txt_file, 'r', encoding='utf-8') as f:
        news_content = f.read()
    
    # 邮件配置
    sender = "840056598@qq.com"
    password = _pwd
    subject = f"每日科技新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}"
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender
    receiver = recipient 
    msg['To']=formataddr(["亲爱的用户",receiver])  #括号里的对应收件人邮箱
    msg['Subject'] = subject
    
    # 添加文本内容
    msg.attach(MIMEText(news_content, 'plain', 'utf-8'))
    print(f"send subject {subject}")
    # 创建安全上下文（解决SSL验证问题）
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # 发送邮件
    try:
        #with smtplib.SMTP_SSL('smtp.qq.com', 465, context) as server:
            #server.login(sender, _pwd.decode("utf-8"))
            #print("login email OK\n")
            #server.sendmail(sender, [receiver,], msg.as_string())
        server=smtplib.SMTP_SSL("smtp.qq.com",465) #发件人邮箱中的SMTP服务器，端口是25 (默认）---------->465
        server.login(sender,_pwd.decode("utf-8"))  #括号中对应的是发件人邮箱账号、邮箱密码
        server.sendmail(sender,[receiver,],msg.as_string())  #括号中对应的是发件人邮箱账号、收件人邮箱账号、发送邮件
        print(f"📧 邮件已成功发送至 {recipient}")
        print ('SEND NEWS AND IMG OK')
        server.quit()  #这句是关闭连接
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
    parser = argparse.ArgumentParser(description="Tech news aggregator")
    parser.add_argument('--dry-run', action='store_true', help='只收集并保存结果，跳过发送邮件')
    parser.add_argument('--github-only', action='store_true', help='仅运行 GitHub Trending 抓取，用于测试')
    args = parser.parse_args()

    if args.github_only:
        print("仅运行 GitHub Trending 抓取（dry-run 模式不会发送邮件）")
        gs = GitHubTrendingScraper()
        articles = gs.scrape()
        # 打印结果并保存
        for idx, art in enumerate(articles, 1):
            title = art[0]
            url = art[1]
            weight = art[2]
            date = art[3] if len(art) > 3 else None
            date_part = f" ({date})" if date else ""
            print(f"{idx}. [{weight:.2f}]{date_part} {title}\n   {url}\n")
        out = TechNewsAggregator().save_to_txt(articles)
        if not args.dry_run:
            send_news_email(out, "840056598@qq.com")
        else:
            print("--dry-run: 已跳过发送邮件")
        sys.exit(0)

    # 创建聚合器并收集新闻
    aggregator = TechNewsAggregator()
    articles = aggregator.collect_news()

    # 保存到文本文件
    txt_file = aggregator.save_to_txt(articles)

    # 发送邮件（除非 dry-run）
    if args.dry_run:
        print("--dry-run: 跳过发送邮件")
    else:
        send_news_email(txt_file, "840056598@qq.com")

    # 可选：清理临时文件
    # os.remove(txt_file)
