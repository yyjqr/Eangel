import military_spider
w = military_spider.TWZWrapperScraper()
try:
    print(w.scrape())
except Exception as e:
    import traceback
    traceback.print_exc()
