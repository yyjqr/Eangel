import os
import json
import asyncio
import smtplib
import ssl
#import mysql.connector
import pymysql
import encrypt_and_verify_url
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from crawl4ai import AsyncWebCrawler
from langchain_openai import ChatOpenAI # 通过 DashScope 兼容

# --- 配置区 ---
DB_CONFIG = {
    "host": "localhost",
    "user": "robot",
    "password": "robot",
    "database": "techNews"
}

EMAIL_CONFIG = {
    "smtp": "smtp.qq.com",
    "sender": "840056598@qq.com",
    "token": "dm1wbmFmYmxsdnR0YmJlaQ==",   # 填入加密后的授权码密文
    "receiver": "840056598@qq.com"
}

# 之前分析得出的权重关键词
KEYWORDS_WEIGHTS = {
    "Mazda Carbon": 1.5,
    "Tesla Recall": 2.0,
    "F-35": 1.2,
    "DeepSeek": 1.8
}

# --- 状态定义 ---
class AgentState(TypedDict):
    urls: List[str]
    raw_markdown: str
    analyzed_data: List[dict]
    alert_queue: List[str]

# --- 节点 A: 深度爬取 ---
_CRAWL_TIMEOUT = 120000   # 毫秒，单页超时
_CRAWL_RETRIES = 2        # 失败后重试次数
_CRAWL_DELAY   = 3        # 重试间隔（秒）

async def _fetch_url(crawler, url: str) -> str:
    """带重试的单 URL 爬取，返回 markdown 或空字符串。"""
    for attempt in range(1, _CRAWL_RETRIES + 1):
        try:
            result = await crawler.arun(
                url=url,
                bypass_cache=True,
                page_timeout=_CRAWL_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            if result.success:
                print(f"[OK] {url}")
                return result.markdown + "\n---\n"
            print(f"[WARN] attempt {attempt}/{_CRAWL_RETRIES} failed for {url}: {result.error_message}")
        except Exception as exc:
            print(f"[WARN] attempt {attempt}/{_CRAWL_RETRIES} exception for {url}: {exc}")
        if attempt < _CRAWL_RETRIES:
            await asyncio.sleep(_CRAWL_DELAY)
    print(f"[SKIP] {url} 爬取失败，已跳过。")
    return ""

async def crawl_node(state: AgentState):
    async with AsyncWebCrawler(verbose=False) as crawler:
        tasks = [_fetch_url(crawler, url) for url in state['urls']]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        combined_md = "".join(results)
    return {"raw_markdown": combined_md}

# --- 节点 B: AI 过滤与权重分析 (Qwen-max) ---
def analyze_node(state: AgentState):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    assert api_key, "DASHSCOPE_API_KEY 环境变量未设置！"
    llm = ChatOpenAI(
        model="qwen3-max-2025-09-23",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key
    )

    prompt = f"""
    你是一个科技分析官。请从以下内容中提取关于“新车”和“飞行器/战斗机”的信息。
    参考权重关键词：{KEYWORDS_WEIGHTS}

    要求：
    1. 过滤无关广告和琐碎新闻。
    2. 如果涉及重大突破（如碳捕集）或重大负面（如召回），计算加权得分。
    3. 输出格式要求为 JSON 列表: [{{ "title": "...", "category": "...", "score": 9.5, "summary": "...", "critical": true }}]

    内容如下：
    {state['raw_markdown'][:10000]} # 截断防止溢出
    """
    response = llm.invoke(prompt)
    # 简单的清理逻辑
    import json
    try:
        data = json.loads(response.content.strip('```json').strip())
    except:
        data = []
    return {"analyzed_data": data}

# --- 节点 C: MariaDB 存储与邮件报警 ---
def storage_node(state: AgentState):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    alerts = []

    for item in state['analyzed_data']:
        # 存入数据库
        sql = """
            INSERT IGNORE INTO techTB(Id, Rate, title, author, publish_time, content, url, key_word)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
        """
        is_critical = item.get('critical', False)
        cursor.execute(sql, (
            None,
            item.get('score', 0),
            item.get('title', ''),
            item.get('author', ''),
            datetime.now(),
            item.get('summary', ''),
            item.get('url', ''),
            item.get('category', '')
        ))

        # 如果是重大动态，加入报警队列
        if is_critical or item['score'] >= 1.8:
            alerts.append(f"🔥 重大动态提醒：{item['title']}\n摘要：{item['summary']}")

    conn.commit()
    cursor.close()
    conn.close()
    return {"alert_queue": alerts}

# --- 辅助函数：发送邮件 ---
def send_alert_email(content_list):
    if not content_list: return
    full_content = "\n\n".join(content_list)
    sender = EMAIL_CONFIG['sender']
    subject = f"🚀 Jetson AI 自动预警 ({datetime.now().strftime('%m-%d')})"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = EMAIL_CONFIG['receiver']
    msg.attach(MIMEText(full_content, 'plain', 'utf-8'))

    print(f"send subject {subject}")

    # 解密授权码
    _pwd = encrypt_and_verify_url.decrypt_getKey(EMAIL_CONFIG['token'].encode('utf-8'))

    # 创建安全上下文（解决 SSL 验证问题）
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp'], 465, context=context)
    try:
        server.login(sender, _pwd.decode('utf-8'))
        server.sendmail(sender, [EMAIL_CONFIG['receiver']], msg.as_string())
    finally:
        server.quit()

# --- 构建图 ---
workflow = StateGraph(AgentState)
workflow.add_node("crawler", crawl_node)
workflow.add_node("analyzer", analyze_node)
workflow.add_node("storage", storage_node)

workflow.set_entry_point("crawler")
workflow.add_edge("crawler", "analyzer")
workflow.add_edge("analyzer", "storage")
workflow.add_edge("storage", END)

app = workflow.compile()

# --- 运行入口 ---
if __name__ == "__main__":
    _config_path = os.path.join(os.path.dirname(__file__), "urls_config.json")
    with open(_config_path, "r", encoding="utf-8") as _f:
        _url_cfg = json.load(_f)
    initial_state = {
        "urls": _url_cfg["urls"]
    }
    # 异步执行
    final_state = asyncio.run(app.ainvoke(initial_state))

    # 触发报警
    if final_state['alert_queue']:
        send_alert_email(final_state['alert_queue'])
        print(f"✅ 任务完成，发送了 {len(final_state['alert_queue'])} 条预警。")
