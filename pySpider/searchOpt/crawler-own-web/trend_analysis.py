import pymysql
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os
import json

def get_db_connection():
    return pymysql.connect(
        host='localhost', user='robot', password='robot', database='techNews', charset='utf8mb4'
    )

class TrendAnalyzer:
    def __init__(self):
        self.CATEGORIES = {
            "Large Models (LLM)": {
                "keywords": ["llm", "large language model", "gpt", "claude", "deepseek", "gemini", "llama", "大模型", "generative ai", "sora", "o1", "r1"],
                "label": "大模型"
            },
            "AI (General)": {
                "keywords": ["ai", "artificial intelligence", "machine learning", "neural network", "computervision", "deep learning", "人工智能"],
                "label": "通用AI"
            },
            "Robotics": {
                "keywords": ["robot", "humanoid", "unitree", "boston dynamics", "optimus", "figure ai", "robotics", "机器人", "人形机器人"],
                "label": "机器人"
            },
            "Autonomous Driving": {
                "keywords": ["autonomous", "self-driving", "waymo", "pony.ai", "tesla fsd", "evtol", "flying car", "无人驾驶", "自动驾驶", "飞行汽车"],
                "label": "自动驾驶"
            },
            "Communication (5G/6G)": {
                "keywords": ["5g", "6g", "v2x", "iot", "satellite", "starlink", "huawei", "communication", "terahertz", "通讯", "物联网"],
                "label": "通讯技术"
            },
            "Biotech": {
                "keywords": ["biotech", "virus", "pharma", "drug", "crispr", "medicine", "vaccine", "biology", "生物技术", "制药", "基因"],
                "label": "生物技术"
            },
            "Energy": {
                "keywords": ["energy", "nuclear fusion", "solar", "battery", "lithium", "grid", "electricity", "renewable", "fusion power", "tokamak", "能源", "核聚变", "新能源"],
                "label": "能源科技"
            },
            "Digital Tech": {
                "keywords": ["vr", "ar", "xr", "metaverse", "digital twin", "digital payment", "crypto", "blockchain", "bitcoin", "web3", "vision pro", "数字孪生", "虚拟现实"],
                "label": "数字技术"
            },
            "Economy": {
                "keywords": ["economy", "tariff", "trade war", "rate cut", "fed", "inflation", "gdp", "geopolitics", "stock market", "nasdaq", "经济", "关税", "降息"],
                "label": "宏观经济"
            }
        }

    def analyze(self):
        monthly_data = defaultdict(lambda: {cat: {'score': 0.0, 'keywords': Counter()} for cat in self.CATEGORIES})
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT title, Rate, category, publish_time FROM techTB WHERE publish_time >= '2024-01-01'"
            cursor.execute(query)
            rows = cursor.fetchall()

            count_matched = 0
            for title, rate, db_cat, publish_time in rows:
                if not title or not publish_time or len(publish_time) < 10: continue

                try:
                    dt_str = publish_time[:10]
                    dt = datetime.strptime(dt_str, '%Y-%m-%d')
                    base_dt = datetime(2024, 1, 1)
                    diff_days = (dt - base_dt).days
                    if diff_days < 0: continue

                    # 2-day bins
                    bin_dt = base_dt + timedelta(days=(diff_days // 2) * 2)
                    time_key = bin_dt.strftime('%Y-%m-%d')
                except: continue

                title_lower = str(title).lower()
                for cat_key, cat_info in self.CATEGORIES.items():
                    # Check each keyword
                    found_kws = []
                    for kw in cat_info['keywords']:
                        if kw in title_lower:
                            found_kws.append(kw)

                    if found_kws:
                        count_matched += 1
                        val = float(rate if rate else 1.0)
                        if val > 10: val = 5.0 + (val/10)
                        monthly_data[time_key][cat_key]['score'] += val
                        for mk in found_kws:
                            monthly_data[time_key][cat_key]['keywords'][mk] += 1

            sorted_times = sorted(monthly_data.keys())

            global_max = 0
            for t in sorted_times:
                for cat in self.CATEGORIES:
                    s = monthly_data[t][cat]['score']
                    if s > global_max: global_max = s
            if global_max == 0: global_max = 1

            chart_series = []
            for cat_key, cat_info in self.CATEGORIES.items():
                series_data = []
                for t_key in sorted_times:
                    m_cat_data = monthly_data[t_key][cat_key]
                    raw_score = m_cat_data['score']
                    norm_score = round((raw_score / global_max) * 100, 1)
                    top_kws = m_cat_data['keywords'].most_common(3)
                    top_events_str = ", ".join([f"{k}" for k, v in top_kws])
                    series_data.append({
                        "value": norm_score,
                        "meta": {"raw": round(raw_score, 1), "events": top_events_str if top_events_str else "无显著事件"},
                        "month": t_key
                    })
                chart_series.append({
                    "name": cat_info['label'],
                    "type": "line", "smooth": True, "symbol": "circle", "symbolSize": 4,
                    "data": series_data
                })

            final_json = {"months": sorted_times, "series": chart_series}
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_data.json")
            with open(json_path, "w", encoding='utf-8') as f:
                json.dump(final_json, f, ensure_ascii=False, indent=2)

            print(f"Analysis complete. RowCount={len(rows)} MatchedCount={count_matched} Points={len(sorted_times)}")
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")
            return False

if __name__ == "__main__":
    TrendAnalyzer().analyze()
