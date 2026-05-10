import asyncio
import re
import ssl
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


TARGET_URL = "https://www.mckinsey.com/featured-insights/artificial-intelligence"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def extract_text_from_html(html: str) -> str:
    patterns = [
        r"<article\b[^>]*>(.*?)</article>",
        r"<main\b[^>]*>(.*?)</main>",
        r"<body\b[^>]*>(.*?)</body>",
    ]
    content = html
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1)
            break

    content = re.sub(
        r"<(script|style|noscript|svg|iframe|form|button)\b[^>]*>.*?</\1>",
        " ",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content = re.sub(r"<[^>]+>", " ", content)
    content = unescape(content)
    content = re.sub(r"\s+", " ", content).strip()
    return content


def fetch_with_http_fallback(url: str, timeout: int = 20) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="ignore")
    return extract_text_from_html(html)


async def crawl_with_browser(
    label: str,
    browser_type: str,
    use_managed_browser: bool,
    enable_stealth: bool,
    extra_args: list[str],
) -> str:
    browser_config = BrowserConfig(
        browser_type=browser_type,
        headless=True,
        use_managed_browser=use_managed_browser,
        enable_stealth=enable_stealth,
        ignore_https_errors=True,
        viewport_width=1280,
        viewport_height=800,
        user_agent=USER_AGENT,
        extra_args=extra_args,
    )

    run_config = CrawlerRunConfig(
        wait_until="domcontentloaded",
        wait_for="css:body",
        delay_before_return_html=8,
        page_timeout=90000,
        magic=True,
        simulate_user=True,
        override_navigator=True,
        remove_overlay_elements=True,
        verbose=False,
    )

    print(f"[{label}] 开始浏览器抓取")
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=TARGET_URL, config=run_config)
    except Exception as exc:
        print(f"[{label}] 浏览器异常: {exc}")
        return ""

    if result.success and result.markdown:
        print(f"[{label}] 浏览器抓取成功")
        return result.markdown

    print(f"[{label}] 浏览器抓取失败: {result.error_message}")
    return ""


async def main():
    browser_attempts = [
        {
            "label": "firefox-dedicated",
            "browser_type": "firefox",
            "use_managed_browser": False,
            "enable_stealth": False,
            "extra_args": [],
        },
        {
            "label": "chromium-dedicated",
            "browser_type": "chromium",
            "use_managed_browser": False,
            "enable_stealth": True,
            "extra_args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-http2",
            ],
        },
        {
            "label": "chromium-managed",
            "browser_type": "chromium",
            "use_managed_browser": True,
            "enable_stealth": True,
            "extra_args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-http2",
            ],
        },
    ]

    for attempt in browser_attempts:
        content = await crawl_with_browser(**attempt)
        if content:
            print("【抓取成功】")
            print(content[:500])
            return

    print("[http-fallback] 开始 HTTP 备用抓取")
    try:
        content = fetch_with_http_fallback(TARGET_URL)
    except HTTPError as exc:
        print(f"【抓取失败】HTTP 备用路径返回 {exc.code}: {exc.reason}")
        return
    except URLError as exc:
        print(f"【抓取失败】HTTP 备用路径网络异常: {exc.reason}")
        return
    except Exception as exc:
        print(f"【抓取失败】HTTP 备用路径异常: {exc}")
        return

    if content:
        print("【HTTP备用抓取成功】")
        print(content[:500])
        return

    print("【抓取失败】所有抓取路径都未获取到有效内容")


if __name__ == "__main__":
    asyncio.run(main())