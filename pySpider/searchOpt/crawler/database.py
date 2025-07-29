import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os

class TechNewsDB:
    def __init__(self, db_path="tech_news.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    title_zh TEXT,
                    url TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    summary_zh TEXT,
                    content TEXT,
                    source TEXT NOT NULL,
                    author TEXT,
                    tags TEXT,
                    publish_time DATETIME,
                    crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    views INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'crawled',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建爬取记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    total_crawled INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    error_message TEXT
                )
            ''')
            
            conn.commit()
            print("数据库初始化完成")
    
    def insert_article(self, article_data: Dict) -> Optional[int]:
        """插入文章数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查URL是否已存在
                cursor.execute("SELECT id FROM articles WHERE url = ?", (article_data['url'],))
                if cursor.fetchone():
                    print(f"文章已存在: {article_data['url']}")
                    return None
                
                cursor.execute('''
                    INSERT INTO articles 
                    (title, title_zh, url, summary, summary_zh, content, source, 
                     author, tags, publish_time, views, likes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article_data.get('title'),
                    article_data.get('title_zh'),
                    article_data.get('url'),
                    article_data.get('summary'),
                    article_data.get('summary_zh'),
                    article_data.get('content'),
                    article_data.get('source'),
                    article_data.get('author'),
                    article_data.get('tags'),
                    article_data.get('publish_time'),
                    article_data.get('views', 0),
                    article_data.get('likes', 0)
                ))
                
                article_id = cursor.lastrowid
                conn.commit()
                print(f"成功插入文章: {article_data['title'][:50]}...")
                return article_id
                
        except Exception as e:
            print(f"插入文章失败: {e}")
            return None
    
    def get_articles(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """获取文章列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM articles 
                    ORDER BY crawl_time DESC 
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                articles = []
                for row in cursor.fetchall():
                    articles.append(dict(row))
                
                return articles
                
        except Exception as e:
            print(f"获取文章失败: {e}")
            return []
    
    def get_article_count(self) -> int:
        """获取文章总数"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"获取文章数量失败: {e}")
            return 0
    
    def insert_crawl_record(self, source: str, total: int, success: int, error: int, status: str = "completed", error_msg: str = None):
        """插入爬取记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO crawl_records 
                    (source, total_crawled, success_count, error_count, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (source, total, success, error, status, error_msg))
                
                conn.commit()
                print(f"爬取记录已保存: {source} - 成功:{success}, 失败:{error}")
                
        except Exception as e:
            print(f"保存爬取记录失败: {e}")
    
    def get_crawl_stats(self) -> Dict:
        """获取爬取统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总文章数
                cursor.execute("SELECT COUNT(*) FROM articles")
                total_articles = cursor.fetchone()[0]
                
                # 今日爬取数
                cursor.execute('''
                    SELECT COUNT(*) FROM articles 
                    WHERE DATE(crawl_time) = DATE('now')
                ''')
                today_articles = cursor.fetchone()[0]
                
                # 按来源统计
                cursor.execute('''
                    SELECT source, COUNT(*) as count 
                    FROM articles 
                    GROUP BY source 
                    ORDER BY count DESC
                ''')
                source_stats = cursor.fetchall()
                
                return {
                    'total_articles': total_articles,
                    'today_articles': today_articles,
                    'source_stats': source_stats
                }
                
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

    def close(self):
        """关闭数据库连接"""
        pass  # SQLite 会自动管理连接 