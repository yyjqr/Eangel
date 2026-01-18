from django.shortcuts import render, redirect
from django.db.models import Q, Count, Avg
from .models import TechNews, UserComment
from django.contrib import messages
import re
from collections import Counter
from datetime import datetime, timedelta

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
]


def is_blocked_in_china(url):
    """判断URL是否在中国大陆被屏蔽"""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in BLOCKED_DOMAINS)


def news_list(request):
    # 获取参数
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    show_all = request.GET.get("show_all", "") == "true"

    # 基础查询
    news_queryset = TechNews.objects.all()

    # 搜索过滤
    if query:
        news_queryset = news_queryset.filter(
            Q(title__icontains=query) | Q(key_word__icontains=query)
        )

    # 分类过滤
    if category:
        news_queryset = news_queryset.filter(category=category)

    # 获取所有新闻（用于分类和排序）
    all_news = list(news_queryset.order_by("-id")[:200])

    # 智能排序：当天文章按权重，之前文章按时间+权重
    today = datetime.now().date()
    today_news = []
    old_news = []

    for news_item in all_news:
        try:
            # 尝试解析发布时间
            if hasattr(news_item, "publish_time") and news_item.publish_time:
                # 处理多种时间格式
                pub_time_str = str(news_item.publish_time)
                try:
                    if len(pub_time_str) > 10:
                        pub_date = datetime.strptime(
                            pub_time_str[:10], "%Y-%m-%d"
                        ).date()
                    else:
                        pub_date = datetime.strptime(pub_time_str, "%Y-%m-%d").date()
                except:
                    pub_date = today - timedelta(days=1)  # 默认为昨天
            else:
                pub_date = today - timedelta(days=1)

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

    # 提取带图片的文章用于轮播展示（优先选择高权重和有图片的）
    featured_news = []
    for news in accessible_news[:20]:  # 从前20条中选择
        if news.image_url and len(featured_news) < 8:
            featured_news.append(news)

    # 1. 统计数据
    stats = {
        "total_count": TechNews.objects.count(),
        "avg_rate": TechNews.objects.aggregate(Avg("rate"))["rate__avg"] or 0,
        "category_counts": TechNews.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count"),
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

    # 3. 所有分类列表
    categories = TechNews.objects.values_list("category", flat=True).distinct()

    # 4. 获取最新的评论
    recent_comments = UserComment.objects.filter(is_approved=True).order_by(
        "-created_at"
    )[:10]

    context = {
        "accessible_news": accessible_news,
        "blocked_news": blocked_news,
        "featured_news": featured_news,
        "stats": stats,
        "word_cloud": word_cloud,
        "categories": categories,
        "current_category": category,
        "query": query,
        "recent_comments": recent_comments,
        "show_all": show_all,
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
