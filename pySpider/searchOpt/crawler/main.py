#!/usr/bin/env python3
"""
TechDaily 技术文章采集器
自动从全球知名IT技术网站采集最新文章
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import TechNewsDB
from scrapers import (
    HackerNewsScraper,
    RedditScraper, 
    GitHubTrendingScraper,
    DevToScraper,
    MediumScraper,
    TechCrunchScraper
)

class TechCrawler:
    """技术文章爬虫主控制器"""
    
    def __init__(self, db_path="tech_news.db"):
        self.db = TechNewsDB(db_path)
        self.scrapers = {
            'hackernews': HackerNewsScraper(),
            'reddit': RedditScraper(),
            'github': GitHubTrendingScraper(),
            'devto': DevToScraper(),
            'medium': MediumScraper(),
            'techcrunch': TechCrunchScraper()
        }
        
    def crawl_all_sources(self, articles_per_source=2):
        """从所有源采集文章"""
        total_articles = 0
        total_success = 0
        
        print(f"🚀 开始采集全球IT技术文章...")
        print(f"📅 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 目标: 每个源采集 {articles_per_source} 篇文章")
        print("-" * 60)
        
        for source_name, scraper in self.scrapers.items():
            print(f"\n📡 正在采集 {scraper.source}...")
            
            try:
                articles = scraper.scrape_articles(limit=articles_per_source)
                success_count = 0
                error_count = 0
                
                for article in articles:
                    article_id = self.db.insert_article(article)
                    if article_id:
                        success_count += 1
                        total_success += 1
                    else:
                        error_count += 1
                    
                    total_articles += 1
                
                # 记录爬取统计
                self.db.insert_crawl_record(
                    source=scraper.source,
                    total=len(articles),
                    success=success_count,
                    error=error_count,
                    status="completed"
                )
                
                print(f"✅ {scraper.source}: 采集 {len(articles)} 篇，成功 {success_count} 篇，重复 {error_count} 篇")
                
            except Exception as e:
                print(f"❌ {scraper.source} 采集失败: {e}")
                self.db.insert_crawl_record(
                    source=scraper.source,
                    total=0,
                    success=0,
                    error=1,
                    status="failed",
                    error_msg=str(e)
                )
        
        print("\n" + "=" * 60)
        print(f"🎉 采集完成！")
        print(f"📊 总计尝试采集: {total_articles} 篇")
        print(f"✅ 成功存储: {total_success} 篇")
        print(f"🔄 重复文章: {total_articles - total_success} 篇")
        
        # 显示统计信息
        self.show_statistics()
        
    def crawl_single_source(self, source_name, limit=10):
        """从单个源采集文章"""
        if source_name not in self.scrapers:
            print(f"❌ 未知的数据源: {source_name}")
            print(f"📋 可用的数据源: {', '.join(self.scrapers.keys())}")
            return
        
        scraper = self.scrapers[source_name]
        print(f"📡 正在从 {scraper.source} 采集 {limit} 篇文章...")
        
        try:
            articles = scraper.scrape_articles(limit=limit)
            success_count = 0
            
            for article in articles:
                article_id = self.db.insert_article(article)
                if article_id:
                    success_count += 1
            
            self.db.insert_crawl_record(
                source=scraper.source,
                total=len(articles),
                success=success_count,
                error=len(articles) - success_count,
                status="completed"
            )
            
            print(f"✅ 采集完成: {len(articles)} 篇，成功存储 {success_count} 篇")
            
        except Exception as e:
            print(f"❌ 采集失败: {e}")
    
    def show_statistics(self):
        """显示数据库统计信息"""
        stats = self.db.get_crawl_stats()
        
        print(f"\n📈 数据库统计:")
        print(f"📚 总文章数: {stats.get('total_articles', 0)}")
        print(f"📅 今日采集: {stats.get('today_articles', 0)}")
        
        print(f"\n📊 按来源统计:")
        for source, count in stats.get('source_stats', []):
            print(f"  {source}: {count} 篇")
    
    def list_recent_articles(self, limit=10):
        """列出最近采集的文章"""
        articles = self.db.get_articles(limit=limit)
        
        print(f"\n📰 最近采集的 {len(articles)} 篇文章:")
        print("-" * 80)
        
        for i, article in enumerate(articles, 1):
            print(f"{i}. 【{article['source']}】{article['title'][:60]}...")
            print(f"   🔗 {article['url']}")
            print(f"   ⏰ {article['crawl_time']}")
            print()

def main():
    parser = argparse.ArgumentParser(description='TechDaily 技术文章采集器')
    #parser.add_argument('--source', help='指定采集源 (hackernews, reddit, github, devto, medium, techcrunch)')
    parser.add_argument('--source', help='指定采集源 (reddit, github, devto, medium)')
    
    parser.add_argument('--limit', type=int, default=10, help='每个源采集的文章数量 (默认: 10)')
    parser.add_argument('--list', action='store_true', help='列出最近采集的文章')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--quick', action='store_true', help='快速采集模式 (每个源2篇)')
    
    args = parser.parse_args()
    
    crawler = TechCrawler()
    
    if args.list:
        crawler.list_recent_articles(args.limit)
    elif args.stats:
        crawler.show_statistics()
    elif args.source:
        crawler.crawl_single_source(args.source, args.limit)
    elif args.quick:
        crawler.crawl_all_sources(articles_per_source=2)
    else:
        # 默认采集模式：每个源采集指定数量的文章
        articles_per_source = min(args.limit, 3)  # 限制每个源最多3篇，避免过载
        crawler.crawl_all_sources(articles_per_source)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  采集被用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc() 
