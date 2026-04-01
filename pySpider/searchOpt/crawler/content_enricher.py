"""
content_enricher.py — 文章内容增强器
======================================
对 tech / economy / products 分类文章的 content 字段做自动增强。

两条路径：
  1. HTTP 快速路径  —— requests + BeautifulSoup，适合静态页面（多数 RSS 来源）
  2. crawl4ai 慢路径 —— 无头浏览器，适合 JS 密集页面（36kr、IT之家等）

公开 API：
  get_enriched_content(url, title='', category='', use_crawl4ai=False, timeout=8)
      → str   前 3 句话拼接，失败返回 ''

  enrich_content_http(url, timeout=8)      → str
  enrich_content_crawl4ai(url, timeout=30) → str
"""

import re
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── 常见文章主体选择器（优先级从高到低） ──────────────────────────────────
_ARTICLE_SELECTORS = [
    '[itemprop="articleBody"]',
    "article .article-body",
    "article .post-content",
    "article .entry-content",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".content-body",
    ".article-body",
    ".news-content",
    ".detail-content",
    ".text-content",
    ".story-body",
    "article",
    "main",
]

# 噪音标签（直接丢弃）
_STRIP_TAGS = {
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    "form",
    "button",
    "figure",
    "figcaption",
    "iframe",
    "ins",
    "ad",
    "advertisement",
}

# 句子分割正则
_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?])\s+|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])")

# 噪音文本关键词（跳过含这些词的"句子"）
_NOISE_KEYWORDS_RE = re.compile(
    r"(cookie|advertisement|版权所有|copyright|subscribe|订阅|登录|注册|" r"加载更多|返回顶部|扫码关注|点击查看)",
    re.IGNORECASE,
)

# JS 密集型域名（HTTP 路径通常拿不到正文，优先用 crawl4ai）
_JS_HEAVY_DOMAINS = {
    "36kr.com",
    "ithome.com",
    "huxiu.com",
    "jiqizhixin.com",
    "aibase.com",
    "smzdm.com",
    "zhihu.com",
    "sspai.com",
    "sina.com.cn",
    "sohu.com",
    "toutiao.com",
}

# 无法在大陆直接访问的域名（不做 HTTP 请求）
_BLOCKED_DOMAINS = {
    "google.com",
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "foxnews.com",
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "reuters.com",
    "bbc.com",
    "cnn.com",
    "engadget.com",
}


# ── 内部工具函数 ─────────────────────────────────────────────────────────────


def _is_blocked(url: str) -> bool:
    from urllib.parse import urlparse

    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in _BLOCKED_DOMAINS)
    except Exception:
        return False


def _is_js_heavy(url: str) -> bool:
    from urllib.parse import urlparse

    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in _JS_HEAVY_DOMAINS)
    except Exception:
        return False


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _ensure_end(s: str) -> str:
    if not s:
        return s
    if s[-1] not in "。！？.!?":
        return s + ("。" if re.search(r"[\u4e00-\u9fff]", s) else ".")
    return s


def _split_sentences(text: str) -> list:
    """将纯文本切分为有意义的句子列表。"""
    parts = _SENT_SPLIT_RE.split(text)
    result, seen = [], set()
    for part in parts:
        part = _clean(part)
        if len(part) < 15:
            continue
        lo = part.lower()
        if lo in seen:
            continue
        if _NOISE_KEYWORDS_RE.search(lo):
            continue
        seen.add(lo)
        result.append(part)
    return result


def _extract_from_html(html: str, n: int = 3) -> str:
    """从 HTML 中提取前 n 句文章正文。"""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 去掉噪音标签
        for tag in soup.find_all(list(_STRIP_TAGS)):
            tag.decompose()

        # 尝试定位文章主体
        body = None
        for sel in _ARTICLE_SELECTORS:
            body = soup.select_one(sel)
            if body:
                break
        if body is None:
            body = soup.body or soup

        # 收集段落文本
        paragraphs = body.find_all(["p", "li", "blockquote"])
        chunks = [
            _clean(p.get_text()) for p in paragraphs if len(_clean(p.get_text())) > 20
        ]

        full_text = " ".join(chunks[:15])  # 取前 15 段够用
        sentences = _split_sentences(full_text)
        if not sentences:
            return ""
        return " ".join(_ensure_end(s) for s in sentences[:n])
    except Exception as e:
        logger.debug(f"_extract_from_html error: {e}")
        return ""


# ── 公开路径函数 ─────────────────────────────────────────────────────────────


def enrich_content_http(url: str, timeout: int = 8) -> str:
    """
    HTTP 快速路径：requests + BeautifulSoup，返回文章前 3 句。
    失败/不可访问时返回 ''。
    """
    if _is_blocked(url):
        return ""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return _extract_from_html(resp.text, n=3)
    except Exception as e:
        logger.debug(f"HTTP enrich failed [{url}]: {e}")
    return ""


def enrich_content_crawl4ai(url: str, timeout: int = 30) -> str:
    """
    crawl4ai 慢路径：无头浏览器渲染，返回文章前 3 句。
    适合 JS 密集页面或需要更完整内容时使用。
    """
    if _is_blocked(url):
        return ""
    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode

        async def _crawl() -> str:
            browser_cfg = BrowserConfig(
                headless=True,
                verbose=False,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
            )
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=8,
                wait_until="domcontentloaded",
                page_timeout=timeout * 1000,
                excluded_tags=[
                    "nav",
                    "header",
                    "footer",
                    "aside",
                    "script",
                    "style",
                    "noscript",
                ],
                excluded_selector=(
                    ".nav, .navbar, .menu, .sidebar, .footer, "
                    '.ad, .advertisement, [class*="cookie"], [class*="popup"]'
                ),
                wait_for_images=False,
                verbose=False,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
                if not result.success:
                    return ""
                # 将 crawl4ai 返回的 Markdown 转换为纯文本后提取句子
                md = result.markdown or ""
                # 去掉 Markdown 语法符号和链接
                clean = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", md)  # 图片
                clean = re.sub(r"\[[^\]]*\]\([^\)]*\)", "", clean)  # 链接
                clean = re.sub(r"[#*>_`~]", "", clean)
                clean = re.sub(r"https?://\S+", "", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                sentences = _split_sentences(clean)
                return " ".join(_ensure_end(s) for s in sentences[:3])

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_crawl())
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"crawl4ai enrich failed [{url}]: {e}")
    return ""


def get_enriched_content(
    url: str,
    title: str = "",
    category: str = "",
    use_crawl4ai: bool = False,
    timeout: int = 8,
) -> str:
    """
    智能入口：优先 HTTP 快速路径；JS 密集站点或指定时走 crawl4ai。

    Parameters
    ----------
    url          : 文章 URL
    title        : 文章标题（供日志用）
    category     : 分类标签
    use_crawl4ai : 强制使用 crawl4ai（适合产品/经济类复杂页面）
    timeout      : HTTP 超时秒数（crawl4ai 固定 30 秒）

    Returns
    -------
    str — 前 3 句拼接，或 '' （获取失败）
    """
    if not url or _is_blocked(url):
        return ""

    use_heavy = use_crawl4ai or _is_js_heavy(url)

    if use_heavy:
        logger.debug(f"crawl4ai 路径: {url}")
        result = enrich_content_crawl4ai(url, timeout=30)
    else:
        logger.debug(f"HTTP 路径: {url}")
        result = enrich_content_http(url, timeout=timeout)
        # HTTP 失败或内容太短，回退到 crawl4ai
        if not result or len(result) < 30:
            logger.debug(f"HTTP 路径不足，回退 crawl4ai: {url}")
            result = enrich_content_crawl4ai(url, timeout=30)

    if result:
        logger.info(f"  ✓ 内容增强 [{category}] ({len(result)}字): {title[:40]}")
    else:
        logger.debug(f"  ✗ 内容增强失败: {title[:40]}")
    return result
