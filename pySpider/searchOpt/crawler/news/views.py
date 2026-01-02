from django.shortcuts import render
from django.db.models import Q, Count, Avg
from .models import TechNews
import re
from collections import Counter


def news_list(request):
    # 获取参数
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")

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

    # 排序并取前100
    news = news_queryset.order_by("-id")[:100]

    # 1. 统计数据 (Dashboard)
    stats = {
        "total_count": TechNews.objects.count(),
        "avg_rate": TechNews.objects.aggregate(Avg("rate"))["rate__avg"] or 0,
        "category_counts": TechNews.objects.values("category")
        .annotate(count=Count("id"))
        .order_by("-count"),
    }

    # 2. 关键词云 (Simple implementation)
    all_titles = " ".join([n.title for n in news])
    words = re.findall(r"\w+", all_titles.lower())
    # 过滤掉停用词和短词
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

    # 3. 所有分类列表 (用于筛选菜单)
    categories = TechNews.objects.values_list("category", flat=True).distinct()

    context = {
        "news_list": news,
        "stats": stats,
        "word_cloud": word_cloud,
        "categories": categories,
        "current_category": category,
        "query": query,
    }

    return render(request, "news/index.html", context)
