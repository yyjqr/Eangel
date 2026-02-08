#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
测试所有经济新闻爬虫
"""

from scrapers_economy import (
    FinancialTimesScraper,
    SinaFinanceScraper,
    PhoenixFinanceScraper,
    ShanghaiSecuritiesNewsScraper,
)


def test_scraper(name, scraper_class, limit=10):
    """测试单个爬虫"""
    print(f"\n{'='*60}")
    print(f"测试 {name}")
    print("=" * 60)

    try:
        scraper = scraper_class()
        articles = scraper.scrape_articles(limit=limit)

        print(f"✅ 获取 {len(articles)} 篇文章")

        if articles:
            print("\n前3篇文章：")
            for i, art in enumerate(articles[:3], 1):
                print(f"\n{i}. {art['title'][:80]}")
                print(f"   🔗 {art['url'][:100]}")
                if art.get("summary"):
                    print(f"   📝 {art['summary'][:80]}")
        else:
            print("⚠️  未获取到文章")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    scrapers = [
        ("Financial Times", FinancialTimesScraper),
        ("新浪财经", SinaFinanceScraper),
        ("凤凰财经", PhoenixFinanceScraper),
        ("上海证券报", ShanghaiSecuritiesNewsScraper),
    ]

    print("开始测试经济新闻爬虫...")
    print(f"共 {len(scrapers)} 个数据源")

    total_articles = 0
    for name, scraper_class in scrapers:
        test_scraper(name, scraper_class)

    print(f"\n{'='*60}")
    print("测试完成！")
