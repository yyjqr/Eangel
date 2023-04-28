import scrapy
from bs4 import BeautifulSoup

class ExampleSpider(scrapy.Spider):
    name = "example"
    allowed_domains = ["aitopics.org"]
    start_urls = ["http://aitopics.org/"]
    #kRankLevelValue = 0.6
    def __init__(self):  ## ADD 0214
        self.NewsList = []
    def parse(self, response):
        page = response.url.split("/")[-2]
        print("page={0}".format(page))
        print("test Parse")
        filename = 'get_page_%s.html' %page
        with open(filename, 'wb') as f:
            f.write(response.body)
        self.log('Saved file %s(MISSING' %filename)
        soup = BeautifulSoup(response.body, "html.parser")
        newsIndex =0
        kRankLevelValue =0.6
        print("first test soup")
        for news in soup.select('.searchtitle   a'):
            print("test soup")
            #if findValuedInfoInNews(news.text,array):
            #curent_news_rank =findValuedInfoRank(news.text,KEYWORDS_RANK_MAP)
            curent_news_rank =0.7
            if curent_news_rank > kRankLevelValue :
               tittle=news.text
               print(news.text)
               for string in news.stripped_strings:
                #article.append(tittle.strip())   #strip去处多余空格
                    newsUrl=news.attrs['href']
                #article.append(url.strip())
                    print(newsUrl)
