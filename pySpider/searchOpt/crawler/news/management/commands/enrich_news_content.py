"""
enrich_news_content.py
======================
批量为 techTB 表中 content 字段为空或内容稀少的文章
通过爬取原文前 3 句来补充 content。

支持分类过滤（tech / economy / products）、并发数控制、
crawl4ai 重路径开关，以及 dry-run 模式。

用法示例：
  python manage.py enrich_news_content --limit 100
  python manage.py enrich_news_content --category 经济 --limit 50
  python manage.py enrich_news_content --use-crawl4ai --limit 20
  python manage.py enrich_news_content --dry-run --limit 10

定时任务（crontab）示例：
  # 每天凌晨 3 点补充 200 篇
  0 3 * * * cd /home/nvidia/valueSearch/value-test2026/crawler && python manage.py enrich_news_content --limit 200 >> /tmp/enrich.log 2>&1
"""

import sys
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# tech / economy / products 三大方向的分类标签
TECH_CATEGORIES = {"科技", "人工智能", "芯片与半导体", "新能源", "科学与数学"}
ECONOMY_CATEGORIES = {"宏观经济", "经济综合", "经济评论", "股市投资", "金融科技", "贸易与供应链", "企业动态", "产业经济"}
PRODUCT_CATEGORIES = {
    "机器人",
    "智能硬件",
    "汽车与自动驾驶",
    "VR/AR/XR",
    "产品发布",
    "航空航天",
    "军事",
    "军工与航天",
}

CATEGORY_MAP = {
    "tech": TECH_CATEGORIES,
    "economy": ECONOMY_CATEGORIES,
    "product": PRODUCT_CATEGORIES,
    "products": PRODUCT_CATEGORIES,
    "all": TECH_CATEGORIES | ECONOMY_CATEGORIES | PRODUCT_CATEGORIES,
}


class Command(BaseCommand):
    help = "批量为 content 字段为空/稀少的文章抓取原文前3句（tech、economy、products）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=100, help="本次最多处理多少篇文章（默认 100）"
        )
        parser.add_argument(
            "--category",
            type=str,
            default="all",
            help="分类过滤：tech | economy | product | all（默认 all）",
        )
        parser.add_argument(
            "--use-crawl4ai",
            action="store_true",
            default=False,
            help="强制使用 crawl4ai（适合 JS 密集站，速度慢）",
        )
        parser.add_argument(
            "--workers", type=int, default=3, help="并发线程数（默认 3，避免过多同时请求）"
        )
        parser.add_argument(
            "--dry-run", action="store_true", default=False, help="仅打印需要增强的文章，不写数据库"
        )
        parser.add_argument(
            "--min-id", type=int, default=0, help="只处理 id >= 此值的文章（用于断点续传）"
        )

    def handle(self, *args, **options):
        # 延迟导入（确保 Django 环境已初始化）
        sys.path.insert(
            0,
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            ),
        )

        from news.models import TechNews
        from news_content_utils import needs_content_enrichment
        from content_enricher import get_enriched_content

        limit = options["limit"]
        cat_key = options["category"].lower()
        use_crawl4ai = options["use_crawl4ai"]
        workers = max(1, min(options["workers"], 8))
        dry_run = options["dry_run"]
        min_id = options["min_id"]

        # 确定要处理的分类集合
        cat_filter = CATEGORY_MAP.get(cat_key)
        if cat_filter is None:
            # 把用户传入的单个中文分类当作精确过滤
            cat_filter = {options["category"]}
            self.stdout.write(f"使用自定义分类过滤：{cat_filter}")

        self.stdout.write(
            f"\n{'[DRY-RUN] ' if dry_run else ''}开始 content 增强任务\n"
            f"  分类: {cat_key}  限制: {limit}  workers: {workers}  "
            f"crawl4ai: {use_crawl4ai}\n"
            f"{'─' * 60}"
        )

        # 查询需要增强的文章
        qs = TechNews.objects.filter(
            id__gte=min_id,
            category__in=list(cat_filter),
        ).order_by("id")

        # 内存中过滤需要增强的条目（避免在 SQL 层做复杂文本判断）
        to_enrich = []
        checked = 0
        for article in qs.iterator():
            checked += 1
            if needs_content_enrichment(article.content):
                to_enrich.append(article)
                if len(to_enrich) >= limit:
                    break

        self.stdout.write(f"扫描 {checked} 条  →  需要增强: {len(to_enrich)} 篇")

        if not to_enrich:
            self.stdout.write(self.style.SUCCESS("所有文章 content 已充足，无需增强。"))
            return

        if dry_run:
            for a in to_enrich:
                self.stdout.write(
                    f"  [{a.id}] [{a.category}] {a.title[:60]}  (content={len(a.content or '')}字)"
                )
            self.stdout.write(
                self.style.WARNING(f"\n[DRY-RUN] 共 {len(to_enrich)} 篇待处理，未写库。")
            )
            return

        # ─── 并发增强 ────────────────────────────────────────────────────────
        success = failed = skipped = 0
        start_ts = time.time()

        def _enrich_one(article):
            """单篇增强并更新数据库，返回 (True/False, article_id)"""
            try:
                enriched = get_enriched_content(
                    article.url,
                    title=article.title,
                    category=article.category,
                    use_crawl4ai=use_crawl4ai,
                    timeout=10,
                )
                if enriched and len(enriched) > 30:
                    TechNews.objects.filter(id=article.id).update(content=enriched)
                    return True, article.id, enriched[:60]
                return False, article.id, ""
            except Exception as exc:
                logger.warning(f"enrich_one [{article.id}] error: {exc}")
                return False, article.id, str(exc)[:60]

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_enrich_one, a): a for a in to_enrich}
            for fut in as_completed(futures):
                ok, aid, snippet = fut.result()
                art = futures[fut]
                if ok:
                    success += 1
                    self.stdout.write(
                        f"  ✓ [{aid}] [{art.category}] {art.title[:45]}  →  {snippet}..."
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        f"  ✗ [{aid}] {art.title[:45]}"
                        + (f"  ({snippet})" if snippet else "")
                    )

        elapsed = time.time() - start_ts
        self.stdout.write(
            f"\n{'─' * 60}\n"
            f"完成  成功: {success}  失败: {failed}  "
            f"耗时: {elapsed:.1f}s\n"
        )
        if success:
            self.stdout.write(self.style.SUCCESS(f"✅ 共更新 {success} 篇文章 content"))
        if failed:
            self.stdout.write(self.style.WARNING(f"⚠️  {failed} 篇增强失败（内容不变）"))
