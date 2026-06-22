import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    # 1. 针对 Jetson 的深度浏览器配置
    browser_config = BrowserConfig(
        headless=True,
        # 启用隐身模式，模拟真人行为
        extra_args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage", # 解决内存不足导致的崩溃
            "--disable-gpu"
        ],
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # 2. 爬取运行配置
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=120000,  # 延长到 2 分钟，给 Jetson 留足渲染时间
        # 核心：开启“魔法模式”，自动处理反爬绕过
        magic_mode=True,
        word_count_threshold=10
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # 建议直接针对搜索结果页面，效率更高
        search_url = "https://www.twz.com/?s=Iran+Israel+USA"

        result = await crawler.arun(
            url=search_url,
            config=run_config
        )

        if result.success and result.markdown:
            print("✅ 抓取成功！正在调用 AI 分析...")
            # 这里接入你之前的 qwen-max 分析逻辑
            print(result.markdown[:1000])
        else:
            # 打印具体的错误详情
            print(f"❌ 抓取失败。错误详情: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
