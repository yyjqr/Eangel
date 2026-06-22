"""
skills_chroma_qianwen.py
基于 ChromaDB + 通义千问(DashScope) 的技能知识库
- 导入 docs/skills.md 按章节分块存入 Chroma
- 使用 Qianwen text-embedding-v3 向量化
- LangGraph Agent 检索问答
- 预留 GitHub 代码搜索入口
"""

import os
import re
import hashlib
from typing import List, TypedDict, Optional

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
SKILLS_MD_PATH = os.path.join(os.path.dirname(__file__), "docs", "skills.md")
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "my_chroma_db")
COLLECTION_NAME = "skills_memory"
EMBED_MODEL = "text-embedding-v3"
CHAT_MODEL = "qwen-plus"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# GitHub 搜索（后续接入，需在此填写 token）
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


# ─────────────────────────────────────────────
# DashScope 向量化函数（供 ChromaDB 使用）
# ─────────────────────────────────────────────
class QianwenEmbedding(EmbeddingFunction):
    """通义千问 text-embedding-v3，兼容 ChromaDB EmbeddingFunction 接口。"""

    def __init__(self):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        assert api_key, "请设置环境变量 DASHSCOPE_API_KEY"
        self._client = OpenAI(
            api_key=api_key,
            base_url=DASHSCOPE_BASE_URL,
        )

    def __call__(self, input: Documents) -> Embeddings:  # type: ignore[override]
        # DashScope 单次最多 25 条，超出需分批
        batch_size = 25
        all_embeddings: Embeddings = []
        for i in range(0, len(input), batch_size):
            batch = input[i : i + batch_size]
            resp = self._client.embeddings.create(model=EMBED_MODEL, input=batch)
            all_embeddings.extend([item.embedding for item in resp.data])
        return all_embeddings


# ─────────────────────────────────────────────
# skills.md 加载与分块
# ─────────────────────────────────────────────
def load_skills_chunks(path: str) -> List[dict]:
    """
    按 ## / ### 章节分块，每块携带 section 元数据。
    返回 [{"id": str, "section": str, "content": str}, ...]
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    h2_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    h3_pattern = re.compile(r"^### (.+)$", re.MULTILINE)

    # 先按 ## 分大块
    h2_matches = list(h2_pattern.finditer(content))
    chunks = []
    if not h2_matches:
        chunks.append({"section": "全文", "content": content.strip()})
    else:
        for idx, m in enumerate(h2_matches):
            start = m.start()
            end = h2_matches[idx + 1].start() if idx + 1 < len(h2_matches) else len(content)
            section_text = content[start:end].strip()
            section_name = m.group(1).strip()

            # 再按 ### 细分
            h3_matches = list(h3_pattern.finditer(section_text))
            if h3_matches:
                for j, hm in enumerate(h3_matches):
                    sub_start = hm.start()
                    sub_end = h3_matches[j + 1].start() if j + 1 < len(h3_matches) else len(section_text)
                    sub_text = section_text[sub_start:sub_end].strip()
                    sub_name = hm.group(1).strip()
                    if sub_text:
                        chunks.append({"section": f"{section_name} > {sub_name}", "content": sub_text})
            else:
                chunks.append({"section": section_name, "content": section_text})

    # 生成稳定 ID
    for chunk in chunks:
        chunk["id"] = hashlib.md5(chunk["content"].encode()).hexdigest()

    return chunks


# ─────────────────────────────────────────────
# 导入 skills.md 到 Chroma
# ─────────────────────────────────────────────
def import_skills(force: bool = False, path: str = SKILLS_MD_PATH):
    """
    将指定 md 文件（或目录下所有 .md 文件）导入 Chroma。
    force=True 时先清空集合再重新导入；默认跳过已存在条目。
    """
    # 收集待导入文件列表
    if os.path.isdir(path):
        md_files = sorted(
            os.path.join(path, f) for f in os.listdir(path) if f.endswith(".md")
        )
        if not md_files:
            print(f"[WARN] 目录 {path!r} 下未找到 .md 文件")
            return None
    else:
        md_files = [path]

    embed_fn = QianwenEmbedding()
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    if force:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"[INFO] 已清空旧集合 {COLLECTION_NAME}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    total_new = 0
    for md_path in md_files:
        safe_name = md_path.encode("utf-8", errors="replace").decode("utf-8")
        print(f"[INFO] 导入文件: {safe_name}")
        chunks = load_skills_chunks(md_path)
        existing_ids = set(collection.get(include=[])["ids"])
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        if not new_chunks:
            print(f"[INFO]   无新增条目（已是最新，共 {len(existing_ids)} 条）")
            continue
        collection.add(
            ids=[c["id"] for c in new_chunks],
            documents=[c["content"] for c in new_chunks],
            metadatas=[{"section": c["section"]} for c in new_chunks],
        )
        print(f"[INFO]   写入 {len(new_chunks)} 个分块")
        total_new += len(new_chunks)

    print(f"[INFO] 全部完成，本次共写入 {total_new} 个分块。")
    return collection


# ─────────────────────────────────────────────
# GitHub 搜索（预留接口）
# ─────────────────────────────────────────────
def github_search_repos(query: str, top_n: int = 5) -> List[dict]:
    """
    搜索 GitHub 仓库，返回 [{name, url, stars, description}, ...]。
    需要在环境变量 GITHUB_TOKEN 中设置 Personal Access Token。
    """
    if not GITHUB_TOKEN:
        print("[WARN] 未设置 GITHUB_TOKEN，GitHub 搜索跳过。")
        return []

    try:
        import urllib.request
        import json as _json

        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={top_n}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = _json.loads(resp.read())

        return [
            {
                "name": item["full_name"],
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "forks": item["forks_count"],
                "description": item.get("description", ""),
            }
            for item in data.get("items", [])
        ]
    except Exception as exc:
        print(f"[ERROR] GitHub 搜索失败: {exc}")
        return []


# 补全缺失的 urllib.parse
import urllib.parse  # noqa: E402 (needed after function definition)


# ─────────────────────────────────────────────
# LangGraph Agent
# ─────────────────────────────────────────────
class SkillsState(TypedDict, total=False):
    query: str
    skill_context: str
    github_results: List[dict]
    answer: str


def _get_collection():
    embed_fn = QianwenEmbedding()
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_node(state: SkillsState) -> dict:
    """从 Chroma 检索最相关的技能片段。"""
    query = state.get("query", "")
    if not query:
        return {"skill_context": "", "github_results": []}

    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=4, include=["documents", "metadatas"])

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    parts = []
    for doc, meta in zip(docs, metas):
        section = meta.get("section", "")
        parts.append(f"【{section}】\n{doc}")

    skill_context = "\n\n---\n\n".join(parts)

    # 同步搜索 GitHub（有 token 才执行）
    github_results = github_search_repos(query, top_n=3)

    return {"skill_context": skill_context, "github_results": github_results}


def answer_node(state: SkillsState) -> dict:
    """结合检索结果，用 Qianwen 生成回答。"""
    query = state.get("query", "")
    skill_context = state.get("skill_context", "")
    github_results = state.get("github_results", [])

    if not query:
        return {"answer": "请输入问题。"}

    llm = ChatOpenAI(
        model=CHAT_MODEL,
        base_url=DASHSCOPE_BASE_URL,
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )

    github_section = ""
    if github_results:
        lines = [
            f"- **{r['name']}**\n  链接：{r['url']}\n  ⭐ Stars: {r['stars']}  🍴 Forks(参与数): {r['forks']}\n  {r['description']}"
            for r in github_results
        ]
        github_section = "\n\nGitHub 相关仓库：\n" + "\n".join(lines)

    prompt = f"""你是一位资深技术专家，请根据以下知识库内容回答问题。
如果知识库中没有相关信息，请说明并基于自身知识回答。

知识库内容：
{skill_context or "（未找到相关内容）"}
{github_section}

问题：{query}

请给出准确、简洁的技术回答。"""

    try:
        response = llm.invoke(prompt)
        answer_text = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as exc:
        # 阿里云内容审核拦截（data_inspection_failed）：去掉检索上下文后仅用原问题重试
        if "data_inspection_failed" in str(exc) or "inappropriate content" in str(exc):
            print("[WARN] 检索上下文触发内容审核，已移除上下文后重试...")
            fallback_prompt = f"你是一位资深技术专家，请回答以下问题：\n\n{query}"
            response = llm.invoke(fallback_prompt)
            answer_text = response.content if isinstance(response.content, str) else str(response.content)
        else:
            raise
    return {"answer": answer_text}


# 构建工作流
_workflow = StateGraph(SkillsState)
_workflow.add_node("retrieve", retrieve_node)
_workflow.add_node("answer", answer_node)
_workflow.set_entry_point("retrieve")
_workflow.add_edge("retrieve", "answer")
_workflow.add_edge("answer", END)
skills_app = _workflow.compile()


def query_skills(question: str) -> str:
    """便捷查询接口，返回回答字符串。"""
    result = skills_app.invoke({"query": question})
    return result.get("answer", "")


# ─────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="技能知识库检索 (Chroma + Qianwen)")
    parser.add_argument("--import-skills", nargs="?", const=SKILLS_MD_PATH, metavar="FILE",
                        help="导入指定 md 文件（默认 docs/skills.md）")
    parser.add_argument("--force", action="store_true", help="配合 --import-skills，清空后重新导入")
    parser.add_argument("--query", "-q", type=str, default="", help="提问内容")
    args = parser.parse_args()

    if args.import_skills:
        import_skills(force=args.force, path=args.import_skills)

    if args.query:
        print("\n正在检索...\n")
        ans = query_skills(args.query)
        print("=" * 60)
        print(ans)
        print("=" * 60)
    elif not args.import_skills:
        parser.print_help()
