#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import os
import sys
import ssl
import json
from datetime import datetime, timedelta
from email.utils import formataddr

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import encrypt_and_verify_url
import mysqlWriteNewsV2
import scrapers_military
from news_content_utils import build_article_content

with open(os.path.join(os.path.dirname(__file__), 'tech_key_config_map.json')) as cfg_f:
    cfg = json.load(cfg_f)

MILITARY_KEYWORD_WEIGHTS = {
    'military': 1.0,
    'defense': 1.0,
    'war': 0.9,
    'navy': 0.9,
    'army': 0.9,
    'air force': 0.9,
    'submarine': 1.0,
    'warship': 1.0,
    'destroyer': 0.8,
    'carrier': 0.8,
    'frigate': 0.8,
    'missile': 1.2,
    'drone': 1.0,
    'uav': 1.0,
    'fighter': 0.8,
    'jet': 0.6,
    'aircraft': 0.6,
    'radar': 0.7,
    'satellite': 0.7,
    'space': 0.4,
    'pentagon': 0.9,
    'marine': 0.6,
    'troops': 0.7,
    'combat': 0.7,
    'security': 0.5,
    'iran': 0.6,
    'russia': 0.6,
    'ukraine': 0.6,
    'china': 0.6,
    'nato': 0.7,
    '军事': 1.2,
    '国防': 1.0,
    '军工': 1.0,
    '战机': 0.9,
    '导弹': 1.2,
    '无人机': 1.1,
    '航母': 1.0,
    '海军': 0.9,
    '空军': 0.9,
    '陆军': 0.9,
    '舰艇': 0.8,
    '军舰': 0.9,
    '潜艇': 1.0,
    '雷达': 0.8,
    '军演': 0.8,
    '台海': 0.8,
    '南海': 0.8,
}

DEFAULT_THRESHOLD = cfg.get('MILITARY_RANK_THRESHOLD', 1.8)   # 原默认 0.5，已调高
MAX_WEIGHT_CAP  = cfg.get('MAX_WEIGHT_CAP', 5.0)              # 最大权重上限
OUTPUT_FILE = 'military_news_summary.txt'


def parse_db_publish_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        for fmt in ('%Y-%m-%d_%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
    return None


class NewsScraper:
    def __init__(self, source_name):
        self.source_name = source_name
        self.articles = []

    def scrape(self):
        raise NotImplementedError('子类必须实现 scrape 方法')

    def calculate_weight(self, title, summary='', tags=''):
        text = f'{title} {summary} {tags} {self.source_name}'.lower()
        score = 0.0
        for key, weight in MILITARY_KEYWORD_WEIGHTS.items():
            if key.lower() in text:
                score += float(weight)
        # 移除 fallback 0.6：无关键词命中则得 0 分不进入库
        return min(score, MAX_WEIGHT_CAP)

    def determine_category(self, title, tags=''):
        text = f'{title} {tags}'.lower()
        if any(word in text for word in ['drone', 'uav', 'fighter', 'air force', 'aircraft', 'missile', '战机', '导弹', '无人机', '空军']):
            return '航空航天'
        return '军事'

    def filter_and_store(self, keywords='军事'):
        filtered_articles = []
        six_months_ago = datetime.now() - timedelta(days=180)

        for article_tuple in self.articles:
            image_url = ''
            publish_time_obj = datetime.now()
            created_at_obj = datetime.now()
            summary_text = ''
            tags_text = ''

            if len(article_tuple) >= 8:
                title, url, weight, image_url, publish_time_obj, created_at_obj, summary_text, tags_text = article_tuple[:8]
            elif len(article_tuple) == 6:
                title, url, weight, image_url, publish_time_obj, created_at_obj = article_tuple
            elif len(article_tuple) == 4:
                title, url, weight, image_url = article_tuple
            else:
                title, url, weight = article_tuple

            if weight < DEFAULT_THRESHOLD:
                continue

            if not isinstance(publish_time_obj, datetime):
                publish_time_obj = datetime.now()
            if not isinstance(created_at_obj, datetime):
                created_at_obj = datetime.now()

            filtered_articles.append((title, url, weight, image_url, publish_time_obj, created_at_obj, summary_text))

            try:
                db_publish_time = parse_db_publish_time(mysqlWriteNewsV2.getArticlePublishTime(url))
                if db_publish_time:
                    if db_publish_time < six_months_ago:
                        print(f'文章已在数据库且超过半年，跳过入库: {url}')
                    else:
                        print(f'文章已在数据库，保留发送: {title[:50]}...')
                    continue

                category = self.determine_category(title, keywords)
                publish_time_str = publish_time_obj.strftime('%Y-%m-%d_%H:%M')
                content = build_article_content(
                    title=title,
                    category=category,
                    source=self.source_name,
                    summary=summary_text,
                    tags=tags_text,
                    keywords=keywords,
                )
                news_one = (
                    weight,
                    title,
                    self.source_name,
                    publish_time_str,
                    content,
                    url,
                    keywords,
                    category,
                    image_url,
                )
                sql = """ INSERT INTO techTB(Rate,title,author,publish_time,content,url,key_word,category,image_url) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) """
                result = mysqlWriteNewsV2.writeDb(sql, news_one)
                if result:
                    print(f'✅ 成功写入数据库 [{category}]: {title[:50]}...')
                else:
                    print(f'⚠️ 数据库写入失败，但保留邮件输出: {title[:50]}...')
            except Exception as e:
                print(f'⚠️ 数据库存储异常，但保留邮件输出: {title[:50]}... -> {e}')

        return filtered_articles

    def append_article(self, article, weight):
        self.articles.append((
            article['title'],
            article['url'],
            weight,
            article.get('image_url', ''),
            article.get('publish_time', datetime.now()),
            article.get('created_at', datetime.now()),
            article.get('summary', ''),
            article.get('tags', ''),
        ))


class TWZWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('The War Zone')
        self.scraper = scrapers_military.TWZScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,防务,TWZ')


class MilitaryComWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('Military.com')
        self.scraper = scrapers_military.MilitaryComScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,防务,Military.com')


class DefenseNewsWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('Defense News')
        self.scraper = scrapers_military.DefenseNewsScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,防务,Defense News')


class BreakingDefenseWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('Breaking Defense')
        self.scraper = scrapers_military.BreakingDefenseScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,防务,Breaking Defense')


class IfengMilitaryWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('凤凰军事')
        self.scraper = scrapers_military.IfengMilitaryScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,凤凰军事')


class HuanqiuMilitaryWrapperScraper(NewsScraper):
    def __init__(self):
        super().__init__('环球网军事')
        self.scraper = scrapers_military.HuanqiuMilitaryScraper()

    def scrape(self, limit=10):
        articles = self.scraper.scrape_articles(limit=limit)
        for art in articles:
            weight = self.calculate_weight(art.get('title', ''), art.get('summary', ''), art.get('tags', ''))
            self.append_article(art, weight)
        return self.filter_and_store('军事,环球军事')


class MilitaryNewsAggregator:
    def __init__(self):
        self.scrapers = [
            TWZWrapperScraper(),
            MilitaryComWrapperScraper(),
            DefenseNewsWrapperScraper(),
            BreakingDefenseWrapperScraper(),
            IfengMilitaryWrapperScraper(),
            HuanqiuMilitaryWrapperScraper(),
        ]

    def collect_news(self):
        all_articles = []
        print(f'📅 开始收集军事新闻 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'🔍 军事阈值: >= {DEFAULT_THRESHOLD}')
        print('-' * 60)

        for scraper in self.scrapers:
            print(f'\n📡 正在采集 {scraper.source_name}...')
            try:
                articles = scraper.scrape()
                print(f'✅ 找到 {len(articles)} 篇军事文章')
                all_articles.extend(articles)
            except Exception as e:
                print(f'❌ 采集失败: {scraper.source_name} -> {e}')

        all_articles.sort(key=lambda x: x[2], reverse=True)
        return all_articles

    def build_email_html(self, articles):
        date_str = datetime.now().strftime('%Y-%m-%d')
        html_parts = []
        html_parts.append(f'<html><body style="font-family:Arial,sans-serif;color:#333;">')
        html_parts.append(f'<h2>每日军事新闻摘要 - {date_str}</h2>')
        html_parts.append(f'<p>共收集到 <b>{len(articles)}</b> 篇军事文章</p><hr>')

        for idx, article in enumerate(articles, 1):
            title, url, weight = article[:3]
            publish_time = article[4] if len(article) > 4 else None
            summary = article[6] if len(article) > 6 else ''
            show_summary = summary and summary.strip().rstrip('。.') != title.strip().rstrip('。.')

            html_parts.append(f'<p style="margin-bottom:4px;"><b>{idx}.</b> '
                              f'[{weight:.2f}] <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a></p>')
            if isinstance(publish_time, datetime):
                html_parts.append(f'<p style="margin:0 0 2px 24px;font-size:12px;color:#888;">📅 {publish_time.strftime("%Y-%m-%d %H:%M")}</p>')
            if show_summary:
                html_parts.append(f'<p style="margin:0 0 12px 24px;font-size:13px;color:#555;">{summary[:300]}</p>')
            else:
                html_parts.append('<br>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def save_to_txt(self, articles, filename=OUTPUT_FILE):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f'每日军事新闻摘要 - {datetime.now().strftime("%Y-%m-%d")}\n')
            f.write(f'共收集到 {len(articles)} 篇军事文章\n')
            f.write('=' * 60 + '\n\n')

            for idx, article in enumerate(articles, 1):
                title, url, weight = article[:3]
                publish_time = article[4] if len(article) > 4 else None
                summary = article[6] if len(article) > 6 else ''
                show_summary = summary and summary.strip().rstrip('。.') != title.strip().rstrip('。.')

                f.write(f'{idx}. [{weight:.2f}] {title}\n')
                f.write(f'   🔗 {url}\n')
                if isinstance(publish_time, datetime):
                    f.write(f'   📅 发布时间: {publish_time.strftime("%Y-%m-%d %H:%M")}\n')
                if show_summary:
                    f.write(f'   📝 {summary[:200]}\n')
                f.write('\n')

        print(f'💾 军事新闻已保存到 {os.path.abspath(filename)}')
        return filename


def send_news_email(txt_file, recipient, html_content=None):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import smtplib

    _pwd = encrypt_and_verify_url.decrypt_getKey('dm1wbmFmYmxsdnR0YmJlaQ=='.encode('utf-8'))
    with open(txt_file, 'r', encoding='utf-8') as f:
        news_content = f.read()

    sender = '840056598@qq.com'
    subject = f'每日军事新闻摘要 - {datetime.now().strftime("%Y-%m-%d")}'

    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = formataddr(['亲爱的用户', recipient])
    msg['Subject'] = subject
    msg.attach(MIMEText(news_content, 'plain', 'utf-8'))
    if html_content:
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(sender, _pwd.decode('utf-8'))
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        print(f'📧 邮件已成功发送至 {recipient}')
        return True
    except Exception as e:
        print(f'❌ 邮件发送失败: {e}')
        return False


if __name__ == '__main__':
    aggregator = MilitaryNewsAggregator()
    articles = aggregator.collect_news()
    txt_file = aggregator.save_to_txt(articles)
    html_content = aggregator.build_email_html(articles)
    send_news_email(txt_file, '840056598@qq.com', html_content=html_content)
