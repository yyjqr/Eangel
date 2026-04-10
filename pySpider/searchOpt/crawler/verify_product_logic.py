#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
验证product_news筛选逻辑
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tech_news_web.settings")
django.setup()

from news.models import TechNews
from datetime import datetime, timedelta


def verify_product_news():
    print("=" * 70)
    print("验证 product_news 筛选逻辑")
    print("=" * 70)

    product_categories = [
        "机器人",
        "智能硬件",
        "汽车与自动驾驶",
        "VR/AR/XR",
        "军事",
        "航空航天",
        "军工与航天",
        "产品发布",
        "芯片与半导体",
    ]
    recent_14days = datetime.now().date() - timedelta(days=14)

    # 模拟views.py中的逻辑
    product_news_query = (
        TechNews.objects.filter(category__in=product_categories, rate__gt=2.0)
        .exclude(category__icontains="经济")
        .order_by("-rate", "-id")[:50]
    )

    product_news = []
    blocked_urls = ["google.com", "ft.com", "bloomberg.com"]

    print(f"\n处理 {product_news_query.count()} 条候选新闻...")
    print(f"筛选条件：权重>2.0, 类别为产品类, 最近14天, 非屏蔽域名\n")

    for news in product_news_query:
        # 检查URL是否被屏蔽
        is_blocked = any(domain in news.url.lower() for domain in blocked_urls)
        if is_blocked:
            continue

        # 检查时间
        is_recent = False
        pub_date_str = ""
        try:
            if hasattr(news, "publish_time") and news.publish_time:
                pub_time_str = str(news.publish_time)
                if len(pub_time_str) >= 10:
                    pub_date = datetime.strptime(pub_time_str[:10], "%Y-%m-%d").date()
                    days_ago = (datetime.now().date() - pub_date).days
                    pub_date_str = f"{pub_date} ({days_ago}天前)"

                    if pub_date >= recent_14days:
                        is_recent = True
                else:
                    # 通过ID判断
                    latest_id = TechNews.objects.order_by("-id").first().id
                    if news.id >= latest_id - 200:
                        is_recent = True
                        pub_date_str = "通过ID判断为最近"
            else:
                # 通过ID判断
                latest_id = TechNews.objects.order_by("-id").first().id
                if news.id >= latest_id - 200:
                    is_recent = True
                    pub_date_str = "无时间，通过ID判断"
        except Exception as e:
            # 解析失败，通过ID判断
            try:
                latest_id = TechNews.objects.order_by("-id").first().id
                if news.id >= latest_id - 200:
                    is_recent = True
                    pub_date_str = f"解析失败，通过ID判断"
            except:
                pass

        if is_recent:
            product_news.append(news)
            print(f"✅ [{news.category}] {news.title[:50]}...")
            print(f"   权重: {news.rate:.2f} | 时间: {pub_date_str}")
            print(f"   ID: {news.id} | URL: {news.url[:60]}...")
            print()

        if len(product_news) >= 5:
            break

    print("=" * 70)
    print(f"最终筛选出 {len(product_news)} 条产品新闻")
    print("=" * 70)

    if len(product_news) == 0:
        print("\n⚠️  警告：没有符合条件的产品新闻！")
        print("建议：")
        print("  1. 降低权重阈值（从2.0改为1.5）")
        print("  2. 运行 main-spider2.py 爬取更多产品新闻")
        print("  3. 扩大时间范围（从14天改为30天）")
    elif len(product_news) < 5:
        print(f"\n⚠️  产品新闻数量不足（{len(product_news)}/5）")
        print("建议运行 main-spider2.py 爬取更多产品新闻")
    else:
        print("\n✅ 产品新闻数量充足！")


if __name__ == "__main__":
    verify_product_news()
