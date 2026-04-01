import scrapers_military

s = scrapers_military.TWZScraper()
print(s.scrape_articles())
s2 = scrapers_military.MilitaryComScraper()
print(s2.scrape_articles())
