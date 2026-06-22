## -*- coding: UTF-8 -*-
# @author: JACK YANG
# @desc:   ISP/嵌入式开发智能检索 Agent
#          基于 ChromaDB RAG + Qwen Function Calling
#          工具: query_chip_doc / query_3a_algorithm /
#               query_coding_standard / search_github_isp

import argparse
import json
import os
import hashlib
import requests

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

# ──────────────────────────────────────────────
# 默认配置
# ──────────────────────────────────────────────
BASE_DIR             = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH      = os.path.join(BASE_DIR, "my_chroma_db")
DEFAULT_DOCS_PATH    = os.path.join(BASE_DIR, "docs")
DEFAULT_MODEL_NAME   = "qwen3-max-2026-01-23"
DEFAULT_BASE_URL     = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_N_RESULTS    = 4
MAX_CONTEXT_BYTES    = 80000
MAX_DOC_BYTES        = 20000
TRUNCATION_NOTICE    = "\n...[内容已截断]"

# 领域 → collection 名称映射
DOMAIN_COLLECTIONS = {
    "chip":     "chip_sdk_docs",
    "isp":      "isp_sdk_docs",
    "3a":       "isp_sdk_docs",
    "camera":   "camera_chip_docs",
    "test":     "autotest_docs",
    "standard": "coding_standard_docs",
    "embedded": "embedded_linux_docs",
    "default":  "markdown_docs",
}

# 芯片厂商 → GitHub 搜索模板
# 说明：不加 language: 限制（仓库搜索建议宽松），{feature} 由调用方替换
VENDOR_QUERIES = {
    # 海思 HiSilicon
    "hisilicon": "hisilicon OR hi3519 OR hi3516 {feature}",
    "hisi":      "hisilicon OR hi3519 OR hi3516 {feature}",
    "海思":       "hisilicon OR hi3519 OR hi3516 {feature}",
    # 瑞芯微 Rockchip
    "rockchip":  "rockchip OR rkaiq OR rv1126 OR rk3588 {feature}",
    "瑞芯微":     "rockchip OR rkaiq OR rv1126 OR rk3588 {feature}",
    # Sony 传感器
    "sony":      "sony IMX OR imx678 OR imx585 {feature}",
    # 联发科 MediaTek
    "mediatek":  "mediatek OR MTK camera {feature}",
    "联发科":     "mediatek OR MTK camera {feature}",
    # 高通 Qualcomm
    "qualcomm":  "qualcomm OR snapdragon CAMX {feature}",
    "高通":       "qualcomm OR snapdragon CAMX {feature}",
    # 安霸 Ambarella
    "ambarella": "ambarella OR cv25 {feature}",
    "安霸":       "ambarella cv25 {feature}",
}

# 3A 算法类型关键词
ALGO_KEYWORDS = {
    "ae":  ["auto exposure", "AE algorithm", "exposure control", "曝光", "亮度收敛"],
    "af":  ["auto focus", "AF algorithm", "CDAF", "PDAF", "lens VCM", "对焦"],
    "awb": ["auto white balance", "AWB", "color temperature", "CCM", "白平衡", "色温"],
    "nr":  ["noise reduction", "TNR", "SNR", "BM3D", "降噪"],
    "hdr": ["HDR", "WDR", "tone mapping", "wide dynamic range", "宽动态"],
    "lsc": ["lens shading correction", "LSC", "镜头阴影"],
}

# C 标准 / MISRA 关键词
STANDARD_KEYWORDS = {
    "c99":   ["C99", "ISO 9899:1999", "restrict", "VLA", "_Bool", "stdint"],
    "c11":   ["C11", "ISO 9899:2011", "_Generic", "stdatomic", "_Static_assert", "_Alignas"],
    "c17":   ["C17", "C18", "ISO 9899:2018"],
    "c23":   ["C23", "ISO 9899:2024", "nullptr", "#embed", "constexpr", "typeof", "_BitInt"],
    "misra": ["MISRA", "MISRA-C", "Rule", "Directive", "ISO 26262", "功能安全"],
    "cert":  ["CERT C", "SEI CERT", "MEM", "INT", "STR", "安全编码"],
}


# ──────────────────────────────────────────────
# 工具函数：ChromaDB 辅助
# ──────────────────────────────────────────────

def _sanitize(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _utf8_len(text: str) -> int:
    return len(_sanitize(text).encode("utf-8"))


def _truncate(text: str, max_bytes: int) -> tuple[str, bool]:
    encoded = _sanitize(text).encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    suffix = TRUNCATION_NOTICE.encode("utf-8")
    body = encoded[: max_bytes - len(suffix)]
    return body.decode("utf-8", errors="ignore") + TRUNCATION_NOTICE, True


def _get_or_fallback_collection(client, name: str, ef):
    """尝试获取指定 collection，不存在时回退到维度兼容的可用 collection。"""
    available = [getattr(c, "name", str(c)) for c in client.list_collections()]
    if not available:
        raise ValueError(
            "ChromaDB 中没有任何 collection，"
            "请先执行 'import' 子命令导入文档。"
        )

    candidates = ([name] if name in available else []) + \
                 [n for n in available if n != name]

    for cname in candidates:
        try:
            coll = client.get_collection(name=cname, embedding_function=ef)
            # 用空查询探测维度兼容性（count>0 时才做）
            if coll.count() > 0:
                coll.query(query_texts=["test"], n_results=1)
            if cname != name:
                print(f"[Agent] 集合 '{name}' 不存在或维度不兼容，回退到 '{cname}'")
            return coll, cname
        except Exception:
            continue

    raise ValueError(
        f"没有找到与当前 embedding 维度兼容的 collection（尝试过: {candidates}）。"
        "请执行 'import' 子命令重新导入文档。"
    )


def _chroma_query(db_path: str, collection_name: str, query_text: str,
                  n_results: int = DEFAULT_N_RESULTS) -> str:
    """在指定 collection 中检索，返回拼接好的上下文字符串。"""
    if chromadb is None:
        return "[错误] 未安装 chromadb，请执行: pip install chromadb"

    client = chromadb.PersistentClient(path=db_path)
    ef = embedding_functions.DefaultEmbeddingFunction()
    collection, used_name = _get_or_fallback_collection(client, collection_name, ef)

    if collection.count() == 0:
        return f"[集合 '{used_name}' 为空，请先导入相关文档]"

    results = collection.query(
        query_texts=[_sanitize(query_text)],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs      = (results.get("documents") or [[]])[0]
    metas     = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    if not docs:
        return "[未检索到相关资料]"

    parts = []
    used_bytes = 0
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        source = _sanitize((meta or {}).get("source", f"文档{i+1}"))
        header = f"[资料{i+1} | 来源:{source} | 距离:{dist:.4f}]\n"
        body, _ = _truncate(_sanitize(doc), MAX_DOC_BYTES)
        piece = header + body
        if used_bytes + _utf8_len(piece) > MAX_CONTEXT_BYTES:
            break
        parts.append(piece)
        used_bytes += _utf8_len(piece)

    return "\n\n".join(parts)


# ──────────────────────────────────────────────
# 四大工具函数
# ──────────────────────────────────────────────

def query_chip_doc(chip: str, keyword: str,
                   db_path: str = DEFAULT_DB_PATH,
                   n_results: int = DEFAULT_N_RESULTS) -> str:
    """
    检索特定芯片的 SDK 文档。
    chip: 芯片型号，如 hi3519 / rv1126 / rk3588 / imx678 / mt6985
    keyword: 检索关键词，如 ISP init / MPI / 编解码 / DMA-BUF
    """
    chip_lower = chip.lower().strip()
    query = f"{chip_lower} {keyword}"

    # 根据芯片品牌猜测领域
    if any(x in chip_lower for x in ["hi3", "hi35", "hi36", "hisilicon"]):
        coll = DOMAIN_COLLECTIONS["chip"]
    elif any(x in chip_lower for x in ["rv", "rk", "rockchip"]):
        coll = DOMAIN_COLLECTIONS["chip"]
    elif any(x in chip_lower for x in ["imx", "sony"]):
        coll = DOMAIN_COLLECTIONS["camera"]
    elif any(x in chip_lower for x in ["mt", "mediatek"]):
        coll = DOMAIN_COLLECTIONS["chip"]
    elif any(x in chip_lower for x in ["snapdragon", "qualcomm", "sm8"]):
        coll = DOMAIN_COLLECTIONS["chip"]
    else:
        coll = DOMAIN_COLLECTIONS["default"]

    context = _chroma_query(db_path, coll, query, n_results)
    return f"【芯片文档检索: {chip} / {keyword}】\n{context}"


def query_3a_algorithm(algo_type: str, scenario: str,
                       db_path: str = DEFAULT_DB_PATH,
                       n_results: int = DEFAULT_N_RESULTS) -> str:
    """
    检索 3A 算法相关资料。
    algo_type: ae / af / awb / nr / hdr / lsc
    scenario:  场景描述，如 低光 / 抗闪烁 / HDR双曝光 / 人脸优先
    """
    algo_lower = algo_type.lower().strip()
    extra_kw = " ".join(ALGO_KEYWORDS.get(algo_lower, [algo_lower]))
    query = f"{algo_lower} {extra_kw} {scenario}"
    context = _chroma_query(db_path, DOMAIN_COLLECTIONS["isp"], query, n_results)
    return f"【3A算法检索: {algo_type.upper()} / {scenario}】\n{context}"


def query_coding_standard(standard: str, rule_id: str = "",
                          db_path: str = DEFAULT_DB_PATH,
                          n_results: int = DEFAULT_N_RESULTS) -> str:
    """
    检索编程规范条目。
    standard: c99 / c11 / c17 / c23 / misra / cert
    rule_id:  规则编号或关键词，如 Rule-15.5 / INT30-C / restrict
    """
    std_lower = standard.lower().strip()
    extra_kw = " ".join(STANDARD_KEYWORDS.get(std_lower, [standard]))
    query = f"{standard} {extra_kw} {rule_id}".strip()
    context = _chroma_query(db_path, DOMAIN_COLLECTIONS["standard"], query, n_results)
    return f"【编程规范检索: {standard.upper()} {rule_id}】\n{context}"


def search_github_isp(vendor: str, feature: str,
                      token: str | None = None,
                      per_page: int = 10) -> str:
    """
    检索 GitHub 上特定厂商的开源 ISP 相关仓库。
    vendor:  hisilicon/rockchip/sony/mediatek/qualcomm/ambarella
             或 '' / 'general' 表示不限厂商
    feature: 检索特性，支持多词，如 'VENC H264 H265' / 'ISP AE 3A'
    策略：精确查 → 无结果时自动退回纯 feature 宽松搜索
    """
    vendor_lower  = vendor.lower().strip()
    feature_clean = feature.strip()

    # 构造候选查询（依次尝试，取第一个有结果的）
    if vendor_lower in ("general", "", "通用"):
        query_candidates = [
            feature_clean,
            f"topic:isp {feature_clean}",
        ]
    else:
        tmpl = VENDOR_QUERIES.get(vendor_lower, f"{vendor} {{feature}}")
        precise  = tmpl.format(feature=feature_clean)
        fallback = feature_clean                         # 不限厂商退回
        query_candidates = [precise, fallback]

    headers = {"Accept": "application/vnd.github+json"}
    resolved_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    items: list = []
    used_query  = ""
    for q in query_candidates:
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 422:
                continue          # 查询语法错误，尝试下一候选
            resp.raise_for_status()
            items = resp.json().get("items", [])
            used_query = q
            if items:
                break
        except requests.exceptions.RequestException as exc:
            return f"[GitHub API 请求失败: {exc}]"

    if not items:
        return (
            f"[未找到结果]\n"
            f"  厂商: {vendor or '通用'}\n"
            f"  特性: {feature_clean}\n"
            f"  已尝试: {' → '.join(query_candidates)}\n"
            f"  建议: 减少关键词、换英文词、或不加 --vendor"
        )

    lines = [
        f"【GitHub 检索: {vendor or '通用'} / {feature_clean}】",
        f"实际搜索式: {used_query}",
        "",
    ]
    for repo in items:
        name        = repo.get("full_name", "")
        stars       = repo.get("stargazers_count", 0)
        description = (repo.get("description") or "")[:90]
        url         = repo.get("html_url", "")
        language    = repo.get("language") or "N/A"
        updated     = repo.get("updated_at", "")[:10]
        topics      = ", ".join(repo.get("topics") or [])[:70]
        lines.append(f"  ★{stars:5d}  [{language}]  {name}")
        if description:
            lines.append(f"           {description}")
        if topics:
            lines.append(f"           topics: {topics}")
        lines.append(f"           {url}  (更新:{updated})")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Function Calling 工具定义（OpenAI 格式）
# ──────────────────────────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_chip_doc",
            "description": (
                "检索特定芯片（海思/瑞芯微/Sony/MediaTek/高通）的 SDK 文档、"
                "驱动接口、MPI 调用方法、寄存器说明等技术资料。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chip": {
                        "type": "string",
                        "description": "芯片型号，如 hi3519、rv1126、rk3588、imx678、mt6985",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "检索关键词，如 ISP初始化、VI CreatePipe、DMA-BUF、编解码",
                    },
                },
                "required": ["chip", "keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_3a_algorithm",
            "description": (
                "检索 3A 算法（AE自动曝光/AF自动对焦/AWB自动白平衡）及 NR降噪/HDR/LSC 等"
                "ISP 图像处理算法的原理、实现方法和调参策略。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "algo_type": {
                        "type": "string",
                        "enum": ["ae", "af", "awb", "nr", "hdr", "lsc"],
                        "description": "算法类型: ae/af/awb/nr/hdr/lsc",
                    },
                    "scenario": {
                        "type": "string",
                        "description": "应用场景，如 低照度、抗闪烁、HDR双曝光、人脸优先对焦",
                    },
                },
                "required": ["algo_type", "scenario"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_coding_standard",
            "description": (
                "查询 C 语言编程规范（C99/C11/C17/C23）或嵌入式安全规范"
                "（MISRA C:2012/CERT C）的具体规则说明和最佳实践。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "standard": {
                        "type": "string",
                        "enum": ["c99", "c11", "c17", "c23", "misra", "cert"],
                        "description": "规范类型: c99/c11/c17/c23/misra/cert",
                    },
                    "rule_id": {
                        "type": "string",
                        "description": "规则编号或关键词，如 Rule-15.5、INT30-C、restrict、_Generic",
                    },
                },
                "required": ["standard"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_github_isp",
            "description": (
                "在 GitHub 上检索特定芯片厂商（海思/瑞芯微/Sony/MediaTek/高通/安霸）"
                "的开源 ISP SDK、3A 算法库、驱动代码等项目。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor": {
                        "type": "string",
                        "description": "芯片厂商: hisilicon/rockchip/sony/mediatek/qualcomm/ambarella",
                    },
                    "feature": {
                        "type": "string",
                        "description": "检索特性，如 ISP、3A、demosaic、noise-reduction、AE",
                    },
                },
                "required": ["vendor", "feature"],
            },
        },
    },
]


# ──────────────────────────────────────────────
# 工具分发器
# ──────────────────────────────────────────────

def dispatch_tool(name: str, args: dict,
                  db_path: str = DEFAULT_DB_PATH,
                  github_token: str | None = None) -> str:
    """根据 LLM 返回的 tool_call 执行对应工具函数。"""
    if name == "query_chip_doc":
        return query_chip_doc(
            chip=args.get("chip", ""),
            keyword=args.get("keyword", ""),
            db_path=db_path,
        )
    if name == "query_3a_algorithm":
        return query_3a_algorithm(
            algo_type=args.get("algo_type", "ae"),
            scenario=args.get("scenario", ""),
            db_path=db_path,
        )
    if name == "query_coding_standard":
        return query_coding_standard(
            standard=args.get("standard", "c23"),
            rule_id=args.get("rule_id", ""),
            db_path=db_path,
        )
    if name == "search_github_isp":
        return search_github_isp(
            vendor=args.get("vendor", ""),
            feature=args.get("feature", ""),
            token=github_token,
        )
    return f"[未知工具: {name}]"


# ──────────────────────────────────────────────
# LLM 调用（OpenAI 兼容，含 Function Calling）
# ──────────────────────────────────────────────

def _chat_request(messages: list, model: str, api_key: str,
                  base_url: str, tools: list | None = None,
                  timeout: int = 120) -> dict:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"

    payload: dict = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"LLM 返回非 JSON: HTTP {resp.status_code}, {resp.text[:400]}") from exc

    if not resp.ok:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        msg = err.get("message") or err.get("code") or resp.text[:300]
        raise RuntimeError(f"LLM 调用失败: HTTP {resp.status_code}, {msg}")
    return data


def _extract_message(data: dict) -> dict:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM 响应无 choices: {data}")
    return choices[0].get("message", {})


# ──────────────────────────────────────────────
# Agent 主循环（多轮 Function Calling）
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一位专注于嵌入式Linux开发、相机ISP SDK开发、3A算法调优的高级工程师助手。
你拥有以下工具来检索专业知识库和GitHub开源资源：
- query_chip_doc：查询芯片（海思/瑞芯微/Sony/联发科/高通）SDK文档
- query_3a_algorithm：查询AE/AF/AWB/NR/HDR等ISP算法原理和调参
- query_coding_standard：查询C99/C11/C23/MISRA/CERT编程规范
- search_github_isp：搜索GitHub上各厂商开源ISP项目

回答规则：
1. 优先调用工具获取资料，再基于资料给出准确答案
2. 技术答案要包含具体的API名称、函数、寄存器或参数
3. 引用开源代码时注明仓库来源
4. 若工具返回"资料不足"，明确说明并给出替代建议
"""


def run_agent(question: str, model: str, api_key: str,
              base_url: str, db_path: str,
              github_token: str | None = None,
              max_rounds: int = 6,
              verbose: bool = False) -> str:
    """
    多轮 Function Calling Agent 主循环。
    返回最终文本答案。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": _sanitize(question)},
    ]

    for round_num in range(1, max_rounds + 1):
        if verbose:
            print(f"\n[Agent] 第 {round_num} 轮 LLM 调用...")

        data    = _chat_request(messages, model, api_key, base_url, TOOLS_SCHEMA)
        message = _extract_message(data)
        finish  = (data.get("choices") or [{}])[0].get("finish_reason", "")

        # 追加 assistant 消息（含 tool_calls 或纯文本）
        messages.append(message)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            # 无工具调用，直接返回
            return message.get("content") or "[Agent 无输出]"

        # 执行所有工具调用
        for tc in tool_calls:
            tc_id   = tc.get("id", "")
            tc_name = tc.get("function", {}).get("name", "")
            try:
                tc_args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                tc_args = {}

            if verbose:
                print(f"[Tool] 调用 {tc_name}({tc_args})")

            result = dispatch_tool(tc_name, tc_args, db_path, github_token)

            if verbose:
                preview = result[:300].replace("\n", " ")
                print(f"[Tool] 结果预览: {preview}...")

            messages.append({
                "role":         "tool",
                "tool_call_id": tc_id,
                "name":         tc_name,
                "content":      _sanitize(result),
            })

    # 超出最大轮数，再做一次无工具调用收尾
    data    = _chat_request(messages, model, api_key, base_url, tools=None)
    message = _extract_message(data)
    return message.get("content") or "[Agent 超出最大轮数，无最终答案]"


# ──────────────────────────────────────────────
# 文档导入（与 inquiry_chroma_llm.py 同模式）
# ──────────────────────────────────────────────

def _doc_id(filename: str) -> str:
    return "md-" + hashlib.sha1(os.fsencode(filename)).hexdigest()


def import_docs(db_path: str, docs_path: str,
                collection_name: str = "markdown_docs") -> None:
    """将 docs 目录下的 .md 文件批量导入到指定 collection。"""
    if chromadb is None:
        print("[错误] 未安装 chromadb")
        return

    client = chromadb.PersistentClient(path=db_path)
    ef     = embedding_functions.DefaultEmbeddingFunction()
    coll   = client.get_or_create_collection(name=collection_name, embedding_function=ef)

    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
        print(f"[导入] 目录 {docs_path} 已创建，请放入 .md 文件后重新运行")
        return

    ids, docs, metas = [], [], []
    for fname in sorted(os.listdir(docs_path)):
        fpath = os.path.join(docs_path, fname)
        if fname.endswith(".md") and os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            ids.append(_doc_id(fname))
            docs.append(content)
            metas.append({"source": fname, "path": fpath})

    if docs:
        # 元数据只保留纯 ASCII/UTF-8 字符串，避免 ChromaDB 序列化失败
        safe_metas = [{"source": _sanitize(m["source"])} for m in metas]
        coll.upsert(ids=ids, documents=docs, metadatas=safe_metas)
        print(f"[导入] 成功导入/更新 {len(docs)} 个文件 → 集合 '{collection_name}'")
    else:
        print(f"[导入] {docs_path} 下没有找到 .md 文件")


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ISP/嵌入式开发智能检索 Agent（ChromaDB + Qwen Function Calling）"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ── agent 子命令（问答）
    ask = sub.add_parser("ask", help="向 Agent 提问（自动调用工具检索）")
    ask.add_argument("question", help="问题，如 '海思hi3519的ISP初始化流程'")
    ask.add_argument("--model",    default=DEFAULT_MODEL_NAME)
    ask.add_argument("--base-url", default=os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL)
    ask.add_argument("--api-key",  default=os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"))
    ask.add_argument("--db-path",  default=DEFAULT_DB_PATH)
    ask.add_argument("--github-token", default=os.getenv("GITHUB_TOKEN"))
    ask.add_argument("--max-rounds",   type=int, default=6)
    ask.add_argument("--verbose",  action="store_true")

    # ── tool 子命令（直接调用单个工具）
    tool = sub.add_parser("tool", help="直接调用单个工具函数")
    tool_sub = tool.add_subparsers(dest="tool_name", required=True)

    t1 = tool_sub.add_parser("chip", help="query_chip_doc")
    t1.add_argument("chip",    help="芯片型号，如 hi3519")
    t1.add_argument("keyword", help="检索关键词")
    t1.add_argument("--db-path", default=DEFAULT_DB_PATH)

    t2 = tool_sub.add_parser("3a", help="query_3a_algorithm")
    t2.add_argument("algo_type", choices=list(ALGO_KEYWORDS.keys()), help="算法类型")
    t2.add_argument("scenario",  help="应用场景")
    t2.add_argument("--db-path", default=DEFAULT_DB_PATH)

    t3 = tool_sub.add_parser("standard", help="query_coding_standard")
    t3.add_argument("standard", choices=list(STANDARD_KEYWORDS.keys()), help="规范类型")
    t3.add_argument("rule_id",  nargs="?", default="", help="规则编号（可选）")
    t3.add_argument("--db-path", default=DEFAULT_DB_PATH)

    t4 = tool_sub.add_parser(
        "github",
        help="search_github_isp — 搜索 GitHub 开源 ISP/嵌入式仓库",
        description=(
            "示例:\n"
            "  不限厂商: tool github ISP AE 3A\n"
            "  不限厂商: tool github VENC H264 H265 yuv rgb convert\n"
            "  指定厂商: tool github --vendor hisilicon ISP AE\n"
            "  指定厂商: tool github --vendor rockchip VENC H264\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    t4.add_argument(
        "--vendor", "-v",
        default="",
        metavar="VENDOR",
        help="芯片厂商(可选): hisilicon/rockchip/sony/mediatek/qualcomm/ambarella",
    )
    t4.add_argument(
        "feature",
        nargs="+",
        help="检索特性关键词（多个词自动拼接），如: ISP AE  /  VENC H264 H265",
    )
    t4.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    t4.add_argument("--per-page", type=int, default=10, help="返回结果数量，默认10")

    # ── import 子命令（导入文档）
    imp = sub.add_parser("import", help="批量导入 Markdown 文档到 ChromaDB")
    imp.add_argument("--docs-path",       default=DEFAULT_DOCS_PATH)
    imp.add_argument("--db-path",         default=DEFAULT_DB_PATH)
    imp.add_argument("--collection-name", default="markdown_docs")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command == "import":
        import_docs(args.db_path, args.docs_path, args.collection_name)
        return

    if args.command == "tool":
        if args.tool_name == "chip":
            print(query_chip_doc(args.chip, args.keyword, args.db_path))
        elif args.tool_name == "3a":
            print(query_3a_algorithm(args.algo_type, args.scenario, args.db_path))
        elif args.tool_name == "standard":
            print(query_coding_standard(args.standard, args.rule_id, args.db_path))
        elif args.tool_name == "github":
            feature_str = " ".join(args.feature)   # 多个词自动拼接为一个字符串
            print(search_github_isp(
                vendor=args.vendor,
                feature=feature_str,
                token=args.token,
                per_page=args.per_page,
            ))
        return

    if args.command == "ask":
        if not args.api_key:
            parser.error(
                "缺少 API Key，请设置环境变量 DASHSCOPE_API_KEY "
                "或通过 --api-key 传入"
            )
        print(f"\n[Agent] 问题: {args.question}\n{'='*60}")
        answer = run_agent(
            question=args.question,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            db_path=args.db_path,
            github_token=args.github_token,
            max_rounds=args.max_rounds,
            verbose=args.verbose,
        )
        print("\n===== Agent 答案 =====")
        print(answer)


if __name__ == "__main__":
    main()
