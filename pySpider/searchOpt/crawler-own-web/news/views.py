from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from .models import TechNews, UserComment, DailyStats, UserIPLog, HotProduct, FeaturedSelection, OriginalArticle
from django.contrib import messages
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import os
from news_content_utils import build_article_content, needs_content_enrichment

# 中国大陆无法直接访问的域名列表
BLOCKED_DOMAINS = [
    'google.com', 'news.google.com', 'youtube.com', 'facebook.com',
    'twitter.com', 'instagram.com', 'foxnews.com', 'nytimes.com',
    'wsj.com', 'ft.com', 'bloomberg.com', 'economist.com',
    'reuters.com', 'bbc.com', 'cnn.com','yahoo.com', 'www.engadget.com'
]

MILITARY_CATEGORY_ALIASES = {'军事', '国际军事', '防务动向', '海军装备', '国内军事'}
PRODUCT_CATEGORIES = ['机器人', '智能硬件', '汽车与自动驾驶', 'VR/AR/XR', '航空航天', '产品发布', '芯片与半导体']
AEROSPACE_KEYWORDS = [
    '航空航天', 'aerospace', 'space', '航天', '卫星', 'satellite', 'nasa', 'spacex',
    'rocket', '火箭', 'spacecraft', 'space station', 'orbit', '轨道', 'lunar', 'moon mission'
]
ECONOMY_CATEGORY_ALIASES = {'宏观经济', '经济综合', '经济评论', '股市投资', '金融科技', '贸易与供应链', '企业动态', '产业经济'}
EXCLUDED_CATEGORIES = MILITARY_CATEGORY_ALIASES | {'军工与航天'} | ECONOMY_CATEGORY_ALIASES
FEATURED_PRIMARY_LAYOUT = [('科技', 8)]
FEATURED_FALLBACK_LAYOUT = [('科技', 8)]
FEATURED_MODE_LABELS = {
    'tech4-econ2-mil2': '科技精选',
    'tech4-mil4': '科技精选',
    'fallback-history': '最近归档精选',
}

logger = logging.getLogger(__name__)


def normalize_category_label(category):
    """标准化分类标签，用于筛选与展示。"""
    if category in MILITARY_CATEGORY_ALIASES or category == '军工与航天':
        return '军事'
    return category


def normalize_news_category(news_item):
    """兼容旧数据分类：军事子类统一归并，航空航天保持独立。"""
    raw_category = getattr(news_item, 'category', '') or ''
    if raw_category in MILITARY_CATEGORY_ALIASES:
        return '军事'
    if raw_category == '航空航天':
        return '航空航天'
    if raw_category == '军工与航天':
        content_text = f"{getattr(news_item, 'title', '')} {getattr(news_item, 'key_word', '')}".lower()
        if any(keyword in content_text for keyword in AEROSPACE_KEYWORDS):
            return '航空航天'
        return '军事'
    return raw_category


def apply_normalized_category(news_list):
    for news_item in news_list:
        news_item.category = normalize_news_category(news_item)
    return news_list


def parse_news_publish_date(news_item):
    today = datetime.now().date()
    try:
        publish_time = getattr(news_item, 'publish_time', '') or ''
        publish_time_str = str(publish_time)
        if not publish_time_str:
            return today - timedelta(days=1)
        if len(publish_time_str) >= 10:
            return datetime.strptime(publish_time_str[:10], '%Y-%m-%d').date()
    except Exception:
        pass
    return today - timedelta(days=1)


def get_featured_bucket(news_item):
    normalized_category = normalize_news_category(news_item)
    if normalized_category in {'军事', '航空航天'}:
        return '军事'
    if normalized_category in ECONOMY_CATEGORY_ALIASES or '经济' in normalized_category:
        return '经济'
    return '科技'


def compute_unified_feature_score(news_item, rate_min, rate_max, today):
    rate_span = rate_max - rate_min
    if rate_span <= 0:
        rate_score = 1.0
    else:
        rate_score = (float(news_item.rate) - rate_min) / rate_span

    publish_date = parse_news_publish_date(news_item)
    age_days = max((today - publish_date).days, 0)
    freshness_score = max(0.0, 1 - min(age_days, 30) / 30)
    content_score = 0.08 if not needs_content_enrichment(getattr(news_item, 'content', '')) else 0.0
    return round(rate_score * 0.72 + freshness_score * 0.23 + content_score, 4)


def ensure_news_content(news_item):
    current_content = getattr(news_item, 'content', '') or ''
    display_summary = build_article_content(
        title=getattr(news_item, 'title', ''),
        category=get_featured_bucket(news_item),
        source=getattr(news_item, 'author', ''),
        summary=current_content,
        tags=getattr(news_item, 'key_word', ''),
        keywords=getattr(news_item, 'key_word', ''),
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
        if not getattr(news_item, 'image_url', '') or is_blocked_in_china(news_item.url):
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
            item.selection_score = compute_unified_feature_score(item, rate_min, rate_max, today)
        items.sort(key=lambda item: (item.selection_score, item.rate, item.id), reverse=True)

    layout = FEATURED_PRIMARY_LAYOUT if len(bucketed_news['经济']) >= 2 else FEATURED_FALLBACK_LAYOUT
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
            if news_item.id not in selected_ids and news_item.title not in selected_titles:
                remaining_candidates.append(news_item)

    remaining_candidates.sort(key=lambda item: (item.selection_score, item.rate, item.id), reverse=True)
    for news_item in remaining_candidates:
        if len(selected_news) >= 8:
            break
        ensure_news_content(news_item)
        selected_news.append(news_item)
        selected_ids.add(news_item.id)
        selected_titles.add(news_item.title)

    mode_key = 'tech4-econ2-mil2' if layout == FEATURED_PRIMARY_LAYOUT else 'tech4-mil4'
    return selected_news[:8], mode_key


def save_featured_snapshot(featured_news, mode_key):
    if not featured_news:
        return
    today = datetime.now().date()
    if FeaturedSelection.objects.filter(selection_date=today).exists():
        return

    snapshot_rows = []
    for index, news_item in enumerate(featured_news, start=1):
        snapshot_rows.append(FeaturedSelection(
            selection_date=today,
            slot_order=index,
            selection_mode=mode_key,
            news_id=getattr(news_item, 'id', None),
            title=getattr(news_item, 'title', ''),
            url=getattr(news_item, 'url', ''),
            category=getattr(news_item, 'featured_bucket', get_featured_bucket(news_item)),
            rate=float(getattr(news_item, 'rate', 0) or 0),
            selection_score=float(getattr(news_item, 'selection_score', 0) or 0),
            image_url=getattr(news_item, 'image_url', ''),
            content=getattr(news_item, 'featured_summary', '') or getattr(news_item, 'content', ''),
        ))

    with transaction.atomic():
        FeaturedSelection.objects.bulk_create(snapshot_rows, ignore_conflicts=True)


def load_featured_history(current_featured, candidate_news, limit_groups=4):
    today = datetime.now().date()
    rows = list(
        FeaturedSelection.objects.exclude(selection_date=today)
        .order_by('-selection_date', 'slot_order')[:limit_groups * 8]
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
                'label': str(row.selection_date),
                'mode_label': FEATURED_MODE_LABELS.get(row.selection_mode, FEATURED_MODE_LABELS['fallback-history']),
                'items': [],
            }
            history_groups.append(current_group)
        row.featured_summary = build_article_content(
            title=row.title,
            category=row.category,
            source='',
            summary=row.content,
            keywords=row.category,
        )
        current_group['items'].append(row)

    if history_groups:
        return history_groups

    selected_ids = {item.id for item in current_featured}
    fallback_items = []
    for news_item in candidate_news:
        if getattr(news_item, 'id', None) in selected_ids:
            continue
        news_item.category = normalize_news_category(news_item)
        news_item.featured_bucket = get_featured_bucket(news_item)
        ensure_news_content(news_item)
        fallback_items.append(news_item)
        if len(fallback_items) >= 8:
            break

    if not fallback_items:
        return []

    return [{
        'label': '最近归档',
        'mode_label': FEATURED_MODE_LABELS['fallback-history'],
        'items': fallback_items,
    }]

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
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
    query = request.GET.get('q', '')
    category = normalize_category_label(request.GET.get('category', ''))
    show_all = request.GET.get('show_all', '') == 'true'

    # 获取总访问统计
    total_stats = DailyStats.objects.aggregate(
        total_uv=Sum('unique_visitors'),
        total_pv=Sum('total_views')
    )
    total_visitors = total_stats['total_uv'] or 0
    total_views = total_stats['total_pv'] or 0

    # 基础查询（排除军事和财经分类，定位为个人科技/生活/感悟分享）
    news_queryset = TechNews.objects.exclude(category__in=EXCLUDED_CATEGORIES)

    # 搜索过滤
    if query:
        news_queryset = news_queryset.filter(
            Q(title__icontains=query) | Q(key_word__icontains=query)
        )

    # 获取所有新闻（用于分类和排序）
    all_news = list(news_queryset.order_by('-id')[:400])
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
        .exclude(image_url='')
        .exclude(category__in=EXCLUDED_CATEGORIES)
        .order_by('-id', '-rate')[:240]
    )
    featured_news, featured_mode = pick_featured_news(featured_candidates)
    save_featured_snapshot(featured_news, featured_mode)
    featured_history = load_featured_history(featured_news, featured_candidates)

    # 1. 统计数据
    stats = {
        'total_count': TechNews.objects.count(),
        'avg_rate': TechNews.objects.aggregate(Avg('rate'))['rate__avg'] or 0,
        'category_counts': [
            {'category': cat, 'count': count}
            for cat, count in Counter(n.category for n in sorted_news if n.category).most_common()
        ],
        'accessible_count': len(accessible_news),
        'blocked_count': len(blocked_news),
        'today_count': len(today_news)
    }

    # 2. 关键词云
    all_titles = " ".join([n.title for n in accessible_news[:50]])
    words = re.findall(r'\w+', all_titles.lower())
    stop_words = {
        'the', 'a', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'is', 'with',
        'it', 'as', 'from', 'this', 'that', 'after', 'down', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'but', 'if', 'or',
        'about', 'into', 'through', 'before', 'above', 'below', 'which', 'who',
        'are', 'all', 'by', 'an', 'not', 'so', 'we', 'they', 'you', 'he', 'she'
    }
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]
    word_cloud = Counter(keywords).most_common(20)

    # 4. 获取最新的评论
    recent_comments = UserComment.objects.filter(is_approved=True).order_by('-created_at')[:10]

    # 5. 读取趋势分析数据
    trend_data = {}
    trend_data_json = "{}"
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trend_data.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                trend_data = json.load(f)
                trend_data_json = json.dumps(trend_data, ensure_ascii=False)
    except Exception as e:
        print(f"Error loading trend data: {e}")

    # 6. 提取特色栏目数据
    # 科学与数学 (包含趣说数学)：总计展示4条，权重最高优先
    science_math_news = [n for n in sorted_news if n.category in ['趣说数学', '科学与数学'] and not is_blocked_in_china(n.url)][:4]
    # 人物
    people_news = [n for n in sorted_news if n.category == '人物' and not is_blocked_in_china(n.url)][:5]

    # 热点产品：从机器人、智能硬件、汽车、VR/AR、军工等类别中选择权重最高的
    # 优化条件：1) 权重>2, 2) 最近14天的新闻, 3) 排除经济类
    product_categories = PRODUCT_CATEGORIES
    recent_14days = datetime.now().date() - timedelta(days=14)

    # 从数据库直接查询最新的高权重产品新闻
    product_news_query = TechNews.objects.filter(
        category__in=product_categories,
        rate__gt=2.0
    ).exclude(
        category__icontains='经济'
    ).order_by('-rate', '-id')[:50]  # 先取50条

    # 过滤：1) 被屏蔽的URL, 2) 旧新闻，并限制为5条
    product_news = []
    for news in product_news_query:
        if not is_blocked_in_china(news.url):
            # 检查发布时间，只保留最近14天的新闻
            is_recent = False
            try:
                if hasattr(news, 'publish_time') and news.publish_time:
                    pub_time_str = str(news.publish_time)
                    if len(pub_time_str) >= 10:
                        pub_date = datetime.strptime(pub_time_str[:10], '%Y-%m-%d').date()
                        # 只保留最近14天的新闻
                        if pub_date >= recent_14days:
                            is_recent = True
                    else:
                        # 无法解析时间格式，检查是否是最近创建的（通过ID判断）
                        # 假设ID越大越新
                        latest_id = TechNews.objects.order_by('-id').first().id
                        if news.id >= latest_id - 200:  # 最近200条记录内
                            is_recent = True
                else:
                    # 无发布时间，通过ID判断
                    latest_id = TechNews.objects.order_by('-id').first().id
                    if news.id >= latest_id - 200:
                        is_recent = True
            except Exception as e:
                # 解析失败，通过ID判断
                try:
                    latest_id = TechNews.objects.order_by('-id').first().id
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
            period_type='weekly',
            period_start__gte=recent_date
        ).order_by('rank')[:5]
    else:
        # 如果已有足够的product_news，也获取hot_products作为补充信息
        recent_date = datetime.now().date() - timedelta(days=2)
        hot_products = HotProduct.objects.filter(
            period_type='weekly',
            period_start__gte=recent_date
        ).order_by('rank')[:5]

    for hot_product in hot_products:
        hot_product.category = normalize_category_label(hot_product.category)

    # 原创专栏
    original_articles = list(OriginalArticle.objects.filter(is_published=True)[:10])

    context = {
        'accessible_news': accessible_news,
        'blocked_news': blocked_news,
        'featured_news': featured_news,
        'featured_mode_label': FEATURED_MODE_LABELS.get(featured_mode, ''),
        'featured_history': featured_history,
        'stats': stats,
        'trend_data': trend_data,
        'trend_data_json': trend_data_json,
        'word_cloud': word_cloud,
        'categories': categories,
        'current_category': category,
        'query': query,
        'recent_comments': recent_comments,
        'show_all': show_all,
        'total_visitors': total_visitors,
        'total_views': total_views,
        'today_news_ids': {n.id for n in today_news},
        'science_math_news': science_math_news,
        'people_news': people_news,
        'product_news': product_news,
        'hot_products': hot_products,
        'original_articles': original_articles,
    }

    return render(request, 'news/index.html', context)


def submit_comment(request):
    """提交用户评论"""
    if request.method == 'POST':
        username = request.POST.get('username', '匿名').strip() or '匿名'
        email = request.POST.get('email', '').strip()
        comment = request.POST.get('comment', '').strip()

        if comment:
            try:
                UserComment.objects.create(
                    username=username,
                    email=email,
                    comment=comment
                )
                messages.success(request, '感谢您的反馈！')
            except Exception as e:
                messages.error(request, f'提交失败：{str(e)}')
        else:
            messages.error(request, '评论内容不能为空！')

    return redirect('news_list')


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
    'tech':     ['https://36kr.com', 'https://www.ithome.com', 'https://huxiu.com'],
    'ai':       ['https://lmarena.ai/leaderboard',
                 'https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard',
                 'https://www.aibase.com',
                 'https://www.jiqizhixin.com'],
    'product':  ['https://www.ithome.com', 'https://www.smzdm.com'],
    'design':   ['https://www.zcool.com.cn', 'https://www.dezeen.com'],
    'science':  ['https://phys.org', 'https://www.sciencedaily.com'],
    'all':      ['https://36kr.com', 'https://huxiu.com'],
}

# SSRF 防护：仅允许白名单域名（防止用户提交内网地址）
_ALLOWED_CRAWL_DOMAINS = {
    # 科技
    '36kr.com', 'ithome.com', 'huxiu.com', 'techcrunch.com',
    'theverge.com', 'wired.com', 'venturebeat.com',
    # 人工智能
    'arena.ai', 'lmarena.ai', 'huggingface.co', 'aibase.com', 'jiqizhixin.com',
    'aitopics.org', 'syncedreview.com',
        # 产品
    'smzdm.com', 'zhuanlan.zhihu.com', 'sspai.com',
    # 设计
    'zcool.com.cn', 'dezeen.com', 'red-dot.org', 'if-design.org',
    # 科学
    'phys.org', 'sciencedaily.com', 'nature.com',
    # 通用
    'xinhuanet.com', 'people.com.cn', 'cnbc.com',
}


def _is_safe_crawl_url(url: str) -> bool:
    """SSRF 防护：只允许白名单域名"""
    if not url:
        return True
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith('www.'):
            host = host[4:]
        return any(host == d or host.endswith('.' + d) for d in _ALLOWED_CRAWL_DOMAINS)
    except Exception:
        return False


import re as _re

# 噪音行正则：导航链接、占位块字符、登录注册等
_NOISE_LINE_RE = _re.compile(
    r'^\s*\!\[\]\(.*?\)\s*$'                       # 纯空图片 ![]()
    r'|^\s*\[\]\(.*?\)\s*$'                         # 纯空链接 [](url)
    r'|[\u2580-\u259f\u25a0-\u25ff]{3,}'            # 块状占位符 ▅▅▅▅
    r'|\s*(登录\s*/\s*注册|加载更多|返回顶部|下载\s*APP|APP下载|暂无数据|查看更多)'
)
# 纯导航链接行：* [文字](url) 或 - [文字](url)，文字很短
_NAV_LINK_RE = _re.compile(r'^\s*[\*\-]\s*\[[^\]]{1,40}\]\(https?://[^\)]+\)\s*$')

_AI_SEARCH_CATEGORY_LABELS = {
    'all': '全部',
    'tech': '科技',
    'ai': 'AI/大模型',
    'product': '产品',
    'design': '设计',
    'science': '科学',
}

_AI_CATEGORY_HINTS = {
    'ai': ['ai', '人工智能', '大模型', 'llm', 'chatgpt', 'openai', 'deepseek'],
    'product': ['产品', '机器人', '芯片', '汽车', '智能硬件', '半导体'],
    'design': ['设计', '工业设计', '红点奖', 'if设计'],
    'science': ['科学', '数学', '物理', '生物', '科研'],
}

_AI_SEARCH_RUNTIME_READY = False


def _json_error(message: str, status: int = 500, code: str = '', detail: str = ''):
    payload = {'error': message}
    if code:
        payload['code'] = code
    if detail and settings.DEBUG:
        payload['detail'] = detail[:200]
    return JsonResponse(payload, status=status)


def _format_crawl_runtime_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lower = message.lower()

    if isinstance(exc, ModuleNotFoundError):
        missing_name = (getattr(exc, 'name', '') or '').lower()
        if 'crawl4ai' in missing_name:
            return '服务器未安装 crawl4ai，请执行: pip install -r requirements.txt'
        if 'playwright' in missing_name:
            return '服务器未安装 Playwright，请执行: pip install -r requirements.txt'

    if 'crawl4ai' in lower and 'no module named' in lower:
        return '服务器未安装 crawl4ai，请执行: pip install -r requirements.txt'
    if 'playwright' in lower and 'no module named' in lower:
        return '服务器未安装 Playwright，请执行: pip install -r requirements.txt'
    if "executable doesn't exist" in lower or 'playwright install' in lower:
        return '服务器缺少 Chromium 浏览器，请执行: python -m playwright install chromium'
    if any(token in lower for token in [
        'libnss3', 'libatk-1.0', 'libatk-bridge-2.0', 'libdrm', 'libgbm',
        'libxkbcommon', 'libxcomposite', 'libxdamage', 'libxfixes', 'libxrandr',
    ]):
        return '服务器缺少 Chromium 运行库，请先安装系统依赖，再执行: python -m playwright install chromium'

    return message[:500]


def _get_ai_search_runtime_error() -> str:
    global _AI_SEARCH_RUNTIME_READY
    if _AI_SEARCH_RUNTIME_READY:
        return ''

    try:
        import crawl4ai  # noqa: F401
    except Exception as exc:
        return _format_crawl_runtime_error(exc)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser_path = playwright.chromium.executable_path
            if not browser_path or not os.path.exists(browser_path):
                raise RuntimeError("Chromium executable doesn't exist")
    except Exception as exc:
        return _format_crawl_runtime_error(exc)

    _AI_SEARCH_RUNTIME_READY = True
    return ''


def _filter_markdown(md: str, query: str) -> str:
    """
    清理爬取的 Markdown：
    1. 去掉导航/噪音行
    2. 压缩连续空行
    3. 优先返回含关键词的段落（上下文各保留1段）
    """
    lines = md.split('\n')
    q_words = [w.lower() for w in query.split() if len(w) > 1]

    cleaned = []
    for line in lines:
        s = line.strip()
        if not s:
            cleaned.append('')
            continue
        if _NOISE_LINE_RE.search(s):
            continue
        if _NAV_LINK_RE.match(s):
            continue
        # 丢弃过短非标题行
        if len(s) < 6 and not s.startswith('#'):
            continue
        cleaned.append(line)

    # 压缩连续空行
    merged, blanks = [], 0
    for l in cleaned:
        if l.strip() == '':
            blanks += 1
            if blanks <= 1:
                merged.append(l)
        else:
            blanks = 0
            merged.append(l)

    full_text = '\n'.join(merged).strip()

    if not q_words:
        return full_text[:8000]

    # 按双换行切段落，优先返回含关键词的段落
    paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]
    relevant, others = [], []
    for p in paragraphs:
        if any(w in p.lower() for w in q_words):
            relevant.append(p)
        else:
            others.append(p)

    if relevant:
        output = '\n\n'.join(relevant)
        # 若相关段落很少，补充前几段通用内容
        if len(output) < 500 and others:
            output += '\n\n---\n' + '\n\n'.join(others[:3])
        return output[:8000]

    # 没有精确匹配段落，返回清理后全文头部
    return full_text[:8000]


def _clean_ai_search_text(value: str) -> str:
    return _re.sub(r'\s+', ' ', str(value or '')).strip()


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _normalize_score(value, min_value, max_value, fallback=0.5) -> float:
    if max_value <= min_value:
        return fallback
    return max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))


def _extract_ai_query_terms(query: str):
    normalized_query = _clean_ai_search_text(query).lower()
    if not normalized_query:
        return []

    terms = []

    def _add_term(term: str):
        term = term.strip().lower()
        if len(term) < 2 or term in terms:
            return
        terms.append(term)

    _add_term(normalized_query)
    for token in _re.findall(r'[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9\-\+\.]{1,}', normalized_query):
        _add_term(token)
        if _re.fullmatch(r'[\u4e00-\u9fff]+', token) and len(token) >= 4:
            for gram_size in range(2, min(4, len(token)) + 1):
                for index in range(len(token) - gram_size + 1):
                    _add_term(token[index:index + gram_size])
    return terms[:12]


def _score_text_presence(text: str, query: str, query_terms) -> float:
    normalized_text = _clean_ai_search_text(text).lower()
    if not normalized_text:
        return 0.0

    score = 0.0
    matched_terms = 0
    if query and query in normalized_text:
        score += 5.0
        matched_terms += 1

    for term in query_terms:
        if term and term in normalized_text:
            matched_terms += 1
            score += min(2.4, 0.7 + len(term) * 0.18)

    if query_terms:
        score += (matched_terms / len(query_terms)) * 2.0
    return score


def _extract_relevant_excerpt(text: str, query_terms, max_length=180) -> str:
    cleaned_text = _clean_ai_search_text(text)
    if not cleaned_text:
        return ''

    lowered_text = cleaned_text.lower()
    anchor_index = -1
    for term in query_terms:
        anchor_index = lowered_text.find(term)
        if anchor_index != -1:
            break

    if anchor_index == -1:
        return cleaned_text[:max_length] + ('...' if len(cleaned_text) > max_length else '')

    start_index = max(anchor_index - max_length // 3, 0)
    end_index = min(start_index + max_length, len(cleaned_text))
    excerpt = cleaned_text[start_index:end_index]
    if start_index > 0:
        excerpt = '...' + excerpt
    if end_index < len(cleaned_text):
        excerpt += '...'
    return excerpt


def _build_ai_query_filter(query_terms):
    query_filter = Q()
    for term in query_terms[:6]:
        query_filter |= Q(title__icontains=term)
        query_filter |= Q(key_word__icontains=term)
        query_filter |= Q(category__icontains=term)
        if len(term) >= 4 or not _re.fullmatch(r'[\u4e00-\u9fff]+', term):
            query_filter |= Q(content__icontains=term)
    return query_filter


def _build_ai_category_filter(category):
    category_filter = Q()

    if category == 'military':
        for label in set(MILITARY_CATEGORY_ALIASES) | {'军事', '军工与航天', '航空航天'}:
            category_filter |= Q(category__icontains=label)
    elif category == 'economy':
        for label in set(ECONOMY_CATEGORY_ALIASES) | {'经济'}:
            category_filter |= Q(category__icontains=label)
    elif category == 'product':
        for label in set(PRODUCT_CATEGORIES) | {'产品'}:
            category_filter |= Q(category__icontains=label)
    elif category == 'design':
        category_filter = Q(category__icontains='设计')
    elif category == 'science':
        category_filter = Q(category__icontains='科学') | Q(category__icontains='数学')
    elif category == 'ai':
        category_filter = (
            Q(category__icontains='AI') |
            Q(category__icontains='人工智能') |
            Q(key_word__icontains='AI') |
            Q(key_word__icontains='大模型')
        )
    elif category == 'tech':
        category_filter = Q(category__icontains='科技') | Q(category__icontains='人工智能')

    return category_filter


def _category_match_score(news_item, category):
    normalized_category = normalize_news_category(news_item)
    if category == 'all' or not category:
        return 0.45
    if category == 'military':
        return 1.0 if normalized_category in {'军事', '航空航天'} else 0.0
    if category == 'economy':
        return 1.0 if normalized_category in ECONOMY_CATEGORY_ALIASES or '经济' in normalized_category else 0.0
    if category == 'product':
        return 1.0 if normalized_category in PRODUCT_CATEGORIES or '产品' in normalized_category else 0.0
    if category == 'design':
        return 1.0 if '设计' in normalized_category else 0.0
    if category == 'science':
        return 1.0 if normalized_category in {'科学与数学', '趣说数学'} or '科学' in normalized_category or '数学' in normalized_category else 0.0
    if category == 'ai':
        ai_text = _clean_ai_search_text(
            f"{getattr(news_item, 'title', '')} {getattr(news_item, 'key_word', '')} {getattr(news_item, 'category', '')}"
        ).lower()
        return 1.0 if any(keyword in ai_text for keyword in _AI_CATEGORY_HINTS['ai']) else 0.0
    if category == 'tech':
        return 1.0 if normalized_category not in {'军事', '航空航天'} and normalized_category not in ECONOMY_CATEGORY_ALIASES else 0.35
    return 0.0


def _recall_local_news_results(query: str, category: str, limit=6):
    query_terms = _extract_ai_query_terms(query)
    for hint in _AI_CATEGORY_HINTS.get(category, [])[:3]:
        if hint not in query_terms:
            query_terms.append(hint)
    normalized_query = _clean_ai_search_text(query).lower()

    query_filter = _build_ai_query_filter(query_terms)
    category_filter = _build_ai_category_filter(category)
    queryset = TechNews.objects.all()

    if category != 'all' and category_filter.children:
        queryset = queryset.filter(category_filter)
        if query_filter.children:
            queryset = queryset.filter(query_filter)
    elif query_filter.children:
        queryset = queryset.filter(query_filter)
    elif category_filter.children:
        queryset = queryset.filter(category_filter)

    candidates = list(queryset.order_by('-id')[:120])
    if not candidates and query_filter.children:
        candidates = list(TechNews.objects.filter(query_filter).order_by('-id')[:80])

    if not candidates:
        return []

    today = datetime.now().date()
    raw_scores = []
    rate_values = []
    for news_item in candidates:
        raw_match_score = (
            _score_text_presence(getattr(news_item, 'title', ''), normalized_query, query_terms) * 1.7 +
            _score_text_presence(getattr(news_item, 'key_word', ''), normalized_query, query_terms) * 1.25 +
            _score_text_presence(getattr(news_item, 'content', ''), normalized_query, query_terms) * 0.7 +
            _score_text_presence(getattr(news_item, 'category', ''), normalized_query, query_terms) * 0.8
        )
        rate_value = _safe_float(getattr(news_item, 'rate', 0))
        category_score = _category_match_score(news_item, category)
        if raw_match_score <= 0 and category_score <= 0:
            continue

        publish_date = parse_news_publish_date(news_item)
        age_days = max((today - publish_date).days, 0)
        freshness_score = max(0.0, 1 - min(age_days, 30) / 30)
        domain = urlparse(getattr(news_item, 'url', '') or '').netloc.replace('www.', '')
        raw_scores.append({
            'source_type': 'db',
            'title': getattr(news_item, 'title', ''),
            'url': getattr(news_item, 'url', ''),
            'domain': domain or f"db-{getattr(news_item, 'id', 0)}",
            'source_label': getattr(news_item, 'author', '') or '本地数据库',
            'category': normalize_news_category(news_item),
            'publish_time': str(getattr(news_item, 'publish_time', '') or '')[:10],
            'raw_match_score': raw_match_score,
            'rate_value': rate_value,
            'freshness_score': freshness_score,
            'category_score': category_score,
            'content': getattr(news_item, 'content', '') or '',
            'snippet': _extract_relevant_excerpt(getattr(news_item, 'content', '') or getattr(news_item, 'title', ''), query_terms),
            'id': getattr(news_item, 'id', 0),
        })
        rate_values.append(rate_value)

    if not raw_scores:
        return []

    max_match_score = max(item['raw_match_score'] for item in raw_scores) or 1.0
    rate_min = min(rate_values) if rate_values else 0.0
    rate_max = max(rate_values) if rate_values else 1.0

    for item in raw_scores:
        match_score = item['raw_match_score'] / max_match_score if max_match_score > 0 else 0.0
        rate_score = _normalize_score(item['rate_value'], rate_min, rate_max, fallback=0.4 if item['rate_value'] > 0 else 0.0)
        item['score'] = round(
            match_score * 0.58 +
            rate_score * 0.22 +
            item['freshness_score'] * 0.12 +
            item['category_score'] * 0.08,
            4
        )

    deduped_results = []
    seen_titles = set()
    for item in sorted(raw_scores, key=lambda current: (current['score'], current['rate_value'], current['id']), reverse=True):
        title_key = item['title'].strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped_results.append(item)
        if len(deduped_results) >= limit:
            break
    return deduped_results


def _rank_web_search_results(query: str, category: str, web_results):
    query_terms = _extract_ai_query_terms(query)
    normalized_query = _clean_ai_search_text(query).lower()
    if not web_results:
        return []

    for item in web_results:
        content = item.get('content', '') or ''
        item['raw_match_score'] = _score_text_presence(content, normalized_query, query_terms)
        item['quality_score'] = max(0.15, min(len(_clean_ai_search_text(content)) / 1400, 1.0))
        item['category_score'] = 0.9 if category and category != 'all' else 0.55
        item['snippet'] = _extract_relevant_excerpt(content, query_terms)

    max_match_score = max(item['raw_match_score'] for item in web_results) or 1.0
    for item in web_results:
        match_score = item['raw_match_score'] / max_match_score if max_match_score > 0 else 0.0
        item['score'] = round(
            match_score * 0.74 +
            item['quality_score'] * 0.18 +
            item['category_score'] * 0.08,
            4
        )

    return sorted(web_results, key=lambda current: (current['score'], current['quality_score']), reverse=True)


def _merge_ai_search_results(web_results, db_results, category, target_url='', limit=6):
    unified_results = []
    seen_titles = set()
    domain_counter = defaultdict(int)
    domain_limit = 3 if target_url else 1 if category == 'military' else 2

    def _can_use(item):
        title_key = item.get('title', '').strip().lower()
        if title_key and title_key in seen_titles:
            return False
        domain_key = item.get('domain') or item.get('source_type')
        if domain_counter[domain_key] >= domain_limit:
            return False
        return True

    def _use(item):
        title_key = item.get('title', '').strip().lower()
        domain_key = item.get('domain') or item.get('source_type')
        unified_results.append(item)
        if title_key:
            seen_titles.add(title_key)
        domain_counter[domain_key] += 1

    if web_results and _can_use(web_results[0]):
        _use(web_results[0])
    if db_results and _can_use(db_results[0]):
        _use(db_results[0])

    all_candidates = sorted(web_results + db_results, key=lambda current: current.get('score', 0), reverse=True)
    for item in all_candidates:
        if len(unified_results) >= limit:
            break
        if not _can_use(item):
            continue
        _use(item)

    return sorted(unified_results, key=lambda current: current.get('score', 0), reverse=True)


def _build_ai_search_warnings(web_results, db_results, unified_results, target_url=''):
    warnings = []
    if not web_results:
        warnings.append('公开网站未抓到有效结果，本次回答主要依赖本地数据库')
    if not db_results:
        warnings.append('本地数据库未命中相关记录，本次回答主要依赖公开网站')

    web_domains = {item.get('domain') for item in web_results if item.get('domain')}
    if web_results and not target_url and len(web_domains) == 1:
        warnings.append(f"公开网页证据当前主要来自 {next(iter(web_domains))}，来源较单一")

    unified_domains = {item.get('domain') for item in unified_results if item.get('domain')}
    if len(unified_domains) <= 1 and len(unified_results) >= 2:
        warnings.append('综合结果的来源多样性不足，建议缩小关键词或指定目标网址')

    return warnings


def _render_ai_search_section(title, results, empty_text):
    lines = [title]
    if not results:
        lines.append(empty_text)
        return lines

    for index, item in enumerate(results, start=1):
        source_type_label = '公开网页' if item.get('source_type') == 'web' else '本地数据库'
        lines.append(f"{index}. [{source_type_label}] {item.get('title', '')}")
        meta_parts = [f"评分 {item.get('score', 0):.3f}", f"来源 {item.get('source_label', '')}"]
        if item.get('category'):
            meta_parts.append(f"分类 {item.get('category')}")
        if item.get('publish_time'):
            meta_parts.append(f"时间 {item.get('publish_time')}")
        lines.append('   ' + ' | '.join(meta_parts))
        if item.get('url'):
            lines.append(f"   链接: {item.get('url')}")
        if item.get('snippet'):
            lines.append(f"   摘要: {item.get('snippet')}")
        lines.append('')
    return lines


def _render_ai_search_report(query, category, unified_results, web_results, db_results, warnings):
    lines = [
        '# AI 混合搜索结果',
        '',
        f"关键词：{query}",
        f"分类：{_AI_SEARCH_CATEGORY_LABELS.get(category, '全部')}",
        '',
        '## 检索摘要',
        f"- 公开网站命中：{len(web_results)} 个来源",
        f"- 本地数据库命中：{len(db_results)} 条记录",
        '- 已按相关度、时效、权重和来源去重进行统一重排',
    ]

    if warnings:
        lines.append(f"- 提示：{'；'.join(warnings)}")

    lines.append('')
    lines.extend(_render_ai_search_section('## 综合排序结果', unified_results, '暂无综合结果'))
    lines.append('')
    lines.extend(_render_ai_search_section('## 本地数据库优先命中', db_results[:4], '暂无本地数据库命中'))
    lines.append('')
    lines.extend(_render_ai_search_section('## 公开网站优先命中', web_results[:4], '暂无公开网站命中'))
    return '\n'.join(line.rstrip() for line in lines).strip()[:14000]


def _build_ai_search_answer(query, unified_results, warnings):
    if not unified_results:
        return '当前没有足够证据生成回答，请尝试调整关键词。'

    top_titles = [item.get('title', '') for item in unified_results[:3] if item.get('title')]
    source_counts = defaultdict(int)
    for item in unified_results[:4]:
        source_counts[item.get('source_type') or 'unknown'] += 1

    evidence_parts = []
    if source_counts.get('db'):
        evidence_parts.append(f"本地数据库命中 {source_counts['db']} 条")
    if source_counts.get('web'):
        evidence_parts.append(f"公开网页命中 {source_counts['web']} 条")

    answer = [
        f"围绕“{query}”的结果已按相关度、时效和来源多样性完成混合排序。",
    ]
    if top_titles:
        answer.append(f"当前最相关的线索包括：{'；'.join(top_titles)}。")
    if evidence_parts:
        answer.append(f"本次回答综合了{'，'.join(evidence_parts)}。")
    if warnings:
        answer.append(f"需要注意：{warnings[0]}。")
    return ''.join(answer)


def _serialize_ai_result_item(item):
    return {
        'source_type': item.get('source_type', ''),
        'title': item.get('title', ''),
        'url': item.get('url', ''),
        'domain': item.get('domain', ''),
        'source_label': item.get('source_label', ''),
        'category': item.get('category', ''),
        'publish_time': item.get('publish_time', ''),
        'snippet': item.get('snippet', ''),
        'score': round(_safe_float(item.get('score', 0.0)), 4),
    }


def _build_ai_search_payload(query, category, unified_results, web_results, db_results, warnings):
    summary = {
        'query': query,
        'category': category,
        'category_label': _AI_SEARCH_CATEGORY_LABELS.get(category, '全部'),
        'web_count': len(web_results),
        'db_count': len(db_results),
        'merged_count': len(unified_results),
    }
    payload = {
        'summary': summary,
        'answer': _build_ai_search_answer(query, unified_results, warnings),
        'warnings': warnings,
        'combined_results': [_serialize_ai_result_item(item) for item in unified_results],
        'db_results': [_serialize_ai_result_item(item) for item in db_results[:6]],
        'web_results': [_serialize_ai_result_item(item) for item in web_results[:6]],
    }
    payload['sections'] = [
        {
            'key': 'answer',
            'title': '综合回答',
            'type': 'answer',
            'content': payload['answer'],
        },
        {
            'key': 'db_results',
            'title': '数据库证据',
            'type': 'results',
            'items': payload['db_results'],
            'empty_text': '暂无本地数据库命中',
        },
        {
            'key': 'web_results',
            'title': '网页证据',
            'type': 'results',
            'items': payload['web_results'],
            'empty_text': '暂无公开网页命中',
        },
    ]
    return payload


def _build_legacy_ai_search_payload(task):
    if not task.result_md:
        return {}
    return {
        'summary': {
            'query': task.query,
            'category': task.category,
            'category_label': _AI_SEARCH_CATEGORY_LABELS.get(task.category, '全部'),
            'web_count': 0,
            'db_count': 0,
            'merged_count': 0,
        },
        'answer': task.result_md,
        'warnings': [],
        'combined_results': [],
        'db_results': [],
        'web_results': [],
        'sections': [
            {
                'key': 'answer',
                'title': '综合回答',
                'type': 'answer',
                'content': task.result_md,
            },
            {
                'key': 'db_results',
                'title': '数据库证据',
                'type': 'results',
                'items': [],
                'empty_text': '历史任务未保存数据库证据',
            },
            {
                'key': 'web_results',
                'title': '网页证据',
                'type': 'results',
                'items': [],
                'empty_text': '历史任务未保存网页证据',
            },
        ],
    }


def _run_crawl(task_id: int):
    """后台线程：并发抓取公开站点并结合本地数据库结果统一重排。"""
    from .models import AiSearchTask

    def _save(task, **kw):
        for k, v in kw.items():
            setattr(task, k, v)
        task.save(update_fields=list(kw.keys()) + ['updated_at'])

    try:
        task = AiSearchTask.objects.get(id=task_id)
        _save(task, status='running')

        runtime_error = _get_ai_search_runtime_error()
        if runtime_error:
            _save(task, status='error', result_md='', result_payload='', error_msg=runtime_error)
            return

        query = task.query
        category = task.category
        # 用户指定了 URL → 单源；否则按分类取多源
        if task.target_url:
            urls = [task.target_url]
        else:
            urls = _AI_SEARCH_MULTI_URLS.get(category,
                    _AI_SEARCH_MULTI_URLS['all'])

        async def _crawl_one(crawler, url: str, run_cfg):
            """抓单个 URL，失败时返回错误信息。"""
            host = urlparse(url).netloc.replace('www.', '')
            try:
                result = await crawler.arun(url=url, config=run_cfg)
                if result.success:
                    filtered_markdown = _filter_markdown(result.markdown or '', query)
                    if filtered_markdown.strip():
                        return {
                            'source_type': 'web',
                            'title': f'{host} 公开网页抓取',
                            'url': url,
                            'domain': host or 'web',
                            'source_label': host or '公开网页',
                            'category': _AI_SEARCH_CATEGORY_LABELS.get(category, '公开网页'),
                            'publish_time': '',
                            'content': filtered_markdown,
                        }
                return {'error': f'{host} 未返回有效正文'}
            except Exception as exc:
                return {'error': f'{host} 抓取失败: {str(exc)[:120]}'}

        async def _crawl_all():
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
            from crawl4ai.cache_context import CacheMode

            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                enable_stealth=True,
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                java_script_enabled=True,
                viewport_width=1280,
                viewport_height=800,
            )

            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=8,
                # domcontentloaded：页面 DOM 就绪即返回，避免等待广告/tracker 超时
                wait_until='domcontentloaded',
                page_timeout=45000,
                magic=True,
                simulate_user=True,
                override_navigator=True,
                remove_overlay_elements=True,
                remove_consent_popups=True,
                excluded_tags=[
                    'nav', 'header', 'footer', 'aside', 'script',
                    'style', 'noscript', 'form',
                ],
                excluded_selector=(
                    '.nav, .navbar, .menu, .sidebar, .footer, .header, '
                    '.login, .register, .cookie-notice, .advertisement, '
                    '.ad, [class*="banner"], [class*="popup"], '
                    '[id*="cookie"], [class*="cookie"]'
                ),
                wait_for_images=False,
                verbose=False,
            )

            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                results = await asyncio.gather(
                    *[_crawl_one(crawler, u, run_cfg) for u in urls],
                    return_exceptions=True
                )

            web_results = []
            warnings = []
            for result in results:
                if isinstance(result, Exception):
                    warnings.append(str(result)[:120])
                elif isinstance(result, dict) and result.get('content'):
                    web_results.append(result)
                elif isinstance(result, dict) and result.get('error'):
                    warnings.append(result['error'])
            return web_results, warnings

        db_results = _recall_local_news_results(query, category)

        try:
            web_results, crawl_warnings = asyncio.run(_crawl_all())
        except Exception as exc:
            web_results, crawl_warnings = [], [_format_crawl_runtime_error(exc)[:120]]

        ranked_web_results = _rank_web_search_results(query, category, web_results)
        unified_results = _merge_ai_search_results(ranked_web_results, db_results, category, task.target_url)
        warnings = _build_ai_search_warnings(ranked_web_results, db_results, unified_results, task.target_url)
        warnings.extend(crawl_warnings[:3])

        if not unified_results:
            error_msg = '公开网站和本地数据库都未找到相关结果，请尝试缩小关键词或指定网址'
            if crawl_warnings:
                error_msg = '；'.join(crawl_warnings[:2])[:500]
            _save(
                task,
                status='error',
                result_md='',
                result_payload='',
                error_msg=error_msg
            )
            return

        payload = _build_ai_search_payload(query, category, unified_results, ranked_web_results, db_results, warnings)
        content = _render_ai_search_report(query, category, unified_results, ranked_web_results, db_results, warnings)
        _save(
            task,
            status='done',
            result_md=content,
            result_payload=json.dumps(payload, ensure_ascii=False),
            error_msg=''
        )
    except Exception as e:
        logger.exception('AI search crawl task failed', extra={'task_id': task_id})
        try:
            from .models import AiSearchTask
            AiSearchTask.objects.filter(id=task_id).update(
                status='error',
                error_msg=_format_crawl_runtime_error(e)[:500],
                result_payload=''
            )
        except Exception:
            pass


@csrf_exempt
@require_POST
def ai_search_submit(request):
    """POST JSON: {query, url?, category?} → {task_id, status}"""
    from .models import AiSearchTask
    try:
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        query = str(data.get('query', '')).strip()[:200]
        target_url = str(data.get('url', '')).strip()[:500]
        category = str(data.get('category', 'all'))[:20]

        if not query:
            return JsonResponse({'error': '请输入搜索关键词'}, status=400)
        if target_url and not _is_safe_crawl_url(target_url):
            return JsonResponse({'error': '不支持的目标域名，请从白名单中选择'}, status=400)

        runtime_error = _get_ai_search_runtime_error()
        if runtime_error:
            return _json_error(runtime_error, status=503, code='crawl_runtime_unavailable')

        task = AiSearchTask.objects.create(query=query, target_url=target_url, category=category)
        threading.Thread(target=_run_crawl, args=(task.id,), daemon=True).start()
        return JsonResponse({'task_id': task.id, 'status': 'pending'})
    except Exception as exc:
        logger.exception('AI search submit failed')
        return _json_error(
            'AI 搜索服务初始化失败，请检查服务器日志',
            status=500,
            code='ai_search_submit_failed',
            detail=str(exc),
        )


@require_GET
def ai_search_status(request, task_id):
    """GET /ai-search/status/<id>/ → {status, result_md, result, error_msg}"""
    from .models import AiSearchTask
    try:
        try:
            task = AiSearchTask.objects.get(id=int(task_id))
        except (AiSearchTask.DoesNotExist, ValueError):
            return JsonResponse({'error': '任务不存在'}, status=404)

        payload = {}
        if task.status == 'done':
            if task.result_payload:
                try:
                    payload = json.loads(task.result_payload)
                except json.JSONDecodeError:
                    payload = _build_legacy_ai_search_payload(task)
            else:
                payload = _build_legacy_ai_search_payload(task)

        return JsonResponse({
            'task_id': task.id,
            'status': task.status,
            'result_md': task.result_md if task.status == 'done' else '',
            'result': payload,
            'error_msg': task.error_msg,
            'query': task.query,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    except Exception as exc:
        logger.exception('AI search status lookup failed', extra={'task_id': task_id})
        return _json_error(
            'AI 搜索状态查询失败，请检查服务器日志',
            status=500,
            code='ai_search_status_failed',
            detail=str(exc),
        )
