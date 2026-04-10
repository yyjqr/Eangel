from django.shortcuts import render, redirect
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from .models import (
    TechNews,
    UserComment,
    DailyStats,
    UserIPLog,
    HotProduct,
    FeaturedSelection,
    OriginalArticle,
)
from django.contrib import messages
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import os
from news_content_utils import build_article_content, needs_content_enrichment

# 中国大陆无法直接访问的域名列表
BLOCKED_DOMAINS = [
    "google.com",
    "news.google.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "foxnews.com",
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "economist.com",
    "reuters.com",
    "bbc.com",
    "cnn.com",
    "yahoo.com",
    "www.engadget.com",
]

MILITARY_CATEGORY_ALIASES = {"军事", "国际军事", "防务动向", "海军装备", "国内军事"}
PRODUCT_CATEGORIES = [
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
AEROSPACE_KEYWORDS = [
    "航空航天",
    "aerospace",
    "space",
    "航天",
    "卫星",
    "satellite",
    "nasa",
    "spacex",
    "rocket",
    "火箭",
    "spacecraft",
    "space station",
    "orbit",
    "轨道",
    "lunar",
    "moon mission",
]
ECONOMY_CATEGORY_ALIASES = {
    "宏观经济",
    "经济综合",
    "经济评论",
    "股市投资",
    "金融科技",
    "贸易与供应链",
    "企业动态",
    "产业经济",
}
FEATURED_PRIMARY_LAYOUT = [("科技", 4), ("经济", 2), ("军事", 2)]
FEATURED_FALLBACK_LAYOUT = [("科技", 4), ("军事", 4)]
FEATURED_MODE_LABELS = {
    "tech4-econ2-mil2": "4篇科技 · 2篇经济 · 2篇军事",
    "tech4-mil4": "4篇科技 · 4篇军事",
    "fallback-history": "最近历史精选",
}


def normalize_category_label(category):
    """标准化分类标签，用于筛选与展示。"""
    if category in MILITARY_CATEGORY_ALIASES or category == "军工与航天":
        return "军事"
    return category


def normalize_news_category(news_item):
    """兼容旧数据分类：军事子类统一归并，航空航天保持独立。"""
    raw_category = getattr(news_item, "category", "") or ""
    if raw_category in MILITARY_CATEGORY_ALIASES:
        return "军事"
    if raw_category == "航空航天":
        return "航空航天"
    if raw_category == "军工与航天":
        content_text = f"{getattr(news_item, 'title', '')} {getattr(news_item, 'key_word', '')}".lower()
        if any(keyword in content_text for keyword in AEROSPACE_KEYWORDS):
            return "航空航天"
        return "军事"
    return raw_category


def apply_normalized_category(news_list):
    for news_item in news_list:
        news_item.category = normalize_news_category(news_item)
    return news_list


def parse_news_publish_date(news_item):
    today = datetime.now().date()
    try:
        publish_time = getattr(news_item, "publish_time", "") or ""
        publish_time_str = str(publish_time)
        if not publish_time_str:
            return today - timedelta(days=1)
        if len(publish_time_str) >= 10:
            return datetime.strptime(publish_time_str[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return today - timedelta(days=1)


def get_featured_bucket(news_item):
    normalized_category = normalize_news_category(news_item)
    if normalized_category in {"军事", "航空航天"}:
        return "军事"
    if normalized_category in ECONOMY_CATEGORY_ALIASES or "经济" in normalized_category:
        return "经济"
    return "科技"


def compute_unified_feature_score(news_item, rate_min, rate_max, today):
    rate_span = rate_max - rate_min
    if rate_span <= 0:
        rate_score = 1.0
    else:
        rate_score = (float(news_item.rate) - rate_min) / rate_span

    publish_date = parse_news_publish_date(news_item)
    age_days = max((today - publish_date).days, 0)
    freshness_score = max(0.0, 1 - min(age_days, 30) / 30)
    content_score = (
        0.08 if not needs_content_enrichment(getattr(news_item, "content", "")) else 0.0
    )
    return round(rate_score * 0.72 + freshness_score * 0.23 + content_score, 4)


def ensure_news_content(news_item):
    current_content = getattr(news_item, "content", "") or ""
    display_summary = build_article_content(
        title=getattr(news_item, "title", ""),
        category=get_featured_bucket(news_item),
        source=getattr(news_item, "author", ""),
        summary=current_content,
        tags=getattr(news_item, "key_word", ""),
        keywords=getattr(news_item, "key_word", ""),
    )
    if needs_content_enrichment(current_content):
        TechNews.objects.filter(id=news_item.id).update(content=display_summary)
        news_item.content = display_summary
    news_item.featured_summary = display_summary
    return news_item


def pick_featured_news(candidate_news):
    today = datetime.now().date()
    bucketed_news = defaultdict(list)
    title_seen = set()

    for news_item in candidate_news:
        if not getattr(news_item, "image_url", "") or is_blocked_in_china(
            news_item.url
        ):
            continue
        news_item.category = normalize_news_category(news_item)
        if news_item.title in title_seen:
            continue
        title_seen.add(news_item.title)
        news_item.featured_bucket = get_featured_bucket(news_item)
        bucketed_news[news_item.featured_bucket].append(news_item)

    for bucket, items in bucketed_news.items():
        if not items:
            continue
        rate_min = min(float(item.rate) for item in items)
        rate_max = max(float(item.rate) for item in items)
        for item in items:
            item.selection_score = compute_unified_feature_score(
                item, rate_min, rate_max, today
            )
        items.sort(
            key=lambda item: (item.selection_score, item.rate, item.id), reverse=True
        )

    layout = (
        FEATURED_PRIMARY_LAYOUT
        if len(bucketed_news["经济"]) >= 2
        else FEATURED_FALLBACK_LAYOUT
    )
    selected_news = []
    selected_ids = set()
    selected_titles = set()
    bucket_counts = defaultdict(int)

    for bucket, limit in layout:
        for news_item in bucketed_news.get(bucket, []):
            if news_item.id in selected_ids or news_item.title in selected_titles:
                continue
            ensure_news_content(news_item)
            selected_news.append(news_item)
            selected_ids.add(news_item.id)
            selected_titles.add(news_item.title)
            bucket_counts[bucket] += 1
            if bucket_counts[bucket] >= limit:
                break

    remaining_candidates = []
    for items in bucketed_news.values():
        for news_item in items:
            if (
                news_item.id not in selected_ids
                and news_item.title not in selected_titles
            ):
                remaining_candidates.append(news_item)

    remaining_candidates.sort(
        key=lambda item: (item.selection_score, item.rate, item.id), reverse=True
    )
    for news_item in remaining_candidates:
        if len(selected_news) >= 8:
            break
        ensure_news_content(news_item)
        selected_news.append(news_item)
        selected_ids.add(news_item.id)
        selected_titles.add(news_item.title)

    mode_key = "tech4-econ2-mil2" if layout == FEATURED_PRIMARY_LAYOUT else "tech4-mil4"
    return selected_news[:8], mode_key


def save_featured_snapshot(featured_news, mode_key):
    if not featured_news:
        return
    today = datetime.now().date()
    if FeaturedSelection.objects.filter(selection_date=today).exists():
        return

    snapshot_rows = []
    for index, news_item in enumerate(featured_news, start=1):
        snapshot_rows.append(
            FeaturedSelection(
                selection_date=today,
                slot_order=index,
                selection_mode=mode_key,
                news_id=getattr(news_item, "id", None),
                title=getattr(news_item, "title", ""),
                url=getattr(news_item, "url", ""),
                category=getattr(
                    news_item, "featured_bucket", get_featured_bucket(news_item)
                ),
                rate=float(getattr(news_item, "rate", 0) or 0),
                selection_score=float(getattr(news_item, "selection_score", 0) or 0),
                image_url=getattr(news_item, "image_url", ""),
                content=getattr(news_item, "featured_summary", "")
                or getattr(news_item, "content", ""),
            )
        )

    with transaction.atomic():
        FeaturedSelection.objects.bulk_create(snapshot_rows, ignore_conflicts=True)


def load_featured_history(current_featured, candidate_news, limit_groups=4):
    today = datetime.now().date()
    rows = list(
        FeaturedSelection.objects.exclude(selection_date=today).order_by(
            "-selection_date", "slot_order"
        )[: limit_groups * 8]
    )

    history_groups = []
    current_group = None
    current_date = None
    for row in rows:
        if row.selection_date != current_date:
            if len(history_groups) >= limit_groups:
                break
            current_date = row.selection_date
            current_group = {
                "label": str(row.selection_date),
                "mode_label": FEATURED_MODE_LABELS.get(
                    row.selection_mode, FEATURED_MODE_LABELS["fallback-history"]
                ),
                "items": [],
            }
            history_groups.append(current_group)
        row.featured_summary = build_article_content(
            title=row.title,
            category=row.category,
            source="",
            summary=row.content,
            keywords=row.category,
        )
        current_group["items"].append(row)

    if history_groups:
        return history_groups

    selected_ids = {item.id for item in current_featured}
    fallback_items = []
    for news_item in candidate_news:
        if getattr(news_item, "id", None) in selected_ids:
            continue
        news_item.category = normalize_news_category(news_item)
        news_item.featured_bucket = get_featured_bucket(news_item)
        ensure_news_content(news_item)
        fallback_items.append(news_item)
        if len(fallback_items) >= 8:
            break

    if not fallback_items:
        return []

    return [
        {
            "label": "最近归档",
            "mode_label": FEATURED_MODE_LABELS["fallback-history"],
            "items": fallback_items,
        }
    ]


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def record_visit(request):
    """记录访问统计"""
    ip = get_client_ip(request)
    today = datetime.now().date()

    # 获取或创建今日统计
    daily_stats, created = DailyStats.objects.get_or_create(date=today)

    # 增加页面浏览量 (PV)
    daily_stats.total_views += 1

    # 检查IP是否已记录 (UV)
    if not UserIPLog.objects.filter(ip_address=ip, visit_date=today).exists():
        UserIPLog.objects.create(ip_address=ip)
        daily_stats.unique_visitors += 1

    daily_stats.save()


def is_blocked_in_china(url):
    """判断URL是否在中国大陆被屏蔽"""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in BLOCKED_DOMAINS)


def news_list(request):
    # 记录访问
    record_visit(request)

    # 获取参数
    query = request.GET.get("q", "")
    category = normalize_category_label(request.GET.get("category", ""))
    show_all = request.GET.get("show_all", "") == "true"

    # 获取总访问统计
    total_stats = DailyStats.objects.aggregate(
        total_uv=Sum("unique_visitors"), total_pv=Sum("total_views")
    )
    total_visitors = total_stats["total_uv"] or 0
    total_views = total_stats["total_pv"] or 0

    # 基础查询
    news_queryset = TechNews.objects.all()

    # 搜索过滤
    if query:
        news_queryset = news_queryset.filter(
            Q(title__icontains=query) | Q(key_word__icontains=query)
        )

    # 获取所有新闻（用于分类和排序）
    all_news = list(news_queryset.order_by("-id")[:400])
    apply_normalized_category(all_news)
    categories = sorted({n.category for n in all_news if n.category})

    # 分类过滤（标准化后进行，兼容旧军事分类）
    if category:
        all_news = [n for n in all_news if n.category == category]

    # 智能排序：当天文章按权重，之前文章按时间+权重
    today = datetime.now().date()
    today_news = []
    old_news = []

    for news_item in all_news:
        try:
            pub_date = parse_news_publish_date(news_item)

            if pub_date >= today:
                today_news.append(news_item)
            else:
                old_news.append(news_item)
        except Exception as e:
            old_news.append(news_item)

    # 当天文章：按权重降序
    today_news.sort(key=lambda x: x.rate, reverse=True)

    # 之前文章：先按时间降序，再按权重降序
    old_news.sort(key=lambda x: (x.id, x.rate), reverse=True)

    # 合并：当天文章在前，之前文章在后
    sorted_news = today_news + old_news

    # 分离境内可访问和境外被屏蔽的新闻
    accessible_news = []
    blocked_news = []

    for news_item in sorted_news:
        if is_blocked_in_china(news_item.url):
            blocked_news.append(news_item)
        else:
            accessible_news.append(news_item)

    # 限制显示数量
    if not show_all:
        accessible_news = accessible_news[:30]  # 主页只显示30条
    else:
        accessible_news = accessible_news[:100]  # 全部显示100条

    blocked_news = blocked_news[:5]  # 境外新闻只显示5条

    featured_candidates = list(
        TechNews.objects.filter(image_url__isnull=False)
        .exclude(image_url="")
        .order_by("-id", "-rate")[:240]
    )
    featured_news, featured_mode = pick_featured_news(featured_candidates)
    save_featured_snapshot(featured_news, featured_mode)
    featured_history = load_featured_history(featured_news, featured_candidates)

    # 1. 统计数据
    stats = {
        "total_count": TechNews.objects.count(),
        "avg_rate": TechNews.objects.aggregate(Avg("rate"))["rate__avg"] or 0,
        "category_counts": [
            {"category": cat, "count": count}
            for cat, count in Counter(
                n.category for n in sorted_news if n.category
            ).most_common()
        ],
        "accessible_count": len(accessible_news),
        "blocked_count": len(blocked_news),
        "today_count": len(today_news),
    }

    # 2. 关键词云
    all_titles = " ".join([n.title for n in accessible_news[:50]])
    words = re.findall(r"\w+", all_titles.lower())
    stop_words = {
        "the",
        "a",
        "in",
        "on",
        "at",
        "for",
        "to",
        "of",
        "and",
        "is",
        "with",
        "it",
        "as",
        "from",
        "this",
        "that",
        "after",
        "down",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "but",
        "if",
        "or",
        "about",
        "into",
        "through",
        "before",
        "above",
        "below",
        "which",
        "who",
        "are",
        "all",
        "by",
        "an",
        "not",
        "so",
        "we",
        "they",
        "you",
        "he",
        "she",
    }
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
    word_cloud = Counter(keywords).most_common(20)

    # 4. 获取最新的评论
    recent_comments = UserComment.objects.filter(is_approved=True).order_by(
        "-created_at"
    )[:10]

    # 5. 读取趋势分析数据
    trend_data = {}
    trend_data_json = "{}"
    try:
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "trend_data.json"
        )
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                trend_data = json.load(f)
                trend_data_json = json.dumps(trend_data, ensure_ascii=False)
    except Exception as e:
        print(f"Error loading trend data: {e}")

    # 6. 提取特色栏目数据
    # 科学与数学 (包含趣说数学)：总计展示4条，权重最高优先
    science_math_news = [
        n
        for n in sorted_news
        if n.category in ["趣说数学", "科学与数学"] and not is_blocked_in_china(n.url)
    ][:4]
    # 人物
    people_news = [
        n for n in sorted_news if n.category == "人物" and not is_blocked_in_china(n.url)
    ][:5]

    # 热点产品：从机器人、智能硬件、汽车、VR/AR、军工等类别中选择权重最高的
    # 优化条件：1) 权重>2, 2) 最近14天的新闻, 3) 排除经济类
    product_categories = PRODUCT_CATEGORIES
    recent_14days = datetime.now().date() - timedelta(days=14)

    # 从数据库直接查询最新的高权重产品新闻
    product_news_query = (
        TechNews.objects.filter(category__in=product_categories, rate__gt=2.0)
        .exclude(category__icontains="经济")
        .order_by("-rate", "-id")[:50]
    )  # 先取50条

    # 过滤：1) 被屏蔽的URL, 2) 旧新闻，并限制为5条
    product_news = []
    for news in product_news_query:
        if not is_blocked_in_china(news.url):
            # 检查发布时间，只保留最近14天的新闻
            is_recent = False
            try:
                if hasattr(news, "publish_time") and news.publish_time:
                    pub_time_str = str(news.publish_time)
                    if len(pub_time_str) >= 10:
                        pub_date = datetime.strptime(
                            pub_time_str[:10], "%Y-%m-%d"
                        ).date()
                        # 只保留最近14天的新闻
                        if pub_date >= recent_14days:
                            is_recent = True
                    else:
                        # 无法解析时间格式，检查是否是最近创建的（通过ID判断）
                        # 假设ID越大越新
                        latest_id = TechNews.objects.order_by("-id").first().id
                        if news.id >= latest_id - 200:  # 最近200条记录内
                            is_recent = True
                else:
                    # 无发布时间，通过ID判断
                    latest_id = TechNews.objects.order_by("-id").first().id
                    if news.id >= latest_id - 200:
                        is_recent = True
            except Exception as e:
                # 解析失败，通过ID判断
                try:
                    latest_id = TechNews.objects.order_by("-id").first().id
                    if news.id >= latest_id - 200:
                        is_recent = True
                except:
                    pass

            if is_recent:
                news.category = normalize_news_category(news)
                product_news.append(news)

            if len(product_news) >= 5:
                break

    # 如果product_news不足5条，从hot_products补充
    if len(product_news) < 5:
        # 获取最新的热点产品排名（从HotProduct表）
        recent_date = datetime.now().date() - timedelta(days=2)  # 最近2天的数据
        hot_products = HotProduct.objects.filter(
            period_type="weekly", period_start__gte=recent_date
        ).order_by("rank")[:5]
    else:
        # 如果已有足够的product_news，也获取hot_products作为补充信息
        recent_date = datetime.now().date() - timedelta(days=2)
        hot_products = HotProduct.objects.filter(
            period_type="weekly", period_start__gte=recent_date
        ).order_by("rank")[:5]

    for hot_product in hot_products:
        hot_product.category = normalize_category_label(hot_product.category)

    # 原创专栏
    original_articles = list(OriginalArticle.objects.filter(is_published=True)[:10])

    context = {
        "accessible_news": accessible_news,
        "blocked_news": blocked_news,
        "featured_news": featured_news,
        "featured_mode_label": FEATURED_MODE_LABELS.get(featured_mode, ""),
        "featured_history": featured_history,
        "stats": stats,
        "trend_data": trend_data,
        "trend_data_json": trend_data_json,
        "word_cloud": word_cloud,
        "categories": categories,
        "current_category": category,
        "query": query,
        "recent_comments": recent_comments,
        "show_all": show_all,
        "total_visitors": total_visitors,
        "total_views": total_views,
        "today_news_ids": {n.id for n in today_news},
        "science_math_news": science_math_news,
        "people_news": people_news,
        "product_news": product_news,
        "hot_products": hot_products,
        "original_articles": original_articles,
    }

    return render(request, "news/index.html", context)


def submit_comment(request):
    """提交用户评论"""
    if request.method == "POST":
        username = request.POST.get("username", "匿名").strip() or "匿名"
        email = request.POST.get("email", "").strip()
        comment = request.POST.get("comment", "").strip()

        if comment:
            try:
                UserComment.objects.create(
                    username=username, email=email, comment=comment
                )
                messages.success(request, "感谢您的反馈！")
            except Exception as e:
                messages.error(request, f"提交失败：{str(e)}")
        else:
            messages.error(request, "评论内容不能为空！")

    return redirect("news_list")


# ─────────────────────────────────────────────
# AI 全网搜索（threading 异步，无需 Celery）
# ─────────────────────────────────────────────
import threading
import asyncio
from urllib.parse import urlparse
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

# 各分类默认抓取入口（支持多个，并发抓取后合并）
_AI_SEARCH_MULTI_URLS = {
    "tech": ["https://36kr.com", "https://www.ithome.com", "https://huxiu.com"],
    "ai": [
        "https://lmarena.ai/leaderboard",
        "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
        "https://www.aibase.com",
        "https://www.jiqizhixin.com",
    ],
    "economy": ["https://www.yicai.com", "https://caixin.com"],
    "product": ["https://www.ithome.com", "https://www.smzdm.com"],
    "military": [
        "https://www.guancha.cn/military-affairs",
        "https://www.81.cn",
        "https://www.defensenews.com",
        "https://www.breakingdefense.com",
    ],
    "design": ["https://www.zcool.com.cn", "https://www.dezeen.com"],
    "science": ["https://phys.org", "https://www.sciencedaily.com"],
    "all": ["https://36kr.com", "https://www.guancha.cn"],
}

# SSRF 防护：仅允许白名单域名（防止用户提交内网地址）
_ALLOWED_CRAWL_DOMAINS = {
    # 科技
    "36kr.com",
    "ithome.com",
    "huxiu.com",
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "venturebeat.com",
    # 人工智能
    "arena.ai",
    "lmarena.ai",
    "huggingface.co",
    "aibase.com",
    "jiqizhixin.com",
    "aitopics.org",
    "syncedreview.com",
    # 经济
    "wallstreetcn.com",
    "yicai.com",
    "caixin.com",
    "bloomberg.com",
    "reuters.com",
    "ft.com",
    "wsj.com",
    # 产品
    "smzdm.com",
    "zhuanlan.zhihu.com",
    "sspai.com",
    # 军事
    "defensenews.com",
    "twz.com",
    "breakingdefense.com",
    "guancha.cn",
    "81.cn",
    # 设计
    "zcool.com.cn",
    "dezeen.com",
    "red-dot.org",
    "if-design.org",
    # 科学
    "phys.org",
    "sciencedaily.com",
    "nature.com",
    # 通用
    "xinhuanet.com",
    "people.com.cn",
    "cnbc.com",
}


def _is_safe_crawl_url(url: str) -> bool:
    """SSRF 防护：只允许白名单域名"""
    if not url:
        return True
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return any(host == d or host.endswith("." + d) for d in _ALLOWED_CRAWL_DOMAINS)
    except Exception:
        return False


import re as _re

# 噪音行正则：导航链接、占位块字符、登录注册等
_NOISE_LINE_RE = _re.compile(
    r"^\s*\!\[\]\(.*?\)\s*$"  # 纯空图片 ![]()
    r"|^\s*\[\]\(.*?\)\s*$"  # 纯空链接 [](url)
    r"|[\u2580-\u259f\u25a0-\u25ff]{3,}"  # 块状占位符 ▅▅▅▅
    r"|\s*(登录\s*/\s*注册|加载更多|返回顶部|下载\s*APP|APP下载|暂无数据|查看更多)"
)
# 纯导航链接行：* [文字](url) 或 - [文字](url)，文字很短
_NAV_LINK_RE = _re.compile(r"^\s*[\*\-]\s*\[[^\]]{1,40}\]\(https?://[^\)]+\)\s*$")


def _filter_markdown(md: str, query: str) -> str:
    """
    清理爬取的 Markdown：
    1. 去掉导航/噪音行
    2. 压缩连续空行
    3. 优先返回含关键词的段落（上下文各保留1段）
    """
    lines = md.split("\n")
    q_words = [w.lower() for w in query.split() if len(w) > 1]

    cleaned = []
    for line in lines:
        s = line.strip()
        if not s:
            cleaned.append("")
            continue
        if _NOISE_LINE_RE.search(s):
            continue
        if _NAV_LINK_RE.match(s):
            continue
        # 丢弃过短非标题行
        if len(s) < 6 and not s.startswith("#"):
            continue
        cleaned.append(line)

    # 压缩连续空行
    merged, blanks = [], 0
    for l in cleaned:
        if l.strip() == "":
            blanks += 1
            if blanks <= 1:
                merged.append(l)
        else:
            blanks = 0
            merged.append(l)

    full_text = "\n".join(merged).strip()

    if not q_words:
        return full_text[:8000]

    # 按双换行切段落，优先返回含关键词的段落
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    relevant, others = [], []
    for p in paragraphs:
        if any(w in p.lower() for w in q_words):
            relevant.append(p)
        else:
            others.append(p)

    if relevant:
        output = "\n\n".join(relevant)
        # 若相关段落很少，补充前几段通用内容
        if len(output) < 500 and others:
            output += "\n\n---\n" + "\n\n".join(others[:3])
        return output[:8000]

    # 没有精确匹配段落，返回清理后全文头部
    return full_text[:8000]


def _run_crawl(task_id: int):
    """后台线程：并发抓取多个站源，合并过滤后写回 DB"""
    from .models import AiSearchTask

    def _save(task, **kw):
        for k, v in kw.items():
            setattr(task, k, v)
        task.save(update_fields=list(kw.keys()) + ["updated_at"])

    try:
        task = AiSearchTask.objects.get(id=task_id)
        _save(task, status="running")

        query = task.query
        # 用户指定了 URL → 单源；否则按分类取多源
        if task.target_url:
            urls = [task.target_url]
        else:
            urls = _AI_SEARCH_MULTI_URLS.get(
                task.category, _AI_SEARCH_MULTI_URLS["all"]
            )

        async def _crawl_one(crawler, url: str, run_cfg):
            """抓单个 URL，失败返回空字符串，不抛异常"""
            try:
                result = await crawler.arun(url=url, config=run_cfg)
                if result.success:
                    return _filter_markdown(result.markdown or "", query)
            except Exception:
                pass
            return ""

        async def _crawl_all():
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from crawl4ai.cache_context import CacheMode

            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                enable_stealth=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
                viewport_width=1280,
                viewport_height=800,
            )

            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=8,
                # domcontentloaded：页面 DOM 就绪即返回，避免等待广告/tracker 超时
                wait_until="domcontentloaded",
                page_timeout=45000,
                magic=True,
                simulate_user=True,
                override_navigator=True,
                remove_overlay_elements=True,
                remove_consent_popups=True,
                excluded_tags=[
                    "nav",
                    "header",
                    "footer",
                    "aside",
                    "script",
                    "style",
                    "noscript",
                    "form",
                ],
                excluded_selector=(
                    ".nav, .navbar, .menu, .sidebar, .footer, .header, "
                    ".login, .register, .cookie-notice, .advertisement, "
                    '.ad, [class*="banner"], [class*="popup"], '
                    '[id*="cookie"], [class*="cookie"]'
                ),
                wait_for_images=False,
                verbose=False,
            )

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                results = await asyncio.gather(
                    *[_crawl_one(crawler, u, run_cfg) for u in urls],
                    return_exceptions=True,
                )

            # 合并各站结果，每段加来源标记
            parts = []
            for u, r in zip(urls, results):
                if isinstance(r, str) and r.strip():
                    host = urlparse(u).netloc.replace("www.", "")
                    parts.append(f"### 来源：{host}\n\n{r.strip()}")

            if not parts:
                return "", "所有站点均抓取失败，请稍后重试或更换目标网址"
            return ("\n\n---\n\n".join(parts))[:10000], ""

        content, err = asyncio.run(_crawl_all())
        if err:
            _save(task, status="error", error_msg=err[:500])
        else:
            _save(task, status="done", result_md=content)
    except Exception as e:
        try:
            from .models import AiSearchTask

            AiSearchTask.objects.filter(id=task_id).update(
                status="error", error_msg=str(e)[:500]
            )
        except Exception:
            pass


@csrf_exempt
@require_POST
def ai_search_submit(request):
    """POST JSON: {query, url?, category?} → {task_id, status}"""
    from .models import AiSearchTask

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    query = str(data.get("query", "")).strip()[:200]
    target_url = str(data.get("url", "")).strip()[:500]
    category = str(data.get("category", "all"))[:20]

    if not query:
        return JsonResponse({"error": "请输入搜索关键词"}, status=400)
    if target_url and not _is_safe_crawl_url(target_url):
        return JsonResponse({"error": "不支持的目标域名，请从白名单中选择"}, status=400)

    task = AiSearchTask.objects.create(
        query=query, target_url=target_url, category=category
    )
    threading.Thread(target=_run_crawl, args=(task.id,), daemon=True).start()
    return JsonResponse({"task_id": task.id, "status": "pending"})


@require_GET
def ai_search_status(request, task_id):
    """GET /ai-search/status/<id>/ → {status, result_md, error_msg}"""
    from .models import AiSearchTask

    try:
        task = AiSearchTask.objects.get(id=int(task_id))
    except (AiSearchTask.DoesNotExist, ValueError):
        return JsonResponse({"error": "任务不存在"}, status=404)
    return JsonResponse(
        {
            "task_id": task.id,
            "status": task.status,
            "result_md": task.result_md if task.status == "done" else "",
            "error_msg": task.error_msg,
            "query": task.query,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
