##! /bin/bash
#GET Current time
time=$(date "+%Y-%m-%d_%H:%M:%S")
echo $time


## ADD news to mysql 数据库
cd  ~/valueSearch/crawler
## 对网页是否可访问做判断

#python3 techAI_value-rank-DB-valid.py
#python3 main-spider2.py

python3  ~/valueSearch/value-test2026/crawler/military-spider.py
exit 0
