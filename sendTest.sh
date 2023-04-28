#!/bin/bash
## 0830 test
cd pySpider/searchOpt
echo "search valueable info"
mkdir techNews
#python techAI_searchValueOpt.py
python techRank_DB_opt.py 
#echo "search mil news"
#python spider_TechMili_Drive_OPT_V1.8.py
