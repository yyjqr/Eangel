## -*- coding: UTF-8 -*-
"""
更新热点产品排名
每2天运行一次，从新闻数据中提取热门产品并保存到HotProduct表
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from news.models import TechNews, HotProduct


class Command(BaseCommand):
    help = '更新热点产品排名（每2天运行）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='分析最近N天的数据（默认2天）'
        )
        parser.add_argument(
            '--top',
            type=int,
            default=5,
            help='保存前N个热门产品（默认5个）'
        )

    def handle(self, *args, **options):
        days = options['days']
        top_n = options['top']

        self.stdout.write(f'开始更新热点产品排名...')
        self.stdout.write(f'分析周期：最近 {days} 天')
        self.stdout.write(f'排名数量：前 {top_n} 名')

        # 计算时间范围
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # 定义产品类别
        product_categories = [
            '机器人',
            '智能硬件',
            '汽车与自动驾驶',
            'VR/AR/XR',
            '军事',
            '航空航天',
            '军工与航天',
            '产品发布',
            '芯片与半导体'
        ]

        # 获取该时间段内的产品新闻，按权重排序
        product_news = TechNews.objects.filter(
            category__in=product_categories
        ).order_by('-rate', '-id')[:100]  # 先取前100条

        if not product_news:
            self.stdout.write(self.style.WARNING('没有找到产品新闻'))
            return

        # 按类别分组统计
        category_stats = {}
        for news in product_news:
            cat = news.category
            if cat not in category_stats:
                category_stats[cat] = []
            category_stats[cat].append(news)

        # 从每个类别选择权重最高的产品
        all_products = []
        for cat, news_list in category_stats.items():
            # 每个类别取前2名
            for news in news_list[:2]:
                all_products.append({
                    'title': news.title,
                    'url': news.url,
                    'category': news.category,
                    'rate': news.rate,
                    'image_url': news.image_url or '',
                    'source': news.author
                })

        # 按权重排序，取前N名
        all_products.sort(key=lambda x: x['rate'], reverse=True)
        top_products = all_products[:top_n]

        if not top_products:
            self.stdout.write(self.style.WARNING('没有符合条件的产品'))
            return

        # 清除该周期的旧数据
        HotProduct.objects.filter(
            period_type='weekly',
            period_start=start_date
        ).delete()

        # 保存新的热点产品排名
        created_count = 0
        for rank, product in enumerate(top_products, 1):
            HotProduct.objects.create(
                title=product['title'],
                url=product['url'],
                category=product['category'],
                rate=product['rate'],
                image_url=product['image_url'],
                source=product['source'],
                rank=rank,
                period_type='weekly',
                period_start=start_date,
                period_end=end_date
            )
            created_count += 1
            self.stdout.write(
                f"  Rank {rank}: [{product['category']}] {product['title'][:50]}... (权重: {product['rate']:.2f})"
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ 成功更新 {created_count} 个热点产品排名')
        )
        self.stdout.write(f'周期：{start_date} 至 {end_date}')

        # 显示各类别统计
        self.stdout.write('\n各类别产品数量：')
        for cat, count in category_stats.items():
            self.stdout.write(f'  {cat}: {len(count)} 个产品')
