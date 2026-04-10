#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试优化后的产品新闻筛选
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tech_news_web.settings")
django.setup()

from news.models import TechNews
from datetime import datetime, timedelta


def test_product_news_filter():
    print("=" * 70)
    print("产品新闻筛选优化测试")
    print("=" * 70)

    # 测试条件
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

    print(f"\n筛选条件：")
    print(f"  - 类别：{', '.join(product_categories)}")
    print(f"  - 权重：> 2.0")
    print(f"  - 时间：最近14天（{recent_14days} 之后）")
    print(f"  - 排除：包含'经济'的分类")

    # 1. 查询所有产品类别的新闻
    print(f"\n1️⃣  所有产品类别新闻统计：")
    for cat in product_categories:
        total = TechNews.objects.filter(category=cat).count()
        high_rate = TechNews.objects.filter(category=cat, rate__gt=2.0).count()
        print(f"  {cat}: {total} 条 (权重>2: {high_rate} 条)")

    # 2. 应用筛选条件
    print(f"\n2️⃣  应用筛选条件后：")
    filtered_news = (
        TechNews.objects.filter(category__in=product_categories, rate__gt=2.0)
        .exclude(category__icontains="经济")
        .order_by("-rate", "-id")[:30]
    )

    print(f"  找到 {filtered_news.count()} 条符合条件的产品新闻")

    # 3. 显示前10条
    print(f"\n3️⃣  权重最高的产品新闻（前10条）：")
    for i, news in enumerate(filtered_news[:10], 1):
        pub_time = ""
        try:
            if hasattr(news, "publish_time") and news.publish_time:
                pub_time_str = str(news.publish_time)
                if len(pub_time_str) >= 10:
                    pub_date = datetime.strptime(pub_time_str[:10], "%Y-%m-%d").date()
                    days_ago = (datetime.now().date() - pub_date).days
                    pub_time = f" [{days_ago}天前]"
        except:
            pass

        print(f"  {i}. [{news.category}] {news.title[:60]}...")
        print(f"     权重: {news.rate:.2f}{pub_time} | 来源: {news.author}")

    # 4. 检查是否有经济类文章混入
    print(f"\n4️⃣  检查经济类文章：")
    economic_categories = [
        "宏观经济",
        "经济综合",
        "经济评论",
        "股市投资",
        "金融科技",
        "贸易与供应链",
        "企业动态",
        "产业经济",
    ]
    economic_news = TechNews.objects.filter(
        category__in=product_categories, rate__gt=2.0
    ).filter(Q(category__icontains="经济") | Q(category__in=economic_categories))

    if economic_news.exists():
        print(f"  ⚠️  发现 {economic_news.count()} 条经济类文章：")
        for news in economic_news[:5]:
            print(f"    - [{news.category}] {news.title[:50]}...")
    else:
        print(f"  ✅ 没有经济类文章混入")

    # 5. 时间分布
    print(f"\n5️⃣  时间分布：")
    time_ranges = [("今天", 0), ("最近3天", 3), ("最近7天", 7), ("最近14天", 14), ("14天前", 999)]

    for range_name, days in time_ranges:
        if days == 999:
            # 14天前
            count = 0
            for news in filtered_news:
                try:
                    if hasattr(news, "publish_time") and news.publish_time:
                        pub_time_str = str(news.publish_time)
                        if len(pub_time_str) >= 10:
                            pub_date = datetime.strptime(
                                pub_time_str[:10], "%Y-%m-%d"
                            ).date()
                            if pub_date < recent_14days:
                                count += 1
                except:
                    pass
            print(f"  {range_name}: {count} 条")
        else:
            target_date = datetime.now().date() - timedelta(days=days)
            count = 0
            for news in filtered_news:
                try:
                    if hasattr(news, "publish_time") and news.publish_time:
                        pub_time_str = str(news.publish_time)
                        if len(pub_time_str) >= 10:
                            pub_date = datetime.strptime(
                                pub_time_str[:10], "%Y-%m-%d"
                            ).date()
                            if pub_date >= target_date:
                                count += 1
                except:
                    pass
            print(f"  {range_name}: {count} 条")

    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    print("\n建议：")
    print("  - 如果产品新闻数量不足，请运行 main-spider2.py 爬取更多数据")
    print("  - 如果有旧新闻，确认已添加时间过滤逻辑")
    print("  - 权重阈值可根据实际情况调整（当前为 2.0）")


if __name__ == "__main__":
    from django.db.models import Q

    test_product_news_filter()
