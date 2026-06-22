import os
import json
import asyncio
import smtplib
import ssl
import hashlib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, TypedDict

import chromadb
import pymysql
from crawl4ai import AsyncWebCrawler
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

import encrypt_and_verify_url

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

_FALLBACK_KEYWORDS_WEIGHTS = {
      "technologies": 0.45,
    "technology": 0.3,
    "chip": 1,
    "risc": 0.8,
    "5G": 1,
    "6G": 1,
    "Robot": 1,
    "robot": 1,
    "science": 1,
    "dataset": 0.5,
    "COVID": 1,
    "Digital": 0.8,
    "AI": 0.9,
    "chatGPT": 0.85,
    "openAI": 0.4,
    "gemini": 0.8,
    "dall-E": 0.8,
    "transformer": 0.7,
    "DEEPMIND": 0.8,
    "lama": 0.5,
    "generative": 0.4,
    "claude": 0.6,
    "copliot": 0.7,
    "IOT": 0.6,
    "ML": 0.8,
    "machine learning": 1,
    "Artificial Intelligence (AI)": 1,
    "AGI": 1.2,
    "ai": 0.2,
    "Machine Learning": 1,
    "Deep Learning": 1,
    "AI Ethics": 0.6,
    "prompts": 0.5,
    "networks": 0.3,
    "neural": 0.4,
    "predicting": 0.3,
    "economic": 0.2,
    "rebuild": 0.2,
    "security": 0.3,
    "IoT (Internet of Things)": 0.8,
    "v2x": 1,
    "auto": 0.6,
    "autonomous": 1.2,
    "system": 0.6,
    "deep learning": 1,
    "light": 0.8,
    "sun": 0.6,
    "electric": 0.7,
    "electronic": 0.7,
    "big data": 0.5,
    "energy": 0.8,
    "clean energy": 0.9,
    "green": 0.6,
    "carbon": 0.8,
    "low carbon": 1,
    "Climate Change": 0.8,
    "percepition": 0.7,
    "multi-sensor": 0.8,
    "end to end": 1,
    "attention": 0.5,
    "deep": 0.3,
    "efficient": 0.3,
    "covid-19": 0.8,
    "SARS-CoV-2": 0.9,
    "flu": 0.7,
    "unmanned": 0.8,
    "NASA": 0.8,
    "MIT": 0.7,
    "DARPA": 0.6,
    "Apple": 0.6,
    "Google": 0.6,
    "USA": 0.3,
    "Russia": 0.3,
    "Taiwan": 0.4,
    "south China": 0.4,
    "market": 0.6,
    "stock market": 0.9,
    "Digital Marketing": 0.7,
    "Social Media Marketing": 0.6,
    "Autonomous Vehicles": 1,
    "robotaxi": 1,
    "Tesla": 0.7,
    "Digital & Health Tech": 1,
    "Cloud & Edge Computing": 1,
    "Smart Cities": 1,
    "Chatbots": 0.7,
    "human robot": 0.8,
    "cybersecurity": 0.7,
    "The Future of Work": 0.8,
    "Sustainablity": 0.8,
    "plane": 0.7,
    "Drone": 0.5,
    "art": 0.4,
    "design": 0.8,
    "quantum": 0.8,
    "Quantum Computing": 1,
    "humanoid robot": 1.3,
    "人形机器人": 1.3,
    "industrial robot": 1.1,
    "工业机器人": 1.1,
    "service robot": 1.0,
    "服务机器人": 1.0,
    "smart hardware": 1.1,
    "智能硬件": 1.1,
    "smart home": 0.9,
    "智能家居": 0.9,
    "wearable": 1.0,
    "可穿戴设备": 1.0,
    "smartwatch": 0.9,
    "智能手表": 0.9,
    "EV": 1.2,
    "electric vehicle": 1.2,
    "电动汽车": 1.2,
    "新能源汽车": 1.2,
    "self-driving": 1.2,
    "无人驾驶": 1.2,
    "vehicle": 0.7,
    "汽车": 0.7,
    "automotive": 0.8,
    "VR": 1.1,
    "virtual reality": 1.1,
    "虚拟现实": 1.1,
    "VR headset": 1.2,
    "VR眼镜": 1.2,
    "AR": 1.0,
    "augmented reality": 1.0,
    "增强现实": 1.0,
    "XR": 1.0,
    "混合现实": 1.0,
    "Vision Pro": 1.2,
    "Quest": 1.0,
    "metaverse": 0.9,
    "元宇宙": 0.9,
    "UAV": 0.7,
    "radar": 0.4,
    "雷达": 0.4,
    "satellite": 1.0,
    "卫星": 1.0,
    "space": 0.9,
    "航天": 1.0,
    "aerospace": 1.0,
    "航空航天": 1.0,

    "Mazda Carbon": 1.5,
    "Tesla Recall": 2.0,
    "F-35": 1.2,
    "DeepSeek": 1.8
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), ".", "tech_key_config_map.json")


def _load_rank_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as cfg_f:
            return json.load(cfg_f)
    except FileNotFoundError:
        print(f"[WARN] 未找到配置文件，使用内置权重: {CONFIG_PATH}")
    except Exception as exc:
        print(f"[WARN] 读取配置文件失败，使用内置权重: {exc}")
    return {}


RANK_CONFIG = _load_rank_config()
KEYWORDS_WEIGHTS = RANK_CONFIG.get("KEYWORDS_RANK_MAP", _FALLBACK_KEYWORDS_WEIGHTS)

_CRAWL_TIMEOUT = 120000
_CRAWL_RETRIES = 2
_CRAWL_DELAY = 3
_ANALYSIS_SOURCE_MAX_CHARS = int(RANK_CONFIG.get("ANALYSIS_SOURCE_MAX_CHARS", 6000))
_ANALYSIS_MAX_ITEMS_PER_SOURCE = int(RANK_CONFIG.get("ANALYSIS_MAX_ITEMS_PER_SOURCE", 4))
_ANALYSIS_RECENT_DAYS = int(RANK_CONFIG.get("ANALYSIS_RECENT_DAYS", 180))
_PROMPT_KEYWORD_LIMIT = int(RANK_CONFIG.get("PROMPT_KEYWORD_LIMIT", 80))
_DUPLICATE_DISTANCE_THRESHOLD = 0.35
_ALERT_SCORE_THRESHOLD = float(RANK_CONFIG.get("ALERT_SCORE_THRESHOLD", 3.0))
_CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
_CURRENT_YEAR = datetime.now().year


class AgentState(TypedDict, total=False):
    urls: List[str]
    raw_markdown: str
    analyzed_data: List[dict]
    alert_queue: list
    stored_news: List[dict]
    duplicate_news: List[dict]


chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="milit_tech_memory")


def _build_llm() -> ChatOpenAI:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    assert api_key, "DASHSCOPE_API_KEY 环境变量未设置！"
    return ChatOpenAI(
        model="qwen3-max-2025-09-23",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key
    )


def _get_event_score(event: dict):
    score = event.get("risk_score")
    if score is None:
        score = event.get("score")
    if score is None:
        return None
    try:
        return round(float(score), 2)
    except (TypeError, ValueError):
        return None


def _get_event_url(event: dict) -> str:
    url = event.get("url") or event.get("source_url") or ""
    return url.strip() if isinstance(url, str) else ""


def _short_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _build_keyword_hint(keyword_weights: dict, top_n: int = _PROMPT_KEYWORD_LIMIT) -> str:
    ranked_keywords = []
    for keyword, weight in keyword_weights.items():
        try:
            ranked_keywords.append((keyword, float(weight)))
        except (TypeError, ValueError):
            continue

    ranked_keywords.sort(key=lambda item: item[1], reverse=True)
    return ", ".join(f"{keyword}:{weight:g}" for keyword, weight in ranked_keywords[:top_n])


def _split_source_blocks(raw_text: str) -> List[dict]:
    pattern = re.compile(r"--- Source URL: (.*?) ---\n")
    matches = list(pattern.finditer(raw_text))
    if not matches:
        return [{"source_url": "", "content": raw_text.strip()}] if raw_text.strip() else []

    blocks = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        content = raw_text[start:end].strip()
        content = re.sub(r"\n---\s*$", "", content).strip()
        if content:
            blocks.append({
                "source_url": match.group(1).strip(),
                "content": content,
            })
    return blocks


def _prepare_source_excerpt(source_url: str, source_content: str) -> str:
    article_patterns = [
        re.compile(r'https://www\.popularmechanics\.com/[^")\s]*/a\d+/[^")\s]+'),
        re.compile(r'https://www\.twz\.com/(?!category/|latest/?$|tag/|wp-content/|author/|page/)[^")\s]+'),
        re.compile(r"https://(?:mil|news)\.ifeng\.com/c/[A-Za-z0-9]+"),
    ]
    noise_tokens = (
        "Newsletter",
        "Subscribe",
        "Privacy Notice",
        "Terms Of Use",
        "Skip to Content",
        "My Bookmarks",
        "Follow",
        "Visual Stories",
        "Promotions",
        "Show More...",
        "Search for:",
    )

    start_index = 0
    for pattern in article_patterns:
        match = pattern.search(source_content)
        if match:
            start_index = max(0, match.start() - 300)
            break

    excerpt = source_content[start_index:]
    cleaned_lines = []
    for line in excerpt.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(token in stripped for token in noise_tokens):
            continue
        cleaned_lines.append(stripped)

    cleaned_excerpt = "\n".join(cleaned_lines).strip()
    if cleaned_excerpt:
        return cleaned_excerpt[:_ANALYSIS_SOURCE_MAX_CHARS]
    return source_content[start_index:start_index + _ANALYSIS_SOURCE_MAX_CHARS]


def _merge_events(events: List[dict]) -> List[dict]:
    merged_events = []
    seen_keys = set()
    for event in events:
        event_url = _get_event_url(event)
        title = str(event.get("title", "")).strip().lower()
        dedupe_key = event_url.lower() if event_url else title
        if not dedupe_key or dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged_events.append(event)
    return merged_events


def _parse_events(content: str, source_url: str = "") -> List[dict]:
    cleaned = content.replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned)
    if isinstance(data, dict):
        data = data.get("events") or data.get("items") or []
    if not isinstance(data, list):
        return []

    normalized_events = []
    for item in data:
        if not isinstance(item, dict):
            continue
        normalized_item = dict(item)
        normalized_item["source_url"] = (normalized_item.get("source_url") or source_url or "").strip()
        normalized_item["url"] = _get_event_url(normalized_item) or normalized_item["source_url"]
        publish_date = normalized_item.get("publish_date") or ""
        normalized_item["publish_date"] = publish_date.strip() if isinstance(publish_date, str) else ""
        normalized_events.append(normalized_item)
    return normalized_events


def _print_event_group(label: str, events: List[dict], max_items: int = 10):
    print(f"{label}: {len(events)} 条")
    for idx, event in enumerate(events[:max_items], 1):
        title = event.get("title", "Unknown")
        score = _get_event_score(event)
        category = event.get("category", "-") or "-"
        score_text = "-" if score is None else score
        print(f"  {idx}. {title} | score={score_text} | category={category}")

        event_url = _get_event_url(event)
        source_url = event.get("source_url", "") or ""
        if event_url:
            print(f"     网页: {event_url}")
        if source_url and source_url != event_url:
            print(f"     来源页: {source_url}")

        publish_date = event.get("publish_date", "") or ""
        if publish_date:
            print(f"     日期: {publish_date}")

        summary = _short_text(event.get("summary", ""))
        if summary:
            print(f"     摘要: {summary}")
    if len(events) > max_items:
        print(f"  ... 其余 {len(events) - max_items} 条省略")


async def _fetch_url(crawler, url: str) -> str:
    """带重试的单 URL 爬取，返回带来源标记的 markdown 或空字符串。"""
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
                return f"--- Source URL: {url} ---\n{result.markdown}\n---\n"
            print(f"[WARN] attempt {attempt}/{_CRAWL_RETRIES} failed for {url}: {result.error_message}")
        except Exception as exc:
            print(f"[WARN] attempt {attempt}/{_CRAWL_RETRIES} exception for {url}: {exc}")
        if attempt < _CRAWL_RETRIES:
            await asyncio.sleep(_CRAWL_DELAY)
    print(f"[SKIP] {url} 爬取失败，已跳过。")
    return ""


async def crawl_node(state: AgentState):
    urls = state.get("urls", [])
    if not urls:
        return {"raw_markdown": ""}

    async with AsyncWebCrawler(verbose=False) as crawler:
        tasks = [_fetch_url(crawler, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    all_content = [content for content in results if content]
    print(f"抓取完成，可分析来源页 {len(all_content)} 个。")
    return {"raw_markdown": "\n".join(all_content)}


def analyze_node(state: AgentState):
    raw_text = state.get("raw_markdown", "")
    if not raw_text or len(raw_text) < 200:
        return {"analyzed_data": [], "alert_queue": []}

    source_blocks = _split_source_blocks(raw_text)
    if not source_blocks:
        return {"analyzed_data": [], "alert_queue": []}

    llm = _build_llm()
    keyword_hint = _build_keyword_hint(KEYWORDS_WEIGHTS)
    all_events = []

    for block in source_blocks:
        source_url = block["source_url"]
        source_content = _prepare_source_excerpt(source_url, block["content"])
        prompt = f"""
        今天是 {_CURRENT_DATE}。
        你是一个科技、产品与军事新闻编辑。
        输入内容仅来自一个来源页的顶部区域，页面通常按“最新”或“最重要”排序。
        来源页：{source_url}
        关键词权重提示（节选）：{keyword_hint}

        任务要求：
        1. 只从输入内容中明确出现的标题、链接、摘要提取新闻，不允许使用页面外知识补全，也不要从模型记忆里补旧闻。
        2. 覆盖三大类：科技产业、产品与消费电子/汽车/机器人、军事与防务科技。
        3. 优先提取最近 {_ANALYSIS_RECENT_DAYS} 天内，尤其是 {_CURRENT_YEAR} 年和最近几个月的新闻；页面顶部条目优先。
        4. 如果页面没有明确日期，也可以根据栏目页顶部顺序保留明显属于当前栏目新闻流的条目；不要因为缺少日期就漏掉科技、产品或军事新闻。
        5. 如果同时出现旧闻回顾、年度总结、历史盘点和近期新闻，优先近期新闻，不要只抓 2025 或更早的旧文章。
        6. 过滤广告、导购、榜单、纯评测、观点专栏、图库、视频页、专题汇总、无明确事件的内容。
        7. category 仅从以下标签中选择最合适的一个：科技、产品、汽车、机器人、芯片/AI、能源/航天、军事。
        8. score 范围为 0.0 到 5.0；重大产品发布、召回、量产、融资、监管事件、军工突破、试飞、订单、部署，可适当提高分数。
        9. url 必须填写具体文章链接；找不到具体文章链接时，才回退为 source_url。
        10. source_url 固定填写来源页 URL。
        11. publish_date 只有在输入内容明确出现日期时才填写，格式为 YYYY-MM-DD 或 YYYY-MM，否则填空字符串。
        12. 最多返回 {_ANALYSIS_MAX_ITEMS_PER_SOURCE} 条。

        只输出 JSON 列表，不要 Markdown，不要解释。
        输出格式：
        [{{"title": "标题", "category": "科技", "score": 2.5, "summary": "简要摘要", "url": "https://...", "source_url": "{source_url}", "publish_date": "", "critical": false}}]

        内容如下：
        {source_content}
        """

        try:
            response = llm.invoke(prompt)
            content = response.content if isinstance(response.content, str) else str(response.content)
            block_events = _parse_events(content, source_url=source_url)
            all_events.extend(block_events)
            print(f"[ANALYZE] {source_url or '-'} -> 提取 {len(block_events)} 条候选")
        except Exception as exc:
            print(f"❌ 分析来源页失败: {source_url or '-'}: {exc}")

    events = _merge_events(all_events)

    alert_candidates = [
        event for event in events
        if bool(event.get("critical")) or ((_get_event_score(event) or 0) >= _ALERT_SCORE_THRESHOLD)
    ]
    _print_event_group("候选有效新闻", events)
    return {"analyzed_data": events, "alert_queue": alert_candidates}


def storage_node(state: AgentState):
    events = state.get("analyzed_data", [])
    raw_alerts = state.get("alert_queue", [])
    final_alert_msgs = []
    stored_news = []
    duplicate_news = []

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for event in events:
        title = event.get("title", "Unknown")
        summary = event.get("summary", "")
        score = _get_event_score(event)
        if score is None:
            score = 0

        category = event.get("category", "")
        author = event.get("author", "")
        event_url = _get_event_url(event)
        source_url = event.get("source_url", "") or ""
        publish_date = event.get("publish_date", "") or ""
        news_item = {
            "title": title,
            "summary": summary,
            "score": score,
            "category": category,
            "url": event_url,
            "source_url": source_url,
            "publish_date": publish_date,
        }

        if not summary.strip():
            print(f"[SKIP] 缺少摘要，跳过入库: {title[:20]}...")
            continue

        search_res = collection.query(query_texts=[summary], n_results=1)
        distances = search_res.get("distances") or []
        first_distance = None
        if distances:
            if isinstance(distances[0], list):
                if distances[0]:
                    first_distance = distances[0][0]
            else:
                first_distance = distances[0]

        # Distance 越小越相似。0.35 是一个比较严苛的阈值，防止重复预警
        is_duplicate = False
        if first_distance is not None and first_distance < _DUPLICATE_DISTANCE_THRESHOLD:
            is_duplicate = True
            duplicate_news.append(news_item)
            print(f"⏭️ 发现语义重复，跳过: {title[:20]}... | 网页: {event_url or source_url or '-'}")

        if not is_duplicate:
            collection.add(
                documents=[summary],
                metadatas=[{
                    "title": title,
                    "score": score,
                    "url": event_url,
                    "source_url": source_url,
                    "publish_date": publish_date,
                }],
                ids=[hashlib.md5((title + summary).encode()).hexdigest()]
            )

            try:
                sql = """
                    INSERT IGNORE INTO techTB(Id, Rate, title, author, publish_time, content, url, key_word)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
                """
                publish_time = publish_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(sql, (None, score, title, author, publish_time, summary, event_url, category))
                conn.commit()
                if cursor.rowcount:
                    stored_news.append(news_item)
                else:
                    duplicate_news.append(news_item)
                    print(f"⏭️ 数据库标题重复，跳过: {title[:20]}... | 网页: {event_url or source_url or '-'}")
                    continue
            except Exception as exc:
                print(f"写入数据库失败: {exc}")
                continue

            should_alert = any(isinstance(item, dict) and item.get("title") == title for item in raw_alerts)
            if not should_alert:
                should_alert = bool(event.get("critical")) or score >= _ALERT_SCORE_THRESHOLD

            if should_alert:
                alert_text = (
                    f"🚨 【高风险预警 ({score})】\n"
                    f"标题: {title}\n"
                    f"网页: {event_url or source_url or '-'}\n"
                    f"摘要: {summary}"
                )
                final_alert_msgs.append(alert_text)

    cursor.close()
    conn.close()
    return {
        "alert_queue": final_alert_msgs,
        "stored_news": stored_news,
        "duplicate_news": duplicate_news,
    }


def send_alert_email(content_list):
    if not content_list:
        return

    full_content = "\n\n".join(content_list)
    sender = EMAIL_CONFIG["sender"]
    subject = f"🚀 Jetson AI 自动预警 ({datetime.now().strftime('%m-%d')})"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = EMAIL_CONFIG["receiver"]
    msg.attach(MIMEText(full_content, "plain", "utf-8"))

    print(f"send subject {subject}")

    _pwd = encrypt_and_verify_url.decrypt_getKey(EMAIL_CONFIG["token"].encode("utf-8"))

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp"], 465, context=context)
    try:
        server.login(sender, _pwd.decode("utf-8"))
        server.sendmail(sender, [EMAIL_CONFIG["receiver"]], msg.as_string())
    finally:
        server.quit()


workflow = StateGraph(AgentState)
workflow.add_node("crawler", crawl_node)
workflow.add_node("analyzer", analyze_node)
workflow.add_node("storage", storage_node)

workflow.set_entry_point("crawler")
workflow.add_edge("crawler", "analyzer")
workflow.add_edge("analyzer", "storage")
workflow.add_edge("storage", END)

app = workflow.compile()


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "urls_config.json")
    with open(config_path, "r", encoding="utf-8") as file_obj:
        url_cfg = json.load(file_obj)

    initial_state = {"urls": url_cfg["urls"]}
    final_state = asyncio.run(app.ainvoke(initial_state))

    analyzed_data = final_state.get("analyzed_data", [])
    stored_news = final_state.get("stored_news", [])
    duplicate_news = final_state.get("duplicate_news", [])

    print(
        f"执行完成：候选 {len(analyzed_data)} 条，新增 {len(stored_news)} 条，"
        f"重复跳过 {len(duplicate_news)} 条。"
    )

    if stored_news:
        _print_event_group("本次新增有效新闻", stored_news)
    else:
        print("本次没有新增有效新闻。")

    if duplicate_news:
        _print_event_group("本次重复新闻", duplicate_news)
    else:
        print("本次没有重复新闻。")

    if final_state.get("alert_queue"):
        send_alert_email(final_state["alert_queue"])
        print(f"✅ 任务完成，发送了 {len(final_state['alert_queue'])} 条预警。")
    else:
        print("本次无高风险预警。")
