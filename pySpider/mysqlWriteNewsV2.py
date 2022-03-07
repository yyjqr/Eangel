
import pymysql
import logging
import pandas as pd
 
HOST = 'localhost'   #数据库登录，使用ip，登录不进去
#USER = 'root'
USER = 'robot'
PASSWORD = 'robot'
PORT = 3306
#DATABASE = 'news_with_keyword'
DATABASE = 'techNews'
CHAREST = 'utf8'

 
global conn 
conn= pymysql.connect(host=HOST, user=USER, password=PASSWORD, port=PORT, database=DATABASE,
                          charset=CHAREST)
print("connect database status %s...",conn) 
#写入数据到数据库中
def writeDb(sql,db_data=()):
    """
    连接mysql数据库（写），并进行写的操作
    """
    try:
        #print("connect  database...")
        conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, port=PORT, database=DATABASE,
                          charset=CHAREST)
        #print(" local connect database status %s",conn)    
        cursor = conn.cursor()
    except Exception as e:
        print(e)
        logging.error('数据库连接失败:%s' % e)
        return False
 
    try:
        cursor.execute(sql, db_data)
        print ("id %d" %conn.insert_id())
        #print ("id %d" %cursor.lastrowid)        
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error('数据写入失败:%s' % e)
        return False
    finally:
        cursor.close()
        conn.close()
    return True
 
def getLastInsertId():
   print ("id %d" %conn.insert_id())
   return conn.insert_id()
 
sql = """ INSERT INTO techTB(Id,Rate,title,author,publish_time,content,url,key_word) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) """

#newsOne=('100', '1','DIGITAL EYE: The Human Brain-Scale AI Supercomputer Is Coming','Tony','2022-01', 'Barbare',
#  'https://www.danfiehn.com/post/digital-eye-how-ai-is-quietly-eating-up-the-workforce-with-job-automation-1', '5432.1')
#result = writeDb(sql, newsOne)

