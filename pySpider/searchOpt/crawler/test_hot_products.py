#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试热点产品功能
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tech_news_web.settings")
django.setup()

from news.models import TechNews, HotProduct
from datetime import datetime, timedelta


def test_hot_products():
    print("=" * 60)
    print("热点产品功能测试")
    print("=" * 60)

    # 1. 检查产品类别的新闻数量
    print("\n1. 检查产品类别新闻数量:")
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

    for cat in product_categories:
        count = TechNews.objects.filter(category=cat).count()
        print(f"  {cat}: {count} 条新闻")

    # 2. 显示权重最高的产品新闻
    print("\n2. 权重最高的产品新闻 (前10条):")
    top_products = TechNews.objects.filter(category__in=product_categories).order_by(
        "-rate"
    )[:10]

    for i, news in enumerate(top_products, 1):
        print(f"  {i}. [{news.category}] {news.title[:50]}... (权重: {news.rate:.2f})")

    # 3. 检查HotProduct表的数据
    print("\n3. 当前热点产品排名:")
    recent_date = datetime.now().date() - timedelta(days=7)
    hot_products = HotProduct.objects.filter(period_start__gte=recent_date).order_by(
        "-period_start", "rank"
    )

    if hot_products.exists():
        current_period = None
        for hp in hot_products:
            if current_period != hp.period_start:
                current_period = hp.period_start
                print(f"\n  周期: {hp.period_start} 至 {hp.period_end}")
            print(
                f"  Rank {hp.rank}: [{hp.category}] {hp.title[:50]}... (权重: {hp.rate:.2f})"
            )
    else:
        print("  暂无数据。请运行: python3 manage.py update_hot_products")

    # 4. 统计信息
    print("\n4. 统计信息:")
    print(
        f"  产品新闻总数: {TechNews.objects.filter(category__in=product_categories).count()}"
    )
    print(f"  热点产品记录数: {HotProduct.objects.count()}")
    print(
        f"  最新更新时间: {HotProduct.objects.order_by('-updated_at').first().updated_at if HotProduct.objects.exists() else '无'}"
    )

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示:")
    print("  - 如果热点产品数据为空，请运行: python3 manage.py update_hot_products")
    print("  - 设置定时任务: 编辑 crontab_setup.sh 并配置 crontab")
    print("  - 查看使用说明: cat HOT_PRODUCTS_README.md")


if __name__ == "__main__":
    test_hot_products()
