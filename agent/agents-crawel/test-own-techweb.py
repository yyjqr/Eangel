import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        # 增加超时时间，并跳过缓存测试
        result = await crawler.arun(
            url="http://8.134.192.249:58888/",
            bypass_cache=True
        )

        if result.success:
            print("✅ 爬取成功！内容预览：")
            print(result.markdown[:500]) # 打印前500个字符
        else:
            print(f"❌ 爬取失败，错误原因: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
